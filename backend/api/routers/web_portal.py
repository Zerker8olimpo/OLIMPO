from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from mercadopago import SDK
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.api.db_deps import get_db
from backend.database.models.payment import Payment, PaymentProvider

router = APIRouter(prefix="/web", tags=["Web Portal"])

# Configuración de plantillas (asumiendo ejecución desde la raíz del proyecto)
templates = Jinja2Templates(directory="backend/templates")

# Inicializar Mercado Pago
sdk = SDK(settings.MP_ACCESS_TOKEN)

def _create_preference(title: str, price: int, payment_id: int):
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
        "external_reference": str(payment_id),
        "back_urls": {
            "success": f"{settings.PUBLIC_BASE_URL}/web/success",
            "failure": f"{settings.PUBLIC_BASE_URL}/web/failure",
            "pending": f"{settings.PUBLIC_BASE_URL}/web/pending"
        },
        "auto_return": "approved",
    }
    preference_response = sdk.preference().create(preference_data)
    # Retornamos el init_point para redirigir al checkout
    return preference_response["response"].get("init_point")

@router.get("/precios")
async def get_pricing_page(request: Request, user_id: str):
    """Sirve la página de precios con los links de pago generados."""
    return templates.TemplateResponse(
        "pricing.html", 
        {
            "request": request,
            "user_id": user_id
        }
    )

@router.get("/checkout")
async def process_checkout(plan: str, user_id: int, db: Session = Depends(get_db)):
    """Crea el registro de pago y redirige a Mercado Pago."""
    plans = {
        "basic": {"title": "Plan Básico", "price": 19990},
        "pro": {"title": "Plan Profesional", "price": 29990},
        "enterprise": {"title": "Plan Enterprise", "price": 39990}
    }
    
    if plan not in plans:
        raise HTTPException(status_code=400, detail="Plan inválido")

    # 1. Registrar intención de pago
    payment = Payment(
        user_id=user_id,
        provider=PaymentProvider.MERCADOPAGO,
        amount=plans[plan]["price"],
        status="created"
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    # 2. Crear preferencia en MP
    checkout_url = _create_preference(plans[plan]["title"], plans[plan]["price"], payment.id)
    return RedirectResponse(url=checkout_url)

@router.get("/success")
async def payment_success(request: Request):
    """Página de éxito tras el pago."""
    return {"status": "success", "message": "¡Pago aprobado! Ya puedes volver a la app."}

@router.get("/failure")
async def payment_failure(request: Request):
    """Página de error tras el pago."""
    return {"status": "error", "message": "El pago no pudo ser procesado."}