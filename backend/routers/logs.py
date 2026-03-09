"""
routers/logs.py — Food and Weight logging endpoints.

POST /log/food   → Log calories + protein for a day; update weekly budget.
POST /log/weight → Log a new weight entry; trigger 14-day recalibration if due.
"""
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from backend.models import LogFoodRequest, LogFoodResponse, LogWeightRequest, LogWeightResponse
from backend.database import supabase_admin
from backend.auth_utils import get_current_user
from backend.engine import compute_full_metabolic_profile, run_recalibration, evaluate_guardrails

router = APIRouter(prefix="/log", tags=["Logging"])


# ─────────────────────────────────────────────────────────────
# POST /log/food
# ─────────────────────────────────────────────────────────────
@router.post("/food", response_model=LogFoodResponse)
async def log_food(payload: LogFoodRequest, authenticated_user_id: str = Depends(get_current_user)) -> LogFoodResponse:
    """
    Upserts the daily_logs row for the given date and deducts the consumed
    calories from the active weekly_budgets row.
    Returns the updated remaining budget and the recommended daily target
    for the rest of the week (budget evenly spread).
    """
    if payload.user_id != authenticated_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    # ── 1. Fetch user ──────────────────────────────────────────────────────
    user_resp = (
        supabase_admin.table("users")
        .select("weight_kg, body_fat, activity_level, goal, target_rate")
        .eq("id", payload.user_id)
        .single()
        .execute()
    )
    if not user_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user = user_resp.data

    # ── 2. Fetch or create daily log ───────────────────────────────────────
    existing_resp = (
        supabase_admin.table("daily_logs")
        .select("id, calories_consumed, protein_consumed")
        .eq("user_id", payload.user_id)
        .eq("date", str(payload.date))
        .execute()
    )

    if existing_resp.data:
        # Increment existing log (accumulate throughout the day)
        existing = existing_resp.data[0]
        new_calories = existing["calories_consumed"] + payload.calories
        new_protein = existing["protein_consumed"] + payload.protein_g
        kcal_delta = payload.calories  # Only the NEW calories matter for budget deduction

        supabase_admin.table("daily_logs").update({
            "calories_consumed": new_calories,
            "protein_consumed": new_protein,
        }).eq("id", existing["id"]).execute()
    else:
        new_calories = payload.calories
        new_protein = payload.protein_g
        kcal_delta = payload.calories

        supabase_admin.table("daily_logs").insert({
            "user_id":           payload.user_id,
            "date":              str(payload.date),
            "calories_consumed": new_calories,
            "protein_consumed":  new_protein,
        }).execute()

    # ── 3. Deduct from weekly budget ───────────────────────────────────────
    week_start = payload.date - timedelta(days=payload.date.weekday())
    budget_resp = (
        supabase_admin.table("weekly_budgets")
        .select("id, remaining_budget, start_date")
        .eq("user_id", payload.user_id)
        .eq("start_date", str(week_start))
        .single()
        .execute()
    )

    if not budget_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No weekly budget found for this date. Please complete onboarding.",
        )

    new_remaining = budget_resp.data["remaining_budget"] - kcal_delta
    supabase_admin.table("weekly_budgets").update({
        "remaining_budget": new_remaining
    }).eq("id", budget_resp.data["id"]).execute()

    # ── 4. Calculate daily target for remaining days of the week ──────────
    days_elapsed = payload.date.weekday() + 1  # 1–7
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


# ─────────────────────────────────────────────────────────────
# POST /log/weight
# ─────────────────────────────────────────────────────────────
@router.post("/weight", response_model=LogWeightResponse)
async def log_weight(payload: LogWeightRequest, authenticated_user_id: str = Depends(get_current_user)) -> LogWeightResponse:
    """
    Logs a new weight entry. If 14+ days have elapsed since the last recalibration,
    runs the Phase 1 recalibration engine and seeds a new weekly budget.
    """
    if payload.user_id != authenticated_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    # ── 1. Fetch user ──────────────────────────────────────────────────────
    user_resp = (
        supabase_admin.table("users")
        .select("*")
        .eq("id", payload.user_id)
        .single()
        .execute()
    )
    if not user_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user = user_resp.data

    # ── 2. Upsert weight log ───────────────────────────────────────────────
    supabase_admin.table("weight_logs").upsert({
        "user_id":   payload.user_id,
        "date":      str(payload.date),
        "weight_kg": payload.weight_kg,
    }, on_conflict="user_id,date").execute()

    # Update user's stored weight
    supabase_admin.table("users").update({
        "weight_kg": payload.weight_kg
    }).eq("id", payload.user_id).execute()

    # ── 3. Check if 14-day recalibration is due ───────────────────────────
    last_recal_date = user.get("last_recalibration_date")
    should_recalibrate = False

    if last_recal_date is None:
        # First weight log after onboarding - use the onboarding date as baseline
        oldest_log_resp = (
            supabase_admin.table("weight_logs")
            .select("date, weight_kg")
            .eq("user_id", payload.user_id)
            .order("date", desc=False)
            .limit(1)
            .execute()
        )
        days_since = (payload.date - date.fromisoformat(oldest_log_resp.data[0]["date"])).days
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
    # Get weight at recalibration baseline
    baseline_resp = (
        supabase_admin.table("weight_logs")
        .select("weight_kg")
        .eq("user_id", payload.user_id)
        .lte("date", str(last_recal_date or payload.date - timedelta(days=14)))
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    baseline_weight = baseline_resp.data[0]["weight_kg"] if baseline_resp.data else user["weight_kg"]
    actual_weight_change = payload.weight_kg - baseline_weight

    # Sum all kcal deltas over the 14-day window (actual consumed - TDEE)
    # Approximation: use total_budget - remaining_budget from weekly budgets in range
    period_start = (payload.date - timedelta(days=14))
    budgets_resp = (
        supabase_admin.table("weekly_budgets")
        .select("total_budget, remaining_budget")
        .eq("user_id", payload.user_id)
        .gte("start_date", str(period_start))
        .execute()
    )
    total_14_day_delta = sum(
        (b["total_budget"] - b["remaining_budget"]) * -1  # deficit is negative
        for b in (budgets_resp.data or [])
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
    supabase_admin.table("users").update({
        "current_tdee":             new_tdee,
        "last_recalibration_date":  str(payload.date),
    }).eq("id", payload.user_id).execute()

    # ── 6. Seed new weekly budget based on recalibrated TDEE ───────────────
    profile = compute_full_metabolic_profile(
        weight_kg=payload.weight_kg,
        body_fat=user["body_fat"],
        activity_level=user["activity_level"],
        goal=user["goal"],
        target_rate=user["target_rate"],
    )
    # Override TDEE with recalibrated value for budget calculation
    from dynacalorie import calculate_caloric_target
    daily_target = calculate_caloric_target(new_tdee, user["goal"], user["target_rate"])
    new_weekly_budget = round(daily_target * 7, 2)

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    supabase_admin.table("weekly_budgets").upsert({
        "user_id":          payload.user_id,
        "start_date":       str(week_start),
        "end_date":         str(week_end),
        "total_budget":     new_weekly_budget,
        "remaining_budget": new_weekly_budget,
    }, on_conflict="user_id,start_date").execute()

    return LogWeightResponse(
        message="Weight logged and 14-day recalibration complete.",
        recalibrated=True,
        recalibration_summary=recal_result,
        new_weekly_budget_kcal=new_weekly_budget,
    )
