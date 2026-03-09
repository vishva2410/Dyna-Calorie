-- =============================================================
-- DynaCalorie AI - Supabase Database Schema
-- Run this in the Supabase SQL Editor to set up all tables.
-- =============================================================

-- ─────────────────────────────────────────────────────────────
-- TABLE: users
-- Stores each user's metabolic profile and current TDEE.
-- Links to Supabase Auth via auth.users(id).
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.users (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    age         INTEGER NOT NULL CHECK (age > 0 AND age < 120),
    gender      TEXT NOT NULL CHECK (gender IN ('male', 'female', 'other')),
    height_cm   FLOAT NOT NULL CHECK (height_cm > 0),
    weight_kg   FLOAT NOT NULL CHECK (weight_kg > 0),
    neck_cm     FLOAT,
    waist_cm    FLOAT,
    hip_cm      FLOAT,
    body_fat    FLOAT NOT NULL CHECK (body_fat >= 0 AND body_fat < 100),
    -- Activity level multiplier: 1.2 sedentary → 1.9 very active
    activity_level FLOAT NOT NULL DEFAULT 1.375,
    -- Goal: 'fat_loss', 'maintenance', 'muscle_gain'
    goal        TEXT NOT NULL DEFAULT 'fat_loss'
                    CHECK (goal IN ('fat_loss', 'maintenance', 'muscle_gain')),
    -- Target rate of change in kg/week (always positive; goal determines direction)
    target_rate FLOAT NOT NULL DEFAULT 0.5 CHECK (target_rate >= 0),
    -- Dynamically updated by the recalibration engine
    current_tdee FLOAT,
    -- Timestamp of the last 14-day recalibration
    last_recalibration_date DATE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- TABLE: weekly_budgets
-- One row per user per week. Tracks total and remaining budget.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.weekly_budgets (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    start_date       DATE NOT NULL,
    end_date         DATE NOT NULL,
    total_budget     FLOAT NOT NULL,   -- kcal budget for the entire week
    remaining_budget FLOAT NOT NULL,   -- kcal remaining after daily logs
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, start_date)
);

-- ─────────────────────────────────────────────────────────────
-- TABLE: daily_logs
-- One row per user per day for calorie and protein tracking.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.daily_logs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    date              DATE NOT NULL,
    calories_consumed FLOAT NOT NULL DEFAULT 0 CHECK (calories_consumed >= 0),
    protein_consumed  FLOAT NOT NULL DEFAULT 0 CHECK (protein_consumed >= 0),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, date)
);

-- ─────────────────────────────────────────────────────────────
-- TABLE: weight_logs
-- Historical weight entries. Drives the 14-day recalibration.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.weight_logs (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id   UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    date      DATE NOT NULL,
    weight_kg FLOAT NOT NULL CHECK (weight_kg > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, date)
);

-- ─────────────────────────────────────────────────────────────
-- Row Level Security (RLS)
-- Users can only read/write their own data.
-- ─────────────────────────────────────────────────────────────
ALTER TABLE public.users          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.weekly_budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_logs     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.weight_logs    ENABLE ROW LEVEL SECURITY;

-- users
CREATE POLICY "users_self_access" ON public.users
    FOR ALL USING (auth.uid() = id);

-- weekly_budgets
CREATE POLICY "budgets_self_access" ON public.weekly_budgets
    FOR ALL USING (auth.uid() = user_id);

-- daily_logs
CREATE POLICY "logs_self_access" ON public.daily_logs
    FOR ALL USING (auth.uid() = user_id);

-- weight_logs
CREATE POLICY "weight_self_access" ON public.weight_logs
    FOR ALL USING (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────
-- Convenience trigger: keep updated_at current
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_budgets_updated_at
    BEFORE UPDATE ON public.weekly_budgets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_logs_updated_at
    BEFORE UPDATE ON public.daily_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
