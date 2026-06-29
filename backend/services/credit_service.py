from supabase import create_client
from backend.core.config import settings

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

async def check_and_deduct_credit(user_id: str) -> bool:
    """Verifica y descuenta 1 crédito. Retorna False si no hay créditos."""
    result = supabase.rpc('deduct_credit', {'p_user_id': user_id}).execute()
    return result.data

async def add_credits(user_id: str, credits: int, plan: str):
    """Agrega créditos después de pago exitoso."""
    supabase.rpc('add_credits', {
        'p_user_id': user_id,
        'p_credits': credits,
        'p_plan': plan
    }).execute()