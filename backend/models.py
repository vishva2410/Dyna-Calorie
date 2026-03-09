"""
models.py — Pydantic v2 request/response schemas for all API endpoints.
"""
from __future__ import annotations
import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, EmailStr


# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


# ══════════════════════════════════════════════════════════════════════════════
# USER / ONBOARDING
# ══════════════════════════════════════════════════════════════════════════════

class OnboardingRequest(BaseModel):
    """Sent from the onboarding screen after registration."""
    user_id: str
    age: int = Field(gt=0, lt=120)
    gender: Literal["male", "female", "other"]
    height_cm: float = Field(gt=0)
    weight_kg: float = Field(gt=0)
    neck_cm: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    body_fat: Optional[float] = Field(None, ge=0, lt=100)
    activity_level: float = Field(ge=1.0, le=2.5, description="Multiplier: 1.2 sedentary → 1.9 very active")
    goal: Literal["fat_loss", "maintenance", "muscle_gain"] = "fat_loss"
    target_rate: float = Field(gt=0, le=2.0, description="kg per week to lose/gain")


class UserProfile(BaseModel):
    """Full user profile returned from DB."""
    id: str
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    body_fat: float
    activity_level: float
    goal: str
    target_rate: float
    current_tdee: Optional[float]
    last_recalibration_date: Optional[datetime.date]


class AvatarMetrics(BaseModel):
    """Metrics specifically for generating the parametric 3D body representation."""
    user_id: str
    height_cm: float
    weight_kg: float
    body_fat: float
    neck_cm: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    expected_weight_change_kg: float


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

class DashboardResponse(BaseModel):
    user_id: str
    current_weight_kg: float
    weekly_budget_kcal: float
    remaining_budget_kcal: float
    calories_consumed_today: float
    protein_consumed_today: float
    protein_target_g: float           # 1.6 * LBM
    protein_compliant: bool           # True if today's protein >= target
    expected_weight_change_kg: float  # Based on remaining budget
    guardrail_warnings: list[str]


class WeightLogEntry(BaseModel):
    date: datetime.date
    weight_kg: float

class CalorieLogEntry(BaseModel):
    date: datetime.date
    calories_consumed: float
    protein_consumed: float

class HistoryResponse(BaseModel):
    weight_history: list[WeightLogEntry]
    calorie_history: list[CalorieLogEntry]


# ══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════════════════

class LogFoodRequest(BaseModel):
    user_id: str
    date: datetime.date = Field(default_factory=datetime.date.today)
    calories: float = Field(ge=0)
    protein_g: float = Field(ge=0)


class LogFoodResponse(BaseModel):
    message: str
    remaining_budget_kcal: float
    new_daily_target_kcal: float   # Budget evenly spread across remaining days
    guardrail_warnings: list[str]


class LogWeightRequest(BaseModel):
    user_id: str
    date: datetime.date = Field(default_factory=datetime.date.today)
    weight_kg: float = Field(gt=0)


class LogWeightResponse(BaseModel):
    message: str
    recalibrated: bool
    recalibration_summary: Optional[dict] = None  # Filled if recalibration ran
    new_weekly_budget_kcal: Optional[float] = None


# ══════════════════════════════════════════════════════════════════════════════
# ACTIONS
# ══════════════════════════════════════════════════════════════════════════════

class RefeedRequest(BaseModel):
    user_id: str


class RefeedResponse(BaseModel):
    message: str
    refeed_calories_kcal: float        # Allowed calories for the refeed day
    adjusted_remaining_budget_kcal: float  # Updated remaining budget after allocation
