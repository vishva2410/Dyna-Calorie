"""
routers/actions.py — Special metabolic actions endpoint.

POST /action/refeed → Grants a structured refeed day.
"""
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from backend.models import RefeedRequest, RefeedResponse
from backend.database_local import get_user, get_weekly_budget, update_weekly_budget_remaining
from backend.auth_utils import get_current_user
from backend.engine import compute_full_metabolic_profile

router = APIRouter(prefix="/action", tags=["Actions"])

REFEED_SURPLUS_FACTOR = 0.20


@router.post("/refeed", response_model=RefeedResponse)
async def refeed(payload: RefeedRequest, authenticated_user_id: str = Depends(get_current_user)) -> RefeedResponse:
    if payload.user_id != authenticated_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    # ── 1. Fetch user ──────────────────────────────────────────────────────
    user = get_user(payload.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # ── 2. Resolve current TDEE ────────────────────────────────────────────
    current_tdee = user.get("current_tdee")
    if not current_tdee:
        profile = compute_full_metabolic_profile(
            weight_kg=user["weight_kg"],
            body_fat=user["body_fat"],
            activity_level=user["activity_level"],
            goal=user["goal"],
            target_rate=user["target_rate"],
        )
        current_tdee = profile["tdee_kcal"]

    # ── 3. Calculate refeed allowance ──────────────────────────────────────
    refeed_calories = round(current_tdee * (1 + REFEED_SURPLUS_FACTOR), 2)

    # ── 4. Fetch active weekly budget ──────────────────────────────────────
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    budget = get_weekly_budget(payload.user_id, str(week_start))
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active weekly budget found.",
        )

    # ── 5. Deduct refeed calories ──────────────────────────────────────────
    remaining = budget["remaining_budget"]
    adjusted_remaining = remaining - refeed_calories

    update_weekly_budget_remaining(budget["id"], adjusted_remaining)

    return RefeedResponse(
        message=(
            f"Refeed day activated. Enjoy {refeed_calories:.0f} kcal today. "
            f"The remaining {adjusted_remaining:.0f} kcal are spread across the rest of your week."
        ),
        refeed_calories_kcal=refeed_calories,
        adjusted_remaining_budget_kcal=round(adjusted_remaining, 2),
    )
