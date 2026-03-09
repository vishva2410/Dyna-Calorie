"""
routers/auth.py — Registration and Login endpoints.

Wraps Supabase Auth for user sign-up and sign-in.
On registration, also inserts the metabolic profile into the `users` table
after an onboarding form submission (separate `POST /users/onboard` endpoint).
"""
from fastapi import APIRouter, HTTPException, status
from backend.models import RegisterRequest, LoginRequest, AuthResponse, OnboardingRequest
from backend.database import supabase_client, supabase_admin
from backend.engine import compute_full_metabolic_profile, calculate_body_fat_navy

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest) -> AuthResponse:
    """
    Creates a new Supabase Auth user.
    Returns the JWT access token for immediate login after registration.
    """
    try:
        response = supabase_client.auth.sign_up({
            "email": payload.email,
            "password": payload.password,
        })
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(exc)}",
        )

    if not response.session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration succeeded but no session was returned. Check email confirmation settings.",
        )

    return AuthResponse(
        access_token=response.session.access_token,
        user_id=response.user.id,
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest) -> AuthResponse:
    """
    Authenticates a user via Supabase Auth email/password.
    Returns a JWT access token for subsequent authenticated requests.
    """
    try:
        response = supabase_client.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password,
        })
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(exc)}",
        )

    if not response.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    return AuthResponse(
        access_token=response.session.access_token,
        user_id=response.user.id,
    )


@router.post("/onboard", status_code=status.HTTP_201_CREATED)
async def onboard(payload: OnboardingRequest) -> dict:
    """
    Called from the Flutter onboarding screen after registration.
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
        supabase_admin.table("users").insert({
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
        }).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Could not save user profile: {str(exc)}",
        )

    # ── 3. Seed the first weekly budget (current ISO week) ─────────────────
    from datetime import date, timedelta
    today = date.today()
    # Start of ISO week (Monday)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    try:
        supabase_admin.table("weekly_budgets").insert({
            "user_id":          payload.user_id,
            "start_date":       str(week_start),
            "end_date":         str(week_end),
            "total_budget":     profile["weekly_budget_kcal"],
            "remaining_budget": profile["weekly_budget_kcal"],
        }).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create weekly budget: {str(exc)}",
        )

    # ── 4. Also store initial weight log ───────────────────────────────────
    try:
        supabase_admin.table("weight_logs").insert({
            "user_id":   payload.user_id,
            "date":      str(today),
            "weight_kg": payload.weight_kg,
        }).execute()
    except Exception:
        pass  # Non-fatal: weight log might fail on duplicate

    return {
        "message": "Onboarding complete.",
        **profile,
    }
