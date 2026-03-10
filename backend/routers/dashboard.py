"""
routers/dashboard.py — GET /dashboard/{user_id}

Returns the user's current weekly budget, remaining calories, today's intake,
protein compliance, and guardrail warnings.
"""
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from backend.models import DashboardResponse, AvatarMetrics, HistoryResponse
from backend.database_local import (
    get_user, get_weekly_budget, insert_weekly_budget,
    get_daily_log_fields, get_latest_weight,
    get_weekly_budget_fields, get_weight_logs_since, get_daily_logs_since,
)
from backend.auth_utils import get_current_user
from backend.engine import compute_full_metabolic_profile, evaluate_guardrails
from dynacalorie import calculate_lbm

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/{user_id}", response_model=DashboardResponse)
async def get_dashboard(user_id: str, authenticated_user_id: str = Depends(get_current_user)) -> DashboardResponse:
    if user_id != authenticated_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user's data.")

    # ── 1. Fetch user profile ──────────────────────────────────────────────
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # ── 2. Fetch active weekly budget ──────────────────────────────────────
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    budget = get_weekly_budget(user_id, str(week_start))

    if not budget:
        profile = compute_full_metabolic_profile(
            weight_kg=user["weight_kg"],
            body_fat=user["body_fat"],
            activity_level=user["activity_level"],
            goal=user["goal"],
            target_rate=user["target_rate"],
        )
        insert_weekly_budget({
            "user_id":          user_id,
            "start_date":       str(week_start),
            "end_date":         str(week_end),
            "total_budget":     profile["weekly_budget_kcal"],
            "remaining_budget": profile["weekly_budget_kcal"],
        })
        weekly_budget = profile["weekly_budget_kcal"]
        remaining_budget = weekly_budget
    else:
        weekly_budget = budget["total_budget"]
        remaining_budget = budget["remaining_budget"]

    # ── 3. Fetch today's food log ──────────────────────────────────────────
    log = get_daily_log_fields(user_id, str(today), ["calories_consumed", "protein_consumed"])
    if not log:
        log = {"calories_consumed": 0.0, "protein_consumed": 0.0}

    # ── 4. Latest weight ───────────────────────────────────────────────────
    current_weight = get_latest_weight(user_id) or user["weight_kg"]

    # ── 5. Protein target and compliance ──────────────────────────────────
    lbm = calculate_lbm(current_weight, user["body_fat"])
    protein_target = round(1.6 * lbm, 1)
    protein_compliant = log["protein_consumed"] >= protein_target

    # ── 6. Expected weight change ──────────────────────────────────────────
    deficit_so_far = weekly_budget - remaining_budget
    expected_weight_change = round(-deficit_so_far / 7700.0, 3)

    # ── 7. Guardrails ──────────────────────────────────────────────────────
    warnings = evaluate_guardrails(
        weekly_weight_loss_kg=0.0,
        weight_kg=current_weight,
        daily_protein_g=log["protein_consumed"],
    )

    return DashboardResponse(
        user_id=user_id,
        current_weight_kg=current_weight,
        weekly_budget_kcal=weekly_budget,
        remaining_budget_kcal=remaining_budget,
        calories_consumed_today=log["calories_consumed"],
        protein_consumed_today=log["protein_consumed"],
        protein_target_g=protein_target,
        protein_compliant=protein_compliant,
        expected_weight_change_kg=expected_weight_change,
        guardrail_warnings=warnings,
    )


@router.get("/{user_id}/avatar", response_model=AvatarMetrics)
async def get_avatar(user_id: str, authenticated_user_id: str = Depends(get_current_user)) -> AvatarMetrics:
    if user_id != authenticated_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    budget = get_weekly_budget_fields(user_id, str(week_start), ["total_budget", "remaining_budget"])
    if budget:
        deficit_so_far = budget["total_budget"] - budget["remaining_budget"]
        expected_change = round(-deficit_so_far / 7700.0, 3)
    else:
        expected_change = 0.0

    return AvatarMetrics(
        user_id=user["id"],
        height_cm=user["height_cm"],
        weight_kg=user["weight_kg"],
        body_fat=user["body_fat"],
        neck_cm=user.get("neck_cm"),
        waist_cm=user.get("waist_cm"),
        hip_cm=user.get("hip_cm"),
        expected_weight_change_kg=expected_change,
    )


@router.get("/{user_id}/history", response_model=HistoryResponse)
async def get_history(user_id: str, authenticated_user_id: str = Depends(get_current_user)) -> HistoryResponse:
    if user_id != authenticated_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    cutoff_date = date.today() - timedelta(days=14)

    weight_history = get_weight_logs_since(user_id, str(cutoff_date))
    calorie_history = get_daily_logs_since(user_id, str(cutoff_date))

    return HistoryResponse(
        weight_history=weight_history if weight_history else [],
        calorie_history=calorie_history if calorie_history else [],
    )
