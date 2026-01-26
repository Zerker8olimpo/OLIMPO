from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import mercadopago

router = APIRouter(prefix="/web", tags=["Web Portal"])

# Configuración de plantillas (asumiendo ejecución desde la raíz del proyecto)
templates = Jinja2Templates(directory="backend/templates")

# Inicializar Mercado Pago
sdk = mercadopago.SDK("TEST-TU-TOKEN-AQUI")

def _create_preference(title: str, price: int, user_id: str):
    """Función auxiliar para generar preferencias de Mercado Pago."""
    preference_data = {
        "items": [
            {
                "title": title,
                "quantity": 1,
                "unit_price": price,
                "currency_id": "CLP"
            }
        ],
        "external_reference": user_id,
        "back_urls": {
            "success": "https://tu-dominio.com/web/success",
            "failure": "https://tu-dominio.com/web/failure",
            "pending": "https://tu-dominio.com/web/pending"
        },
        "auto_return": "approved",
    }
    preference_response = sdk.preference().create(preference_data)
    # Retornamos el init_point para redirigir al checkout
    return preference_response["response"].get("init_point")

@router.get("/precios")
async def get_pricing_page(request: Request, user_id: str):
    """Sirve la página de precios con los links de pago generados."""
    url_basic = _create_preference("Plan Básico", 19990, user_id)
    url_pro = _create_preference("Plan Profesional", 29990, user_id)
    url_enterprise = _create_preference("Plan Enterprise", 39990, user_id)
    
    return templates.TemplateResponse(
        "pricing.html", 
        {
            "request": request,
            "url_basic": url_basic,
            "url_pro": url_pro,
            "url_enterprise": url_enterprise
        }
    )