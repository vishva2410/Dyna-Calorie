import pytest
from dynacalorie import (
    calculate_lbm,
    calculate_bmr,
    calculate_tdee,
    calculate_caloric_target,
    calculate_body_fat_navy
)
from backend.engine import run_recalibration, evaluate_guardrails

def test_calculate_lbm():
    # 100kg person with 20% body fat = 80kg LBM
    assert calculate_lbm(100.0, 20.0) == 80.0
    # Edge case: 0% body fat
    assert calculate_lbm(50.0, 0.0) == 50.0

def test_calculate_tdee():
    # Katch-McArdle: 370 + (21.6 * LBM)
    # 80kg LBM * 21.6 = 1728 + 370 = 2098 BMR
    # 2098 * 1.55 (activity) = 3251.9 TDEE
    bmr = calculate_bmr(80.0)
    tdee = calculate_tdee(bmr, 1.55)
    assert tdee == 3251.9

def test_calculate_caloric_target():
    # Fat loss: Needs roughly 7700 kcal deficit per kg of fat
    # Target 0.5kg/week = 3850 deficit / week = 550 deficit / day
    tdee = 2500.0
    # Should be 2500 - 550 = 1950
    target = calculate_caloric_target(tdee, "fat_loss", 0.5)
    assert target == pytest.approx(1950.0, abs=1.0)
    
    # Muscle gain: Target 0.25kg/week = 1925 surplus / week = ~275 surplus / day
    # Should be 2500 + 275 = 2775
    target_gain = calculate_caloric_target(tdee, "muscle_gain", 0.25)
    assert target_gain == pytest.approx(2775.0, abs=1.0)
    
    # Maintenance should equal TDEE
    target_maint = calculate_caloric_target(tdee, "maintenance", 0.0)
    assert target_maint == tdee

def test_run_recalibration():
    # Simulate someone who should have lost 1kg based on their deficit, but lost 0kg
    # Total deficit = 7700 kcal (predicted -1kg)
    # Actual weight change = 0kg
    # Expected weight change = -1.0kg
    # Actual (0.0) > Expected (-1.0) + threshold(0.1) -> Lost less than expected
    # Recalibration logic flatly drops TDEE by 100 kcal.
    current_tdee = 2500.0
    res = run_recalibration(current_tdee, total_14_day_kcal_delta=-7700.0, actual_weight_change_kg=0.0)
    
    assert res["new_tdee_kcal"] == 2400.0
    assert res["expected_weight_change_kg"] == -1.0
    assert res["adjustment_direction"] == "decrease"

def test_evaluate_guardrails():
    # Normal user losing safe amount of weight with good protein
    warnings = evaluate_guardrails(0.5, 80.0, 150.0)
    assert len(warnings) == 0
    
    # Weight loss too fast (>1% of bw)
    # 80 * 0.01 = 0.8
    warnings = evaluate_guardrails(1.5, 80.0, 150.0)
    assert any("exceeds 1%" in w for w in warnings)
    
    # Low protein (<1.6g/kg)
    # 80 * 1.6 = 128g
    warnings = evaluate_guardrails(0.0, 80.0, 100.0)
    assert any("below the minimum recommended" in w for w in warnings)
