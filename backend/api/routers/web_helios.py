import logging
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from backend.services.credit_service import check_and_deduct_credit

logger = logging.getLogger("olimpo.auth")
router = APIRouter(prefix="/web", tags=["web"])


# ── Schemas de entrada (basados en el motor real) ──────────────────

class WebHeliosRequest(BaseModel):
    model: str           # "epsilon" | "sigma" | "poseidon"
    market_id: str
    product_id: str
    historical_data: List[int]
    periodos: int = 6
    # Epsilon
    margen_bruto_pct: Optional[float] = None
    horizonte_meses: int = 3
    # Sigma
    costo_unitario: Optional[float] = None
    costo_pedido: Optional[float] = None
    costo_mantencion_pct: Optional[float] = None
    stock_actual: Optional[float] = None
    # Poseidón
    inventario_inicial_tanque1: Optional[float] = None
    inventario_inicial_tanque2: Optional[float] = None
    capacidad_max_mensual: Optional[int] = None
    capacidad_tanque_1: Optional[int] = None
    capacidad_tanque_2: Optional[int] = None
    cobertura_objetivo: Optional[float] = 1.0
    cantidad_clientes: Optional[int] = None

# ── Adaptador Web → Motor Helios ───────────────────────────────────

def build_helios_payload(req: WebHeliosRequest, user_id: str) -> dict:
    """Convierte el request web al formato exacto que acepta el Motor Helios."""
    
    base_params = {
        "market_id": req.market_id,
        "product_id": req.product_id,
        "demanda_historica": req.historical_data,
        "activar_digital_twin": True,
        "pais_principal": "CL",
    }

    if req.model == "epsilon":
        base_params.update({
            "horizonte_meses": req.horizonte_meses,
            "margen_bruto_pct": (req.margen_bruto_pct or 30) / 100,
        })

    elif req.model == "sigma":
        demanda_invertida = list(reversed(req.historical_data))
        base_params.update({
            "demanda_historica": demanda_invertida,
            "periodos": req.periodos,
            "costo_unitario": req.costo_unitario or 1000.0,
            "costo_pedido": req.costo_pedido or 50.0,
            "costo_mantencion_pct": (req.costo_mantencion_pct or 25) / 100,
        })

    elif req.model == "poseidon":
        base_params.update({
            "demanda_historica": req.historical_data[:12],
            "inventario_inicial_tanque1": req.inventario_inicial_tanque1 or 0,
            "inventario_inicial_tanque2": req.inventario_inicial_tanque2 or 0,
            "capacidad_max_mensual": req.capacidad_max_mensual or 1000,
            "capacidad_tanque_1": req.capacidad_tanque_1 or 500,
            "capacidad_tanque_2": req.capacidad_tanque_2 or 500,
            "cobertura_objetivo": req.cobertura_objetivo,
            "cantidad_clientes": req.cantidad_clientes or 1,
            "kalman": {"usar_kalman": True, "Q": 0.1, "R": 0.5, "P0": 1.0},
            "pid": {"Kp": 0.5, "Ki": 0.1, "Kd": 0.05}
        })

    return {
        "modelName": req.model.upper(),
        "modelParams": base_params,
        "device_id": "web_app"
    }

# ── Adaptador respuesta Motor → Frontend Web ───────────────────────

def adapt_response_for_web(model: str, raw: dict) -> dict:
    """Convierte la respuesta del Motor Helios al JSON que espera el frontend web."""

    if model == "epsilon":
        p50 = raw.get("p50", [])
        p95 = raw.get("p95", [])
        forecast_base = raw.get("forecast_base", [])
        compra = raw.get("compra_sugerida", 0)
        if isinstance(compra, list):
            compra = compra[-1] if compra else 0

        periods = [f"M{i+1}" for i in range(len(p50))]
        return {
            "status": "success",
            "model": "epsilon",
            "risk_level": "MEDIUM" if raw.get("volatilityIndex", 0) < 0.3 else "HIGH",
            "trend_direction": "upward",
            "kpis": {
                "optimal_order_qty": round(compra),
                "reorder_point": round(p50[-1]) if p50 else 0,
                "safety_stock": round((p95[-1] - p50[-1]) if p50 and p95 else 0),
                "service_level_achieved": raw.get("confidenceIndex", 0.87),
            },
            "chart_data": {
                "forecast_line": [
                    {
                        "period": periods[i],
                        "forecast": p50[i],
                        "upper": p95[i] if i < len(p95) else p50[i],
                        "lower": forecast_base[i] if i < len(forecast_base) else p50[i],
                        "historical": None
                    }
                    for i in range(len(p50))
                ],
                "weekly_breakdown": [
                    {"week": periods[i], "demand": p50[i], "lower_band": forecast_base[i] if i < len(forecast_base) else p50[i]}
                    for i in range(len(p50))
                ]
            }
        }

    elif model == "sigma":
        eoq = raw.get("eoq_dt", [0])
        rop = raw.get("rop_dt", [0])
        demanda = raw.get("demanda_dt", [])
        forecast = raw.get("forecast_base", [])
        periods = [f"M{i+1}" for i in range(len(demanda))]

        return {
            "status": "success",
            "model": "sigma",
            "risk_level": "LOW",
            "trend_direction": "stable",
            "kpis": {
                "forecasted_demand": round(demanda[-1]) if demanda else 0,
                "safety_stock": round((eoq[-1] - rop[-1]) if eoq and rop else 0),
                "reorder_point": round(rop[-1]) if rop else 0,
                "confidence_score": 0.87,
                "inventory_turnover": round(raw.get("costo_unitario", 1) / 100, 1),
            },
            "chart_data": {
                "forecast_line": [
                    {
                        "period": periods[i],
                        "historical": demanda[i] if i < len(demanda) else None,
                        "forecast": forecast[i] if i < len(forecast) else None,
                        "upper": (forecast[i] * 1.1) if i < len(forecast) and forecast[i] else None,
                        "lower": (forecast[i] * 0.9) if i < len(forecast) and forecast[i] else None,
                    }
                    for i in range(max(len(demanda), len(forecast)))
                ],
                "weekly_breakdown": [
                    {"week": f"M{i+1}", "demand": eoq[i] if i < len(eoq) else 0, "lower_band": rop[i] if i < len(rop) else 0}
                    for i in range(len(eoq))
                ]
            }
        }

    elif model == "poseidon":
        p = raw.get("poseidon", {})
        prod = p.get("produccion_sugerida", [])
        demanda = p.get("demanda_proyectada", [])
        tanque1 = p.get("inventario_tanque1", [])
        periods = [f"D{i+1}" for i in range(len(prod))]

        cap_util = round((sum(prod) / (len(prod) * max(prod)) * 100) if prod and max(prod) > 0 else 0)

        return {
            "status": "success",
            "model": "poseidon",
            "risk_level": "LOW" if cap_util < 80 else "HIGH",
            "trend_direction": "upward",
            "kpis": {
                "recommended_production": round(sum(prod)),
                "capacity_utilization_pct": cap_util,
                "batches_required": len([x for x in prod if x > 0]),
                "efficiency_score": 0.82,
                "bottleneck_detected": cap_util > 90,
            },
            "chart_data": {
                "forecast_line": [
                    {
                        "period": periods[i],
                        "forecast": demanda[i] if i < len(demanda) else 0,
                        "upper": (demanda[i] * 1.1) if i < len(demanda) else 0,
                        "lower": (demanda[i] * 0.9) if i < len(demanda) else 0,
                        "historical": None
                    }
                    for i in range(len(demanda))
                ],
                "weekly_breakdown": [
                    {"week": periods[i], "demand": prod[i], "lower_band": tanque1[i] if i < len(tanque1) else 0}
                    for i in range(len(prod))
                ],
                "poseidon_specific": {
                    "production_schedule": [
                        {"day": periods[i], "units": prod[i], "capacity": max(prod) if prod else 0}
                        for i in range(len(prod))
                    ]
                }
            }
        }

# ── Endpoint principal ─────────────────────────────────────────────

@router.post("/helios/calculate")
async def web_calculate(
    request: WebHeliosRequest,
    background_tasks: BackgroundTasks,
    authorization: str = Header(...)
):
    # 1. Extraer user_id del token Supabase
    try:
        from backend.core.supabase_client import supabase as sb_client
        token = authorization.replace("Bearer ", "")
        user_response = sb_client.auth.get_user(token)
        user_id = user_response.user.id
    except Exception as e:
        logger.error(f"Fallo validación de token Supabase: {type(e).__name__}: {e}")
        raise HTTPException(status_code=401, detail=f"Token inválido: {type(e).__name__}: {str(e)}")

    # 2. Verificar y descontar crédito
    has_credits = await check_and_deduct_credit(user_id)
    if not has_credits:
        raise HTTPException(status_code=402, detail="INSUFFICIENT_CREDITS")

    # 3. Construir payload para el Motor Helios
    helios_payload = build_helios_payload(request, user_id)

    # 4. Llamar al Motor Helios existente (Corrección de firma)
    try:
        from backend.services.model_service import run_model_and_adapt
        
        model_name = helios_payload.get("modelName")
        model_params = helios_payload.get("modelParams")
        user_context = {"device_id": "web_app", "user_id": user_id}

        # La función es síncrona y requiere 4 parámetros posicionales
        raw_result = run_model_and_adapt(model_name, model_params, background_tasks, user_context)
        
    except Exception as e:
        # Si el motor falla, devolver el crédito
        from backend.services.credit_service import add_credits
        await add_credits(user_id, 1, "free")
        raise HTTPException(status_code=500, detail=f"Motor error: {str(e)}")

    # 5. Adaptar respuesta para el frontend web
    web_response = adapt_response_for_web(request.model, raw_result.modelOutput)

    # 6. Guardar análisis en Supabase
    try:
        from backend.core.supabase_client import supabase as sb_client
        sb_client.table("analyses").insert({
            "user_id": user_id,
            "model": request.model,
            "market": request.market_id,
            "product_name": request.product_id,
            "credits_used": 1,
            "result": web_response
        }).execute()
    except Exception:
        pass  # No bloquear si falla el guardado

    return web_response