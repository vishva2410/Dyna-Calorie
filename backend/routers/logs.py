"""
routers/logs.py — Food and Weight logging endpoints.

POST /log/food   → Log calories + protein for a day; update weekly budget.
POST /log/weight → Log a new weight entry; trigger 14-day recalibration if due.
"""
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from backend.models import LogFoodRequest, LogFoodResponse, LogWeightRequest, LogWeightResponse
from backend.database_local import (
    get_user, get_user_fields, upsert_daily_log,
    get_weekly_budget, update_weekly_budget_remaining,
    upsert_weight_log, update_user, get_oldest_weight_log,
    get_weight_before_date, get_budgets_since,
)
from backend.auth_utils import get_current_user
from backend.engine import compute_full_metabolic_profile, run_recalibration, evaluate_guardrails
from backend.database_local import upsert_weekly_budget

router = APIRouter(prefix="/log", tags=["Logging"])


@router.post("/food", response_model=LogFoodResponse)
async def log_food(payload: LogFoodRequest, authenticated_user_id: str = Depends(get_current_user)) -> LogFoodResponse:
    if payload.user_id != authenticated_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    # ── 1. Fetch user ──────────────────────────────────────────────────────
    user = get_user_fields(payload.user_id, ["weight_kg", "body_fat", "activity_level", "goal", "target_rate"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # ── 2. Upsert daily log ────────────────────────────────────────────────
    new_calories, new_protein, kcal_delta = upsert_daily_log(
        payload.user_id, str(payload.date), payload.calories, payload.protein_g
    )

    # ── 3. Deduct from weekly budget ───────────────────────────────────────
    week_start = payload.date - timedelta(days=payload.date.weekday())
    budget = get_weekly_budget(payload.user_id, str(week_start))

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No weekly budget found for this date. Please complete onboarding.",
        )

    new_remaining = budget["remaining_budget"] - kcal_delta
    update_weekly_budget_remaining(budget["id"], new_remaining)

    # ── 4. Calculate daily target for remaining days ──────────────────────
    days_elapsed = payload.date.weekday() + 1
    days_remaining = max(7 - days_elapsed, 1)
    new_daily_target = new_remaining / days_remaining

    # ── 5. Guardrail check ─────────────────────────────────────────────────
    warnings = evaluate_guardrails(
        weekly_weight_loss_kg=0.0,
        weight_kg=user["weight_kg"],
        daily_protein_g=new_protein,
    )

    return LogFoodResponse(
        message="Food log updated.",
        remaining_budget_kcal=round(new_remaining, 2),
        new_daily_target_kcal=round(new_daily_target, 2),
        guardrail_warnings=warnings,
    )


@router.post("/weight", response_model=LogWeightResponse)
async def log_weight(payload: LogWeightRequest, authenticated_user_id: str = Depends(get_current_user)) -> LogWeightResponse:
    if payload.user_id != authenticated_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    # ── 1. Fetch user ──────────────────────────────────────────────────────
    user = get_user(payload.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # ── 2. Upsert weight log ───────────────────────────────────────────────
    upsert_weight_log(payload.user_id, str(payload.date), payload.weight_kg)

    # Update user's stored weight
    update_user(payload.user_id, {"weight_kg": payload.weight_kg})

    # ── 3. Check if 14-day recalibration is due ───────────────────────────
    last_recal_date = user.get("last_recalibration_date")
    should_recalibrate = False

    if last_recal_date is None:
        oldest = get_oldest_weight_log(payload.user_id)
        if oldest:
            days_since = (payload.date - date.fromisoformat(oldest["date"])).days
            if days_since >= 14:
                should_recalibrate = True
    else:
        days_since = (payload.date - date.fromisoformat(last_recal_date)).days
        if days_since >= 14:
            should_recalibrate = True

    if not should_recalibrate:
        return LogWeightResponse(
            message="Weight logged. Recalibration not yet due.",
            recalibrated=False,
        )

    # ── 4. Run recalibration engine ────────────────────────────────────────
    baseline_date = last_recal_date or str(payload.date - timedelta(days=14))
    baseline = get_weight_before_date(payload.user_id, baseline_date)
    baseline_weight = baseline["weight_kg"] if baseline else user["weight_kg"]
    actual_weight_change = payload.weight_kg - baseline_weight

    period_start = str(payload.date - timedelta(days=14))
    budgets = get_budgets_since(payload.user_id, period_start)
    total_14_day_delta = sum(
        (b["total_budget"] - b["remaining_budget"]) * -1
        for b in budgets
    )

    current_tdee = user.get("current_tdee") or compute_full_metabolic_profile(
        weight_kg=user["weight_kg"],
        body_fat=user["body_fat"],
        activity_level=user["activity_level"],
        goal=user["goal"],
        target_rate=user["target_rate"],
    )["tdee_kcal"]

    recal_result = run_recalibration(
        current_tdee=current_tdee,
        total_14_day_kcal_delta=total_14_day_delta,
        actual_weight_change_kg=actual_weight_change,
    )

    new_tdee = recal_result["new_tdee_kcal"]

    # ── 5. Update user TDEE + recalibration date ───────────────────────────
    update_user(payload.user_id, {
        "current_tdee": new_tdee,
        "last_recalibration_date": str(payload.date),
    })

    # ── 6. Seed new weekly budget based on recalibrated TDEE ───────────────
    from dynacalorie import calculate_caloric_target
    daily_target = calculate_caloric_target(new_tdee, user["goal"], user["target_rate"])
    new_weekly_budget = round(daily_target * 7, 2)

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    upsert_weekly_budget({
        "user_id":          payload.user_id,
        "start_date":       str(week_start),
        "end_date":         str(week_end),
        "total_budget":     new_weekly_budget,
        "remaining_budget": new_weekly_budget,
    })

    return LogWeightResponse(
        message="Weight logged and 14-day recalibration complete.",
        recalibrated=True,
        recalibration_summary=recal_result,
        new_weekly_budget_kcal=new_weekly_budget,
    )
