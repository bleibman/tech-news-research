"""Quick sanity check — can we reach Supabase via PostgREST?"""
import httpx
from src.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

resp = httpx.get(
    f"{SUPABASE_URL}/rest/v1/articles?select=id&limit=1",
    headers={
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    },
    timeout=10.0,
)
print(f"Status: {resp.status_code}")
print(f"Body: {resp.text[:200]}")
