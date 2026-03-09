from dataclasses import dataclass
from typing import Literal
import math

@dataclass
class User:
    """
    Data structure representing a user's core metabolic profile and goals.
    """
    age: int
    gender: str  # e.g., 'male', 'female'
    height_cm: float
    weight_kg: float
    body_fat_percentage: float
    activity_level_multiplier: float
    goal_type: Literal['fat_loss', 'maintenance', 'muscle_gain']
    target_rate_of_change_kg_per_week: float


def calculate_lbm(weight_kg: float, body_fat_percentage: float) -> float:
    """
    Calculates Lean Body Mass (LBM) in kg.
    """
    return weight_kg * (1 - (body_fat_percentage / 100))


def calculate_body_fat_navy(gender: str, height_cm: float, neck_cm: float, waist_cm: float, hip_cm: float = 0.0) -> float:
    """
    Calculates Body Fat Percentage using the US Navy Method.
    Inputs are in centimeters.
    """
    try:
        if gender.lower() == 'male':
            bf = 495.0 / (1.0324 - 0.19077 * math.log10(waist_cm - neck_cm) + 0.15456 * math.log10(height_cm)) - 450.0
        elif gender.lower() == 'female':
            if hip_cm <= 0:
                raise ValueError("Hip measurement is required for females.")
            bf = 495.0 / (1.29579 - 0.35004 * math.log10(waist_cm + hip_cm - neck_cm) + 0.22100 * math.log10(height_cm)) - 450.0
        else:
            raise ValueError("Gender must be 'male' or 'female'")
    except ValueError:
        # Prevent math domain errors if log10 argument is <= 0 
        # (happens if waist <= neck, which is anatomically unlikely but possible in bad data)
        return 15.0 # fallback default

    return max(1.0, min(80.0, bf))  # Clamp between 1% and 80% for safety


def calculate_bmr(lbm_kg: float) -> float:
    """
    Calculates Basal Metabolic Rate (BMR) using the Katch-McArdle formula.
    """
    return 370 + (21.6 * lbm_kg)


def calculate_tdee(bmr: float, activity_level_multiplier: float) -> float:
    """
    Calculates Total Daily Energy Expenditure (TDEE).
    """
    return bmr * activity_level_multiplier


def calculate_caloric_target(tdee: float, goal_type: Literal['fat_loss', 'maintenance', 'muscle_gain'], target_rate_of_change_kg_per_week: float) -> float:
    """
    Calculates the required daily caloric target to hit a specific weight change goal.
    Assumes 1 kg of fat roughly equals 7700 kcal.
    """
    # Treat rate as absolute magnitude to ensure goal_type determines direction
    magnitude = abs(target_rate_of_change_kg_per_week)
    daily_kcal_delta = (magnitude * 7700) / 7.0

    if goal_type == 'fat_loss':
        return tdee - daily_kcal_delta
    elif goal_type == 'muscle_gain':
        return tdee + daily_kcal_delta
    elif goal_type == 'maintenance':
        return tdee
    else:
        raise ValueError(f"Unknown goal type: {goal_type}")


def check_guardrails(weekly_weight_loss_kg: float, weight_kg: float, daily_protein_g: float) -> list[str]:
    """
    Checks muscle protection and general safety guardrails.
    Returns a list of warning messages if any constraints are violated.
    """
    warnings = []
    
    # 1. Weekly weight loss should not exceed 1% of total body weight
    max_safe_weekly_loss = weight_kg * 0.01
    if weekly_weight_loss_kg > max_safe_weekly_loss:
        warnings.append(f"WARNING: Weekly weight loss ({weekly_weight_loss_kg:.2f} kg) exceeds 1% of body weight ({max_safe_weekly_loss:.2f} kg). Risk of muscle loss.")
        
    # 2. Daily protein intake must not fall below 1.6 * Total Body Weight
    min_protein_g = 1.6 * weight_kg
    if daily_protein_g < min_protein_g:
        warnings.append(f"WARNING: Daily protein intake ({daily_protein_g:.1f} g) is below the minimum recommended ({min_protein_g:.1f} g) for your body weight. Risk of muscle loss.")
        
    return warnings



class WeeklyTracker:
    """
    Manages a user's weekly caloric budget, dynamic daily targets, and rollovers.
    """
    def __init__(self, user: User, current_tdee: float):
        self.user = user
        self.current_tdee = current_tdee
        self.daily_target = calculate_caloric_target(
            tdee=current_tdee,
            goal_type=user.goal_type,
            target_rate_of_change_kg_per_week=user.target_rate_of_change_kg_per_week
        )
        self.weekly_budget = self.daily_target * 7
        self.remaining_budget = self.weekly_budget
        self.days_logged = 0

    def log_calories(self, calories_consumed: float, protein_consumed: float) -> tuple[float, list[str]]:
        """
        Logs a day's intake.
        Deducts consumed calories from the weekly budget and recalculates the target for remaining days.
        Returns the new daily target and any muscle protection warnings.
        """
        self.days_logged += 1
        self.remaining_budget -= calories_consumed

        # Calculate new daily target spread across remaining days
        remaining_days = 7 - self.days_logged
        if remaining_days > 0:
            new_daily_target = self.remaining_budget / remaining_days
        else:
            new_daily_target = 0.0 # Week is over

        warnings = check_guardrails(
            weekly_weight_loss_kg=0.0, # Checked separately on a weekly basis, not daily
            weight_kg=self.user.weight_kg,
            daily_protein_g=protein_consumed,
        )

        return new_daily_target, warnings

    def reset_week(self):
        """
        Resets the tracker for a new week.
        """
        self.weekly_budget = self.daily_target * 7
        self.remaining_budget = self.weekly_budget
        self.days_logged = 0


def recalibrate(user: User, actual_weight_change_kg: float, total_14_day_deficit_or_surplus_kcal: float, current_tdee: float) -> float:
    """
    The 14-Day Recalibration Engine.
    Adjusts the estimated TDEE if the actual weight change significantly deviates from the calculated expected change.
    """
    # Expected weight change: negative for deficit, positive for surplus
    expected_weight_change_kg = total_14_day_deficit_or_surplus_kcal / 7700.0

    print(f"[Recalibration Engine] Expected 14-day weight change: {expected_weight_change_kg:.2f} kg")
    print(f"[Recalibration Engine] Actual 14-day weight change: {actual_weight_change_kg:.2f} kg")
    
    # Check deviation
    deviation = actual_weight_change_kg - expected_weight_change_kg
    
    # Threshold for adjustment (10% of expected, or a small absolute value if expected is near 0)
    threshold = max(abs(expected_weight_change_kg) * 0.10, 0.1)

    new_tdee = current_tdee
    if actual_weight_change_kg < expected_weight_change_kg - threshold:
         # Lost more weight than expected (or gained less). Engine underestimated metabolism or overestimated intake.
         # Increase TDEE estimation by 100 kcal
         new_tdee += 100.0
         print(f"[Recalibration Engine] Outcome: Exceeded expectations. Increasing TDEE by 100 kcal/day.")
    elif actual_weight_change_kg > expected_weight_change_kg + threshold:
         # Lost less weight than expected (or gained more). Engine overestimated metabolism or underestimated intake.
         # Decrease TDEE estimation by 100 kcal
         new_tdee -= 100.0
         print(f"[Recalibration Engine] Outcome: Underperformed expectations. Decreasing TDEE by 100 kcal/day.")
    else:
         print("[Recalibration Engine] Outcome: Within expected variance. No TDEE adjustment needed.")
         
    return new_tdee


def run_simulation():
    """
    Runs a 60-day validation simulation of the DynaCalorie core metabolic engine.
    """
    print("=" * 60)
    print("   DynaCalorie AI - 60-Day Core Engine Validation")
    print("=" * 60)

    # 1. Initialize Test User
    test_user = User(
        age=21,
        gender='male',
        height_cm=169.0,
        weight_kg=77.0,
        body_fat_percentage=22.0,
        activity_level_multiplier=1.375, # Lightly active
        goal_type='fat_loss',
        target_rate_of_change_kg_per_week=0.5 # 0.5 kg loss per week
    )

    # Initial metabolic calculations
    lbm = calculate_lbm(test_user.weight_kg, test_user.body_fat_percentage)
    bmr = calculate_bmr(lbm)
    current_tdee = calculate_tdee(bmr, test_user.activity_level_multiplier)
    
    print(f"[Initial Stats] LBM: {lbm:.1f} kg | BMR: {bmr:.0f} kcal | TDEE: {current_tdee:.0f} kcal")
    
    # Init Tracking
    tracker = WeeklyTracker(user=test_user, current_tdee=current_tdee)
    print(f"[Initial Goal] Target: {test_user.target_rate_of_change_kg_per_week} kg/wk | Starting Daily target approx: {tracker.daily_target:.0f} kcal")
    print("-" * 60)

    total_14_day_deficit_or_surplus = 0.0
    weight_at_last_recalibration = test_user.weight_kg

    # 2. Simulation Loop (60 Days)
    for day in range(1, 61):
        # Determine if it's a weekend (day 6 or 7 of a week)
        day_of_week = ((day - 1) % 7) + 1
        
        # Simulate intake behavior
        if day_of_week in [6, 7]:
            # Weekend overeating
            consumed_calories = tracker.daily_target + 800
        else:
            # Weekday strict adherence
            # Let's add slight variance just for realism
            consumed_calories = tracker.daily_target - 50 
            
        # Simulate an occasional low protein day (to test guardrails)
        if day == 10:
            consumed_protein = 50.0  # Deliberately low to trigger warning
        else:
            consumed_protein = 150.0 # Adequate 

        # Log calories to tracker
        total_14_day_deficit_or_surplus += (consumed_calories - tracker.current_tdee)
        new_target, warnings_daily = tracker.log_calories(consumed_calories, consumed_protein)
        
        if warnings_daily:
            print(f"[Day {day}] " + " | ".join(warnings_daily))

        # End of week cleanup/guardrails
        if day_of_week == 7:
             # Weekly guardrail check - simulating weight change
             # Realistically, weight wouldn't change strictly according to math every single week, but for simulation let's simulate a standard progression.
             # On day 35, let's simulate excessive weight loss to trigger the guardrail
             simulated_weekly_loss = 0.5
             if day == 35:
                 simulated_weekly_loss = 1.0 # Exceeds 1% of 77kg (0.77kg)
             
             warnings_weekly = check_guardrails(
                 weekly_weight_loss_kg=simulated_weekly_loss,
                 weight_kg=test_user.weight_kg,
                 daily_protein_g=150, # Doesn't matter for this check
             )
             if warnings_weekly:
                 print(f"[End of Week {day//7}] " + " | ".join([w for w in warnings_weekly if 'Weekly weight loss' in w]))

             tracker.reset_week()

        # 14-Day Recalibration Check
        if day % 14 == 0:
            print(f"\n[{'-'*10} DAY {day} REPORT {'-'*10}]")
            print(f"Current Weight: {test_user.weight_kg:.1f} kg")
            print(f"Current Weekly Budget (Starting): {tracker.daily_target * 7:.0f} kcal (Avg {tracker.daily_target:.0f}/day)")
            
            # Simulate actual weight change
            # We'll make it under-perform expected on Day 14, over-perform on Day 28, hit target on Day 42.
            if day == 14:
                 # Underperformed (lost less than expected)
                 actual_weight_change = -0.5 # Total loss over 14 days
            elif day == 28:
                 # Overperformed (lost more than expected)
                 actual_weight_change = -1.5 
            else:
                 # Hit target roughly
                 actual_weight_change = total_14_day_deficit_or_surplus / 7700.0

            # Update User Weight
            test_user.weight_kg += actual_weight_change
            print(f"Recorded Weight Change: {actual_weight_change:.2f} kg. New Weight: {test_user.weight_kg:.1f} kg")

            # Run recalibration
            new_tdee = recalibrate(
                user=test_user,
                actual_weight_change_kg=actual_weight_change,
                total_14_day_deficit_or_surplus_kcal=total_14_day_deficit_or_surplus,
                current_tdee=current_tdee
            )
            
            if new_tdee != current_tdee:
                 print(f"-> Adjusted TDEE from {current_tdee:.0f} to {new_tdee:.0f} kcal.")
                 current_tdee = new_tdee
                 
                 # Reinitialize tracker with new TDEE to alter daily targets moving forward
                 tracker = WeeklyTracker(user=test_user, current_tdee=current_tdee)
                 print(f"-> Recalculated Daily Target: {tracker.daily_target:.0f} kcal/day")

            # Reset metrics for next recalibration period
            total_14_day_deficit_or_surplus = 0.0
            weight_at_last_recalibration = test_user.weight_kg
            print("-" * 43 + "\n")


if __name__ == "__main__":
    run_simulation()
