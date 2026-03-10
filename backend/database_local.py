"""
database_local.py — SQLite database layer replacing Supabase.

Provides a simple synchronous SQLite interface that mirrors the Supabase
query patterns used throughout the routers. All data is stored in a local
file (dynacalorie.db) so the app works fully offline.
"""
import sqlite3
import uuid
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "dynacalorie.db")

def get_db() -> sqlite3.Connection:
    """Returns a new SQLite connection with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Creates all tables if they don't exist."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS auth_users (
            id          TEXT PRIMARY KEY,
            email       TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS users (
            id               TEXT PRIMARY KEY,
            age              INTEGER NOT NULL,
            gender           TEXT NOT NULL,
            height_cm        REAL NOT NULL,
            weight_kg        REAL NOT NULL,
            neck_cm          REAL,
            waist_cm         REAL,
            hip_cm           REAL,
            body_fat         REAL NOT NULL,
            activity_level   REAL NOT NULL DEFAULT 1.375,
            goal             TEXT NOT NULL DEFAULT 'fat_loss',
            target_rate      REAL NOT NULL DEFAULT 0.5,
            current_tdee     REAL,
            last_recalibration_date TEXT,
            created_at       TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS weekly_budgets (
            id               TEXT PRIMARY KEY,
            user_id          TEXT NOT NULL,
            start_date       TEXT NOT NULL,
            end_date         TEXT NOT NULL,
            total_budget     REAL NOT NULL,
            remaining_budget REAL NOT NULL,
            created_at       TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at       TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (user_id, start_date)
        );

        CREATE TABLE IF NOT EXISTS daily_logs (
            id                TEXT PRIMARY KEY,
            user_id           TEXT NOT NULL,
            date              TEXT NOT NULL,
            calories_consumed REAL NOT NULL DEFAULT 0,
            protein_consumed  REAL NOT NULL DEFAULT 0,
            created_at        TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at        TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (user_id, date)
        );

        CREATE TABLE IF NOT EXISTS weight_logs (
            id        TEXT PRIMARY KEY,
            user_id   TEXT NOT NULL,
            date      TEXT NOT NULL,
            weight_kg REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (user_id, date)
        );

        CREATE TABLE IF NOT EXISTS food_items (
            id           TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            category     TEXT NOT NULL DEFAULT 'general',
            calories     REAL NOT NULL,
            protein_g    REAL NOT NULL DEFAULT 0,
            carbs_g      REAL NOT NULL DEFAULT 0,
            fat_g        REAL NOT NULL DEFAULT 0,
            serving_size TEXT NOT NULL DEFAULT '100g'
        );

        CREATE TABLE IF NOT EXISTS meal_entries (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL,
            date         TEXT NOT NULL,
            meal_type    TEXT NOT NULL DEFAULT 'snack',
            food_name    TEXT NOT NULL,
            servings     REAL NOT NULL DEFAULT 1,
            calories     REAL NOT NULL,
            protein_g    REAL NOT NULL DEFAULT 0,
            carbs_g      REAL NOT NULL DEFAULT 0,
            fat_g        REAL NOT NULL DEFAULT 0,
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()
    seed_food_items()


def new_id() -> str:
    """Generates a new UUID string."""
    return str(uuid.uuid4())


# ── Auth helpers ──────────────────────────────────────────────────────────────

def create_auth_user(email: str, password_hash: str) -> str:
    """Creates a new auth user. Returns the user ID."""
    conn = get_db()
    user_id = new_id()
    try:
        conn.execute(
            "INSERT INTO auth_users (id, email, password_hash) VALUES (?, ?, ?)",
            (user_id, email, password_hash),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("A user with this email already exists.")
    conn.close()
    return user_id


def get_auth_user_by_email(email: str) -> dict | None:
    """Returns the auth user row or None."""
    conn = get_db()
    row = conn.execute("SELECT * FROM auth_users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── User profile ──────────────────────────────────────────────────────────────

def insert_user(data: dict):
    """Inserts a user profile row."""
    conn = get_db()
    conn.execute(
        """INSERT INTO users (id, age, gender, height_cm, weight_kg, neck_cm, waist_cm,
           hip_cm, body_fat, activity_level, goal, target_rate, current_tdee)
           VALUES (:id, :age, :gender, :height_cm, :weight_kg, :neck_cm, :waist_cm,
           :hip_cm, :body_fat, :activity_level, :goal, :target_rate, :current_tdee)""",
        data,
    )
    conn.commit()
    conn.close()


def get_user(user_id: str) -> dict | None:
    """Returns the user profile or None."""
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_fields(user_id: str, fields: list[str]) -> dict | None:
    """Returns specific fields from the user profile."""
    cols = ", ".join(fields)
    conn = get_db()
    row = conn.execute(f"SELECT {cols} FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_user(user_id: str, data: dict):
    """Updates user profile fields."""
    sets = ", ".join(f"{k} = ?" for k in data)
    vals = list(data.values()) + [user_id]
    conn = get_db()
    conn.execute(f"UPDATE users SET {sets}, updated_at = datetime('now') WHERE id = ?", vals)
    conn.commit()
    conn.close()


# ── Weekly budgets ────────────────────────────────────────────────────────────

def get_weekly_budget(user_id: str, start_date: str) -> dict | None:
    """Returns the weekly budget for a given start date."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM weekly_budgets WHERE user_id = ? AND start_date = ?",
        (user_id, start_date),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_weekly_budget_fields(user_id: str, start_date: str, fields: list[str]) -> dict | None:
    """Returns specific fields from the weekly budget."""
    cols = ", ".join(fields)
    conn = get_db()
    row = conn.execute(
        f"SELECT {cols} FROM weekly_budgets WHERE user_id = ? AND start_date = ?",
        (user_id, start_date),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def insert_weekly_budget(data: dict):
    """Inserts a weekly budget row."""
    conn = get_db()
    data.setdefault("id", new_id())
    conn.execute(
        """INSERT INTO weekly_budgets (id, user_id, start_date, end_date, total_budget, remaining_budget)
           VALUES (:id, :user_id, :start_date, :end_date, :total_budget, :remaining_budget)""",
        data,
    )
    conn.commit()
    conn.close()


def upsert_weekly_budget(data: dict):
    """Inserts or replaces a weekly budget row."""
    conn = get_db()
    data.setdefault("id", new_id())
    conn.execute(
        """INSERT INTO weekly_budgets (id, user_id, start_date, end_date, total_budget, remaining_budget)
           VALUES (:id, :user_id, :start_date, :end_date, :total_budget, :remaining_budget)
           ON CONFLICT(user_id, start_date) DO UPDATE SET
               total_budget = excluded.total_budget,
               remaining_budget = excluded.remaining_budget,
               end_date = excluded.end_date,
               updated_at = datetime('now')""",
        data,
    )
    conn.commit()
    conn.close()


def update_weekly_budget_remaining(budget_id: str, remaining: float):
    """Updates the remaining budget amount."""
    conn = get_db()
    conn.execute(
        "UPDATE weekly_budgets SET remaining_budget = ?, updated_at = datetime('now') WHERE id = ?",
        (remaining, budget_id),
    )
    conn.commit()
    conn.close()


def get_budgets_since(user_id: str, start_date: str) -> list[dict]:
    """Returns all budgets with start_date >= the given date."""
    conn = get_db()
    rows = conn.execute(
        "SELECT total_budget, remaining_budget FROM weekly_budgets WHERE user_id = ? AND start_date >= ?",
        (user_id, start_date),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Daily logs ────────────────────────────────────────────────────────────────

def get_daily_log(user_id: str, date: str) -> dict | None:
    """Returns today's daily log or None."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM daily_logs WHERE user_id = ? AND date = ?",
        (user_id, date),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_daily_log_fields(user_id: str, date: str, fields: list[str]) -> dict | None:
    """Returns specific fields from the daily log."""
    cols = ", ".join(fields)
    conn = get_db()
    row = conn.execute(
        f"SELECT {cols} FROM daily_logs WHERE user_id = ? AND date = ?",
        (user_id, date),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_daily_log(user_id: str, date: str, calories: float, protein: float):
    """Creates or updates a daily log entry."""
    conn = get_db()
    existing = conn.execute(
        "SELECT id, calories_consumed, protein_consumed FROM daily_logs WHERE user_id = ? AND date = ?",
        (user_id, date),
    ).fetchone()

    if existing:
        new_cal = existing["calories_consumed"] + calories
        new_pro = existing["protein_consumed"] + protein
        conn.execute(
            "UPDATE daily_logs SET calories_consumed = ?, protein_consumed = ?, updated_at = datetime('now') WHERE id = ?",
            (new_cal, new_pro, existing["id"]),
        )
        kcal_delta = calories
    else:
        conn.execute(
            "INSERT INTO daily_logs (id, user_id, date, calories_consumed, protein_consumed) VALUES (?, ?, ?, ?, ?)",
            (new_id(), user_id, date, calories, protein),
        )
        new_cal = calories
        new_pro = protein
        kcal_delta = calories

    conn.commit()
    conn.close()
    return new_cal, new_pro, kcal_delta


def get_daily_logs_since(user_id: str, cutoff_date: str) -> list[dict]:
    """Returns daily logs since a cutoff date."""
    conn = get_db()
    rows = conn.execute(
        "SELECT date, calories_consumed, protein_consumed FROM daily_logs WHERE user_id = ? AND date >= ? ORDER BY date ASC",
        (user_id, cutoff_date),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Weight logs ───────────────────────────────────────────────────────────────

def upsert_weight_log(user_id: str, date: str, weight_kg: float):
    """Creates or updates a weight log entry."""
    conn = get_db()
    conn.execute(
        """INSERT INTO weight_logs (id, user_id, date, weight_kg)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, date) DO UPDATE SET weight_kg = excluded.weight_kg""",
        (new_id(), user_id, date, weight_kg),
    )
    conn.commit()
    conn.close()


def get_latest_weight(user_id: str) -> float | None:
    """Returns the most recent weight entry."""
    conn = get_db()
    row = conn.execute(
        "SELECT weight_kg FROM weight_logs WHERE user_id = ? ORDER BY date DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return row["weight_kg"] if row else None


def get_oldest_weight_log(user_id: str) -> dict | None:
    """Returns the oldest weight log entry."""
    conn = get_db()
    row = conn.execute(
        "SELECT date, weight_kg FROM weight_logs WHERE user_id = ? ORDER BY date ASC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_weight_before_date(user_id: str, date: str) -> dict | None:
    """Returns the most recent weight log on or before a given date."""
    conn = get_db()
    row = conn.execute(
        "SELECT weight_kg FROM weight_logs WHERE user_id = ? AND date <= ? ORDER BY date DESC LIMIT 1",
        (user_id, date),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_weight_logs_since(user_id: str, cutoff_date: str) -> list[dict]:
    """Returns weight logs since a cutoff date."""
    conn = get_db()
    rows = conn.execute(
        "SELECT date, weight_kg FROM weight_logs WHERE user_id = ? AND date >= ? ORDER BY date ASC",
        (user_id, cutoff_date),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Food database ─────────────────────────────────────────────────────────────

FOOD_DATA = [
    # (name, category, calories, protein, carbs, fat, serving)
    ("Chicken Breast (grilled)", "protein", 165, 31, 0, 3.6, "100g"),
    ("Salmon (baked)", "protein", 208, 20, 0, 13, "100g"),
    ("Egg (whole, boiled)", "protein", 78, 6.3, 0.6, 5.3, "1 large"),
    ("Egg Whites", "protein", 17, 3.6, 0.2, 0.1, "1 large"),
    ("Greek Yogurt (plain)", "dairy", 100, 17, 6, 0.7, "170g"),
    ("Whey Protein Shake", "protein", 120, 24, 3, 1, "1 scoop"),
    ("Tuna (canned)", "protein", 116, 25.5, 0, 0.8, "100g"),
    ("Turkey Breast", "protein", 135, 30, 0, 0.7, "100g"),
    ("Tofu (firm)", "protein", 144, 17, 3, 8, "100g"),
    ("Paneer", "protein", 265, 18, 1.2, 20, "100g"),
    ("Shrimp", "protein", 99, 24, 0.2, 0.3, "100g"),
    ("Protein Bar", "snacks", 210, 20, 22, 7, "1 bar"),

    ("White Rice (cooked)", "grains", 130, 2.7, 28, 0.3, "100g"),
    ("Brown Rice (cooked)", "grains", 123, 2.6, 26, 1, "100g"),
    ("Oatmeal", "grains", 154, 5, 27, 2.6, "1 cup cooked"),
    ("Whole Wheat Bread", "grains", 69, 3.6, 12, 1.1, "1 slice"),
    ("Pasta (cooked)", "grains", 131, 5, 25, 1.1, "100g"),
    ("Quinoa (cooked)", "grains", 120, 4.4, 21, 1.9, "100g"),
    ("Chapati / Roti", "grains", 104, 3.3, 18, 2.6, "1 piece"),
    ("Corn Tortilla", "grains", 52, 1.4, 11, 0.7, "1 piece"),

    ("Banana", "fruits", 105, 1.3, 27, 0.4, "1 medium"),
    ("Apple", "fruits", 95, 0.5, 25, 0.3, "1 medium"),
    ("Blueberries", "fruits", 85, 1.1, 21, 0.5, "1 cup"),
    ("Orange", "fruits", 62, 1.2, 15, 0.2, "1 medium"),
    ("Avocado", "fruits", 240, 3, 12, 22, "1 whole"),
    ("Mango", "fruits", 99, 1.4, 25, 0.6, "1 cup"),

    ("Broccoli", "vegetables", 55, 3.7, 11, 0.6, "1 cup"),
    ("Spinach (raw)", "vegetables", 7, 0.9, 1.1, 0.1, "1 cup"),
    ("Sweet Potato", "vegetables", 103, 2.3, 24, 0.1, "1 medium"),
    ("Mixed Salad", "vegetables", 20, 1.5, 3.5, 0.3, "1 cup"),
    ("Carrot", "vegetables", 25, 0.6, 6, 0.1, "1 medium"),

    ("Almonds", "snacks", 164, 6, 6, 14, "28g"),
    ("Peanut Butter", "snacks", 188, 8, 6, 16, "2 tbsp"),
    ("Dark Chocolate (70%)", "snacks", 170, 2.2, 13, 12, "30g"),
    ("Trail Mix", "snacks", 175, 5, 16, 11, "30g"),
    ("Granola Bar", "snacks", 190, 3, 29, 7, "1 bar"),
    ("Rice Cake", "snacks", 35, 0.7, 7.3, 0.3, "1 cake"),

    ("Whole Milk", "dairy", 149, 8, 12, 8, "1 cup"),
    ("Skim Milk", "dairy", 83, 8.3, 12, 0.2, "1 cup"),
    ("Cheddar Cheese", "dairy", 113, 7, 0.4, 9.3, "28g"),
    ("Cottage Cheese", "dairy", 206, 28, 6.2, 9, "1 cup"),
    ("Butter", "dairy", 102, 0.1, 0, 11.5, "1 tbsp"),

    ("Olive Oil", "fats", 119, 0, 0, 13.5, "1 tbsp"),
    ("Coconut Oil", "fats", 121, 0, 0, 13.5, "1 tbsp"),

    ("Coffee (black)", "beverages", 2, 0.3, 0, 0, "1 cup"),
    ("Orange Juice", "beverages", 112, 1.7, 26, 0.5, "1 cup"),
    ("Coca-Cola", "beverages", 140, 0, 39, 0, "355ml"),
    ("Green Smoothie", "beverages", 150, 4, 30, 2, "1 cup"),

    ("Pizza Slice (cheese)", "meals", 285, 12, 36, 10, "1 slice"),
    ("Chicken Biryani", "meals", 350, 18, 42, 12, "1 cup"),
    ("Caesar Salad", "meals", 220, 8, 12, 16, "1 bowl"),
    ("Burrito Bowl", "meals", 420, 22, 48, 15, "1 bowl"),
    ("Grilled Cheese Sandwich", "meals", 366, 14, 28, 23, "1 sandwich"),
    ("Dal (lentils cooked)", "meals", 116, 9, 20, 0.4, "1 cup"),
    ("Chicken Tikka", "meals", 180, 25, 5, 6, "100g"),
]


def seed_food_items():
    """Seeds the food_items table with common foods if empty."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM food_items").fetchone()[0]
    if count > 0:
        conn.close()
        return
    for name, cat, cal, pro, carbs, fat, serving in FOOD_DATA:
        conn.execute(
            "INSERT INTO food_items (id, name, category, calories, protein_g, carbs_g, fat_g, serving_size) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id(), name, cat, cal, pro, carbs, fat, serving),
        )
    conn.commit()
    conn.close()


def search_foods(query: str) -> list[dict]:
    """Searches food_items by name (case-insensitive partial match)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, category, calories, protein_g, carbs_g, fat_g, serving_size FROM food_items WHERE name LIKE ? LIMIT 20",
        (f"%{query}%",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_foods() -> list[dict]:
    """Returns all food items."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, category, calories, protein_g, carbs_g, fat_g, serving_size FROM food_items ORDER BY category, name",
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_meal_entry(user_id: str, date: str, meal_type: str, food_name: str,
                   servings: float, calories: float, protein_g: float,
                   carbs_g: float, fat_g: float) -> str:
    """Adds a meal entry and returns its ID."""
    entry_id = new_id()
    conn = get_db()
    conn.execute(
        """INSERT INTO meal_entries (id, user_id, date, meal_type, food_name, servings, calories, protein_g, carbs_g, fat_g)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (entry_id, user_id, date, meal_type, food_name, servings, calories, protein_g, carbs_g, fat_g),
    )
    conn.commit()
    conn.close()
    return entry_id


def get_meal_entries_for_date(user_id: str, date: str) -> list[dict]:
    """Returns all meal entries for a given date."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, meal_type, food_name, servings, calories, protein_g, carbs_g, fat_g, created_at FROM meal_entries WHERE user_id = ? AND date = ? ORDER BY created_at ASC",
        (user_id, date),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_meal_entry(entry_id: str, user_id: str) -> bool:
    """Deletes a meal entry. Returns True if deleted."""
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM meal_entries WHERE id = ? AND user_id = ?",
        (entry_id, user_id),
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted
