"""
routers/auth.py — Registration, Login, and Onboarding endpoints.

Uses local SQLite + bcrypt auth instead of Supabase.
"""
from fastapi import APIRouter, HTTPException, status
from backend.models import RegisterRequest, LoginRequest, AuthResponse, OnboardingRequest
from backend.database_local import (
    create_auth_user, get_auth_user_by_email, insert_user,
    insert_weekly_budget, upsert_weight_log, new_id,
)
from backend.auth_utils import hash_password, verify_password, create_access_token
from backend.engine import compute_full_metabolic_profile, calculate_body_fat_navy

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest) -> AuthResponse:
    """Creates a new user with local auth."""
    try:
        pw_hash = hash_password(payload.password)
        user_id = create_auth_user(payload.email, pw_hash)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    token = create_access_token(user_id)
    return AuthResponse(access_token=token, user_id=user_id)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest) -> AuthResponse:
    """Authenticates a user via email/password."""
    user = get_auth_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(user["id"])
    return AuthResponse(access_token=token, user_id=user["id"])


@router.post("/onboard", status_code=status.HTTP_201_CREATED)
async def onboard(payload: OnboardingRequest) -> dict:
    """
    Called from the onboarding screen after registration.
    Inserts a metabolic profile row for the user and calculates their initial
    TDEE + weekly budget, then seeds the first weekly_budgets row.
    """
    # ── 0. Calculate Body Fat if not provided directly ───────────────────
    body_fat = payload.body_fat
    if body_fat is None:
        if payload.neck_cm and payload.waist_cm:
            body_fat = calculate_body_fat_navy(
                gender=payload.gender,
                height_cm=payload.height_cm,
                neck_cm=payload.neck_cm,
                waist_cm=payload.waist_cm,
                hip_cm=payload.hip_cm or 0.0
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide either body_fat OR (neck_cm, waist_cm, and hip_cm for females)."
            )

    # ── 1. Compute full metabolic profile ─────────────────────────────────
    profile = compute_full_metabolic_profile(
        weight_kg=payload.weight_kg,
        body_fat=body_fat,
        activity_level=payload.activity_level,
        goal=payload.goal,
        target_rate=payload.target_rate,
    )

    # ── 2. Insert user row ─────────────────────────────────────────────────
    try:
        insert_user({
            "id":             payload.user_id,
            "age":            payload.age,
            "gender":         payload.gender,
            "height_cm":      payload.height_cm,
            "weight_kg":      payload.weight_kg,
            "neck_cm":        payload.neck_cm,
            "waist_cm":       payload.waist_cm,
            "hip_cm":         payload.hip_cm,
            "body_fat":       body_fat,
            "activity_level": payload.activity_level,
            "goal":           payload.goal,
            "target_rate":    payload.target_rate,
            "current_tdee":   profile["tdee_kcal"],
        })
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Could not save user profile: {str(exc)}",
        )

    # ── 3. Seed the first weekly budget (current ISO week) ─────────────────
    from datetime import date, timedelta
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    try:
        insert_weekly_budget({
            "user_id":          payload.user_id,
            "start_date":       str(week_start),
            "end_date":         str(week_end),
            "total_budget":     profile["weekly_budget_kcal"],
            "remaining_budget": profile["weekly_budget_kcal"],
        })
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create weekly budget: {str(exc)}",
        )

    # ── 4. Also store initial weight log ───────────────────────────────────
    try:
        upsert_weight_log(payload.user_id, str(today), payload.weight_kg)
    except Exception:
        pass  # Non-fatal

    return {
        "message": "Onboarding complete.",
        **profile,
    }
