"""
engine.py — Phase 1 metabolic engine re-exported as pure functions for FastAPI.

All functions accept raw floats from database rows so that no `User` dataclass
dependency bleeds into the API layer. The simulation-specific logic (print
statements, WeeklyTracker, etc.) is intentionally excluded here.
"""
import sys
import os
from typing import Literal

# ── Allow importing from project root regardless of working directory ──────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dynacalorie import (
    calculate_lbm,
    calculate_bmr,
    calculate_tdee,
    calculate_caloric_target,
    check_guardrails,
    calculate_body_fat_navy,
)


def compute_full_metabolic_profile(
    weight_kg: float,
    body_fat: float,
    activity_level: float,
    goal: Literal["fat_loss", "maintenance", "muscle_gain"],
    target_rate: float,
) -> dict:
    """
    Convenience function that runs the full metabolic calculation pipeline
    in one call. Returns a dict suitable for API responses and DB writes.
    """
    lbm = calculate_lbm(weight_kg, body_fat)
    bmr = calculate_bmr(lbm)
    tdee = calculate_tdee(bmr, activity_level)
    daily_target = calculate_caloric_target(tdee, goal, target_rate)
    weekly_budget = daily_target * 7

    return {
        "lbm_kg": round(lbm, 2),
        "bmr_kcal": round(bmr, 2),
        "tdee_kcal": round(tdee, 2),
        "daily_target_kcal": round(daily_target, 2),
        "weekly_budget_kcal": round(weekly_budget, 2),
    }


def run_recalibration(
    current_tdee: float,
    total_14_day_kcal_delta: float,
    actual_weight_change_kg: float,
) -> dict:
    """
    Runs the 14-day recalibration and returns the new TDEE and a human-readable
    summary of the outcome, suitable for an API response payload.
    """
    expected_weight_change_kg = total_14_day_kcal_delta / 7700.0
    threshold = max(abs(expected_weight_change_kg) * 0.10, 0.1)

    if actual_weight_change_kg < expected_weight_change_kg - threshold:
        # Lost more than expected → TDEE was underestimated, increase it
        new_tdee = current_tdee + 100.0
        direction = "increase"
    elif actual_weight_change_kg > expected_weight_change_kg + threshold:
        # Lost less than expected → TDEE was overestimated, decrease it
        new_tdee = current_tdee - 100.0
        direction = "decrease"

    return {
        "new_tdee_kcal": round(new_tdee, 2),
        "expected_weight_change_kg": round(expected_weight_change_kg, 3),
        "actual_weight_change_kg": round(actual_weight_change_kg, 3),
        "adjustment_direction": direction,
        "adjustment_amount_kcal": 100.0 if direction != "none" else 0.0,
    }


def evaluate_guardrails(
    weekly_weight_loss_kg: float,
    weight_kg: float,
    daily_protein_g: float,
) -> list[str]:
    """
    Thin wrapper around Phase 1 `check_guardrails`.
    Returns a list of warning strings (empty if all clear).
    """
    return check_guardrails(
        weekly_weight_loss_kg=weekly_weight_loss_kg,
        weight_kg=weight_kg,
        daily_protein_g=daily_protein_g,
    )
