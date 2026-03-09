"""
database.py — Supabase client initialization.

Two clients are provided:
  - `supabase_client`  → Anon key, used for auth operations.
  - `supabase_admin`   → Service-role key, bypasses RLS for server-side reads/writes.
"""
from supabase import create_client, Client
from backend.config import settings


# ── Anon client (respects RLS, passes user JWT to Supabase) ───────────────
supabase_client: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY,
)

# ── Admin / Service-role client (bypasses RLS for server-side operations) ─
supabase_admin: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY,
)
