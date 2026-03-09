"""
routers/dashboard.py — GET /dashboard/{user_id}

Returns the user's current weekly budget, remaining calories, today's intake,
protein compliance, and guardrail warnings.
"""
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from backend.models import DashboardResponse, AvatarMetrics, HistoryResponse
from backend.database import supabase_admin
from backend.auth_utils import get_current_user
from backend.engine import compute_full_metabolic_profile, evaluate_guardrails
from dynacalorie import calculate_lbm

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/{user_id}", response_model=DashboardResponse)
async def get_dashboard(user_id: str, authenticated_user_id: str = Depends(get_current_user)) -> DashboardResponse:
    """
    Aggregates all data needed for the main Flutter dashboard screen into a
    single, efficient API call.
    """
    if user_id != authenticated_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user's data.")
    # ── 1. Fetch user profile ──────────────────────────────────────────────
    user_resp = (
        supabase_admin.table("users")
        .select("*")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not user_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user = user_resp.data

    # ── 2. Fetch active weekly budget ──────────────────────────────────────
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)

    budget_resp = (
        supabase_admin.table("weekly_budgets")
        .select("*")
        .eq("user_id", user_id)
        .eq("start_date", str(week_start))
        .single()
        .execute()
    )

    if not budget_resp.data:
        # Seed a budget if one doesn't exist for this week
        profile = compute_full_metabolic_profile(
            weight_kg=user["weight_kg"],
            body_fat=user["body_fat"],
            activity_level=user["activity_level"],
            goal=user["goal"],
            target_rate=user["target_rate"],
        )
        supabase_admin.table("weekly_budgets").insert({
            "user_id":          user_id,
            "start_date":       str(week_start),
            "end_date":         str(week_end),
            "total_budget":     profile["weekly_budget_kcal"],
            "remaining_budget": profile["weekly_budget_kcal"],
        }).execute()
        weekly_budget = profile["weekly_budget_kcal"]
        remaining_budget = weekly_budget
    else:
        weekly_budget = budget_resp.data["total_budget"]
        remaining_budget = budget_resp.data["remaining_budget"]

    # ── 3. Fetch today's food log (if exists) ──────────────────────────────
    log_resp = (
        supabase_admin.table("daily_logs")
        .select("calories_consumed, protein_consumed")
        .eq("user_id", user_id)
        .eq("date", str(today))
        .execute()
    )
    log = log_resp.data[0] if log_resp.data else {"calories_consumed": 0.0, "protein_consumed": 0.0}

    # ── 4. Latest weight ───────────────────────────────────────────────────
    weight_resp = (
        supabase_admin.table("weight_logs")
        .select("weight_kg")
        .eq("user_id", user_id)
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    current_weight = (
        weight_resp.data[0]["weight_kg"] if weight_resp.data else user["weight_kg"]
    )

    # ── 5. Protein target and compliance ──────────────────────────────────
    lbm = calculate_lbm(current_weight, user["body_fat"])
    protein_target = round(1.6 * lbm, 1)
    protein_compliant = log["protein_consumed"] >= protein_target

    # ── 6. Expected weight change based on remaining budget ────────────────
    #    Deficit = total_budget - remaining_budget (kcal burned beyond target)
    deficit_so_far = weekly_budget - remaining_budget
    expected_weight_change = round(-deficit_so_far / 7700.0, 3)

    # ── 7. Guardrails ──────────────────────────────────────────────────────
    warnings = evaluate_guardrails(
        weekly_weight_loss_kg=0.0,   # Handled in weight log endpoint
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
    """
    Returns metrics specifically used to morph the pre-rendered 3D body avatar.
    Includes tape measurements and the expected weekly weight change.
    """
    if user_id != authenticated_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user's data.")
    user_resp = (
        supabase_admin.table("users")
        .select("*")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not user_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user = user_resp.data

    # Fetch active weekly budget to compute expected change
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    budget_resp = (
        supabase_admin.table("weekly_budgets")
        .select("total_budget, remaining_budget")
        .eq("user_id", user_id)
        .eq("start_date", str(week_start))
        .single()
        .execute()
    )
    if budget_resp.data:
        deficit_so_far = budget_resp.data["total_budget"] - budget_resp.data["remaining_budget"]
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
    """
    Returns the last 14 days of weight and calorie logs for generating charts.
    """
    if user_id != authenticated_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user's data.")
    cutoff_date = date.today() - timedelta(days=14)

    weight_resp = (
        supabase_admin.table("weight_logs")
        .select("date, weight_kg")
        .eq("user_id", user_id)
        .gte("date", str(cutoff_date))
        .order("date", desc=False)
        .execute()
    )

    log_resp = (
        supabase_admin.table("daily_logs")
        .select("date, calories_consumed, protein_consumed")
        .eq("user_id", user_id)
        .gte("date", str(cutoff_date))
        .order("date", desc=False)
        .execute()
    )

    return HistoryResponse(
        weight_history=weight_resp.data if weight_resp.data else [],
        calorie_history=log_resp.data if log_resp.data else []
    )
