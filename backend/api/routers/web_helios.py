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

def adapt_response_for_web(request: WebHeliosRequest, model_output: dict) -> dict:
    """Convierte la respuesta del Motor Helios al JSON que espera el frontend web."""

    model = request.model

    if model == "epsilon":
        # Safe access to model output
        expected = model_output.get("expected", []) or model_output.get("p50", [])
        upper = model_output.get("upper", []) or model_output.get("p95", [])
        stress = model_output.get("stress", [])
        confidence_index = model_output.get("confidenceIndex", 0.0)
        volatility_index = model_output.get("volatilityIndex", 0.0)
        recommended_purchase = model_output.get("recommendedPurchase", 0.0)

        # KPI calculations
        if confidence_index >= 0.72:
            confidence_label = "Alta"
        elif confidence_index >= 0.45:
            confidence_label = "Media"
        else:
            confidence_label = "Baja"

        kpis = {
            "recommended_purchase": round(recommended_purchase),
            "central_projection": round(expected[-1]) if expected else 0,
            "upper_band": round(upper[-1]) if upper else 0,
            "confidence_label": confidence_label,
        }

        # Chart data calculations
        forecast = expected
        upper_band = upper
        lower_band = [(f - (u - f)) for f, u in zip(forecast, upper_band)]

        if stress:
            shock_upper = stress
            shock_lower = [(f - (s - f)) for f, s in zip(forecast, shock_upper)]
        else:
            shock_upper = [(f + volatility_index * f * 1.25) for f in forecast]
            shock_lower = [(f - volatility_index * f * 1.25) for f in forecast]
        
        periods = [f"M{i+1}" for i in range(len(forecast))]

        chart_data = {
            "periods": periods,
            "historical": request.historical_data,
            "forecast": forecast,
            "upper_band": upper_band,
            "lower_band": [max(0, val) for val in lower_band],
            "shock_upper": shock_upper,
            "shock_lower": [max(0, val) for val in shock_lower],
            "purchase_line": recommended_purchase,
        }

        return {
            "status": "success",
            "model": "epsilon",
            "kpis": kpis,
            "chart_data": chart_data,
        }

    elif model == "sigma":
        demanda_dt = model_output.get("demanda_dt", []) or model_output.get("demandDt", [])
        rop_dt = model_output.get("rop_dt", []) or model_output.get("ropDt", [])
        eoq_dt = model_output.get("eoq_dt", []) or model_output.get("eoqDt", [])
        
        kpis = {
            "expected_demand": round(demanda_dt[-1]) if demanda_dt else 0,
            "reorder_point": round(rop_dt[-1]) if rop_dt else 0,
            "recommended_lot": round(eoq_dt[-1]) if eoq_dt else 0,
            "order_cost": model_output.get("costo_pedido", 0.0),
        }

        periods = [f"M{i+1}" for i in range(len(demanda_dt))]

        chart_data = {
            "periods": periods,
            "historical": request.historical_data,
            "forecasted_demand": demanda_dt,
            "reorder_point_line": rop_dt,
            "economic_order_quantity_line": eoq_dt,
        }

        return {
            "status": "success",
            "model": "sigma",
            "kpis": kpis,
            "chart_data": chart_data,
        }

    elif model == "poseidon":
        p = model_output.get("poseidon", {})
        demanda_proyectada = p.get("demanda_proyectada", [])
        inventario_tanque1 = p.get("inventario_tanque1", [])
        
        sum_demand = sum(demanda_proyectada)
        sum_inventory = sum(inventario_tanque1)
        
        kpis = {
            "initial_stock_t1": request.inventario_inicial_tanque1 or 0,
            "estimated_coverage": round(sum_inventory / sum_demand, 2) if sum_demand > 0 else 0,
            "accumulated_demand": round(sum_demand),
            "stability_score": round(1 - (p.get('pid_params', {}).get('Kd', 0.05) / 0.1), 2) if 'pid_params' in p else 0.5,
        }

        periods = [f"D{i+1}" for i in range(len(demanda_proyectada))]

        chart_data = {
            "periods": periods,
            "tank1_inventory": inventario_tanque1,
            "tank2_inventory": p.get("inventario_tanque2", []),
            "suggested_production": p.get("produccion_sugerida", []),
            "projected_demand": demanda_proyectada,
        }

        return {
            "status": "success",
            "model": "poseidon",
            "kpis": kpis,
            "chart_data": chart_data,
        }

    # Fallback for unknown model
    return {"status": "error", "message": f"Adaptador para modelo '{model}' no implementado."}

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

    try:
        # 3. Construir payload para el Motor Helios
        helios_payload = build_helios_payload(request, user_id)

        # 4. Llamar al Motor Helios existente
        from backend.services.model_service import run_model_and_adapt
        
        model_name = helios_payload.get("modelName")
        model_params = helios_payload.get("modelParams")
        user_context = {"device_id": "web_app", "user_id": user_id}

        raw_result = run_model_and_adapt(model_name, model_params, background_tasks, user_context)
        
        # 5. Adaptar respuesta para el frontend web
        web_response = adapt_response_for_web(request, raw_result.modelOutput)

        # 6. Guardar análisis en Supabase
        from backend.core.supabase_client import supabase as sb_client
        sb_client.table("analyses").insert({
            "user_id": user_id,
            "model": request.model,
            "market": request.market_id,
            "product_name": request.product_id,
            "credits_used": 1,
            "result": web_response
        }).execute()

    except Exception as e:
        # Si cualquier paso del pipeline falla, se reembolsa el crédito.
        from backend.services.credit_service import add_credits
        await add_credits(user_id, 1, "free")
        
        # Loguear el error real para diagnóstico
        logger.error(
            f"Error en pipeline de cálculo, crédito reembolsado. User: {user_id}. Error: {type(e).__name__}: {e}",
            exc_info=True
        )
        
        # Devolver un error 500 genérico al cliente
        raise HTTPException(status_code=500, detail=f"Error interno del servidor durante el cálculo: {type(e).__name__}")

    return web_response