import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError(
        "Faltan las variables de entorno SUPABASE_URL o SUPABASE_ANON_KEY"
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)