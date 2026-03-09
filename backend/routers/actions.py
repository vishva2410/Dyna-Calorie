"""
routers/actions.py — Special metabolic actions endpoint.

POST /action/refeed → Grants a structured refeed day allowing a temporary
caloric surplus without breaking the fat-gain threshold. The extra calories
for the refeed day are allocated, and the remaining weekly budget is adjusted
so the rest of the week compensates.
"""
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from backend.models import RefeedRequest, RefeedResponse
from backend.database import supabase_admin
from backend.auth_utils import get_current_user
from backend.engine import compute_full_metabolic_profile

router = APIRouter(prefix="/action", tags=["Actions"])

# A refeed day is capped at TDEE + 20% (maintenance + slight surplus for hormonal reset)
REFEED_SURPLUS_FACTOR = 0.20


@router.post("/refeed", response_model=RefeedResponse)
async def refeed(payload: RefeedRequest, authenticated_user_id: str = Depends(get_current_user)) -> RefeedResponse:
    """
    Activates a structured refeed day for the user.

    Logic:
    1. Calculate the refeed day calorie allowance = TDEE * (1 + REFEED_SURPLUS_FACTOR).
    2. Deduct the refeed allocation from the remaining weekly budget.
    3. Return the adjusted budget so Flutter can display the updated state.

    Design note: A refeed is intentional — it does NOT add calories to the weekly
    budget; it front-loads consumption. The remaining days tighten accordingly.
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

    # ── 3. Calculate refeed allowance (TDEE + 20%) ─────────────────────────
    refeed_calories = round(current_tdee * (1 + REFEED_SURPLUS_FACTOR), 2)

    # ── 4. Fetch active weekly budget ──────────────────────────────────────
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    budget_resp = (
        supabase_admin.table("weekly_budgets")
        .select("id, remaining_budget")
        .eq("user_id", payload.user_id)
        .eq("start_date", str(week_start))
        .single()
        .execute()
    )
    if not budget_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active weekly budget found.",
        )

    # ── 5. Deduct refeed calories from remaining budget ────────────────────
    remaining = budget_resp.data["remaining_budget"]
    adjusted_remaining = remaining - refeed_calories

    supabase_admin.table("weekly_budgets").update({
        "remaining_budget": adjusted_remaining
    }).eq("id", budget_resp.data["id"]).execute()

    return RefeedResponse(
        message=(
            f"Refeed day activated. Enjoy {refeed_calories:.0f} kcal today. "
            f"The remaining {adjusted_remaining:.0f} kcal are spread across the rest of your week."
        ),
        refeed_calories_kcal=refeed_calories,
        adjusted_remaining_budget_kcal=round(adjusted_remaining, 2),
    )
