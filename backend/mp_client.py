import mercadopago
from backend.api.settings import settings

def get_mp_client():
    access_token = settings.MP_ACCESS_TOKEN
    if not access_token:
        raise RuntimeError("MP_ACCESS_TOKEN no configurado")

    return mercadopago.SDK(access_token)