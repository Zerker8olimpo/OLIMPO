import datetime
import json
import os
from typing import Optional, Dict, Any, List

from backend.agora.agora_config_adapter import AgoraConfigAdapter
from backend.agora.family_catalog_service import FamilyCatalogService
from backend.agora.compatibility_alias_adapter import CompatibilityAliasAdapter
from backend.agora.engines.observation_engine import ObservationEngine
from backend.agora.engines.projection_engine import ProjectionEngine
from backend.agora.engines.indicators_engine import IndicatorsEngine
from backend.agora.engines.market_forces_engine import MarketForcesEngine
from backend.agora.engines.margin_engine import MarginEngine
from backend.agora.engines.commercial_interpreter import CommercialInterpreter
from backend.agora.id_normalization_service import IdNormalizationService
from backend.agora.schemas.agora_v2_models import (
    AgoraV2PulseResponse, 
    AgoraV2SourceContext,
    AgoraV2HistoryPoint,
    AgoraV2ProjectionPoint,
    AgoraV2MarginProjectionPoint,
    AgoraV2HistoryCoverage
)
from backend.agora.config_registry_stub import ConfigRegistryStub
from backend.agora.agora_history_service import AgoraHistoryService
from sqlalchemy.orm import Session

class AgoraV2Service:
    def __init__(self):
        self.catalog = FamilyCatalogService()
        self.alias_adapter = CompatibilityAliasAdapter()
        self.cfg_adapter = AgoraConfigAdapter()
        
        self.obs_engine = ObservationEngine()
        self.proj_engine = ProjectionEngine()
        self.ind_engine = IndicatorsEngine()
        self.forces_engine = MarketForcesEngine()
        self.margin_engine = MarginEngine()
        self.interpreter = CommercialInterpreter()
        self.history_service = AgoraHistoryService()

    def get_sample_snapshots(self) -> List[Dict[str, Any]]:
        path = "backend/cfg/CFG_AGORA_FAMILY_SNAPSHOTS_SAMPLE.json"
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("snapshots", [])
        return []

    def get_snapshot_for_family(self, market_id: str, product_id: str, family_id: str) -> Optional[Dict[str, Any]]:
        snaps = self.get_sample_snapshots()
        for s in snaps:
            if s.get("market_id") == market_id and s.get("product_id") == product_id and s.get("family_id") == family_id:
                return s
        return None

    async def get_pulse(
        self,
        market_id: str,
        product_id: str,
        family_id: str,
        horizon: int,
        current_cost: Optional[float] = None,
        current_sale_price: Optional[float] = None,
        legacy_context: Optional[Dict[str, str]] = None,
        db: Optional[Session] = None,
        plan: str = "basic"
    ) -> AgoraV2PulseResponse:
        
        warnings = []
        frontend_message = "ÁGORA está analizando el pulso del mercado para esta familia."
        
        # TAREA 8: Behavior por Plan
        effective_horizon = horizon
        if plan == "basic" and horizon > 3:
            effective_horizon = 3
            warnings.append("Horizonte limitado a 3 meses para plan Basic.")
        
        # 1. Resolver IDs Canónicos
        c_market_id = self.catalog.resolve_market_id(market_id)
        c_product_id = self.catalog.resolve_product_id(c_market_id, product_id)
        c_family_id = self.catalog.resolve_family_id(c_market_id, c_product_id, family_id)
        
        # 2. Validar existencia en catálogo
        if not self.catalog.validate_market_product_family(c_market_id, c_product_id, c_family_id):
            warnings.append(f"La familia {family_id} no se encontró en el catálogo canónico.")
        
        # 3. Obtener Histórico Real desde DB
        real_history_data = None
        if db:
            real_history_data = self.history_service.get_last_6_months_history(
                db, c_market_id, c_product_id, c_family_id
            )
            
            if real_history_data and "warnings" in real_history_data:
                warnings.extend(real_history_data["warnings"])

        snapshot = None
        has_real_db_snapshot = real_history_data and real_history_data.get("data_status") == "real_available" and real_history_data["history"]
        
        # TAREA 5: Proyección basada en calidad de datos
        history_list = real_history_data["history"] if real_history_data else []
        calculated_trend = self._calculate_trend_from_history(history_list)
        
        if has_real_db_snapshot:
            latest_snap = real_history_data["history"][-1]
            snapshot = {
                "current": {
                    "price_median": latest_snap["price_median"],
                    "price_min": latest_snap["price_min"],
                    "price_avg": latest_snap["price_avg"],
                    "price_max": latest_snap["price_max"],
                    "sample_size": latest_snap["sample_size"],
                    "volatility": latest_snap["volatility"],
                    "historical_trend_percent": calculated_trend,
                    "last_update": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                },
                "source_context": {
                    "source_mode": "real",
                    "real_web_observation": True
                }
            }
        else:
            snapshot = self.get_snapshot_for_family(c_market_id, c_product_id, c_family_id)
            if snapshot and "current" in snapshot:
                # Si es de muestra, respetamos su tendencia si no hay historia real
                if calculated_trend == 0 and "historical_trend_percent" not in snapshot["current"]:
                     snapshot["current"]["historical_trend_percent"] = 0.0

        # 4. Determinar status y calidad de datos
        if snapshot and snapshot.get("source_context", {}).get("source_mode") == "real":
             data_status = "real_available"
             snapshot_status = "real_snapshot"
             source_mode = "real"
             real_web_observation = True
             frontend_message = "ÁGORA está analizando el pulso del mercado para esta familia con datos reales."
        elif snapshot:
            source_mode = snapshot.get("source_context", {}).get("source_mode", "sample")
            real_web_observation = snapshot.get("source_context", {}).get("real_web_observation", False)
            
            data_status = "sample_available"
            snapshot_status = "sample_snapshot"
            warnings.append("No existe snapshot real para esta familia. Se entrega referencia de muestra/controlada específica.")
            frontend_message = "ÁGORA aún no tiene suficientes observaciones reales para esta familia. Los valores mostrados son referenciales."
        else:
            warnings.append("No existe observación real de precios para esta familia.")
            frontend_message = "ÁGORA aún no tiene mediciones reales para esta familia. Puedes consultar las variaciones macroeconómicas referenciales."
            data_status = "no_data"
            snapshot_status = "missing_snapshot"
            source_mode = "none"
            real_web_observation = False
            
            snapshot = {
                "current": {},
                "indicators": {
                    "inflation": {"variation_6m": 0.03, "impact": "medio", "direction": "presiona_alza"}, 
                    "exchange_rate": {"variation_6m": 0.05, "impact": "medio", "direction": "presiona_alza"}
                },
                "market_forces": {"supply": "neutral", "demand": "neutral", "substitutes": "neutral"}
            }

        rules = self.cfg_adapter.get_projection_rules()
        comm_rules = self.cfg_adapter.get_commercial_rules()

        # 5. Ejecutar Motores
        adapted_snapshot_data = {
            "current": snapshot.get("current", {}),
            "indicators": snapshot.get("indicators", {
                "inflation": {"variation_6m": 0.03, "impact": "medio", "direction": "presiona_alza"}, 
                "exchange_rate": {"variation_6m": 0.05, "impact": "medio", "direction": "presiona_alza"}
            }),
            "market_forces": snapshot.get("market_forces", {"supply": "neutral", "demand": "neutral", "substitutes": "neutral"})
        }

        obs_result = self.obs_engine.process(adapted_snapshot_data)
        proj_result = self.proj_engine.process(obs_result, rules, effective_horizon)
        ind_result = self.ind_engine.process(adapted_snapshot_data)
        forces_result = self.forces_engine.process(adapted_snapshot_data)
        margin_result = self.margin_engine.process(obs_result["current_reference_price"], proj_result, current_cost, current_sale_price)
        
        # 6. Construir Respuesta
        snapshot_date = snapshot.get("date", datetime.datetime.now().strftime("%Y-%m-%d"))
        
        source_ctx = AgoraV2SourceContext(
            source_mode=source_mode,
            real_web_observation=real_web_observation,
            snapshot_date=snapshot_date,
            historical_window_available=True if snapshot.get("current", {}).get("sample_size", 0) > 0 else False,
            historical_backfill_months=6,
            message=frontend_message,
            is_sample_data=(source_mode in ["sample", "fallback"]),
            display_as_reference_only=(source_mode in ["sample", "fallback"])
        )

        history_series = []
        coverage = None

        if real_history_data and real_history_data["history"]:
            h_list = real_history_data["history"]
            for idx, h in enumerate(h_list):
                m_idx = idx - (len(h_list) - 1)
                history_series.append(AgoraV2HistoryPoint(
                    month_index=m_idx,
                    label=h["month"],
                    reference_price=h["price_median"],
                    price_min=h["price_min"],
                    price_median=h["price_median"],
                    price_avg=h["price_avg"],
                    price_max=h["price_max"],
                    confidence=0.85, 
                    data_status=h["data_status"]
                ))

            source_ctx.historical_window_available = True
            source_ctx.historical_backfill_months = len(h_list)
            if real_history_data["data_status"] == "real_available":
                data_status = "real_available"
                snapshot_status = "real_snapshot"
            
            if "coverage" in real_history_data:
                source_ctx.coverage = AgoraV2HistoryCoverage(**real_history_data["coverage"])
                
                if source_ctx.coverage.history_status == "partial":
                    warnings.append("Histórico insuficiente para una proyección robusta.")
                    frontend_message = f"ÁGORA tiene datos parciales ({source_ctx.coverage.available_months} meses). La proyección es referencial."
        else:
            history_series = []
            source_ctx.historical_window_available = False
            source_ctx.historical_backfill_months = 0
            source_ctx.coverage = AgoraV2HistoryCoverage(
                required_months=6,
                available_months=0,
                missing_months=6,
                history_status="none",
                projection_quality="unavailable"
            )

        # TAREA 3, 4, 5, 6: Market Position Engine
        market_ref = obs_result.get("current_reference_price")
        if market_ref is not None and market_ref <= 0:
            market_ref = None
            
        projected_market = proj_result.get("base") if proj_result else None
        if projected_market is not None and projected_market <= 0:
            projected_market = None
        
        # Inicializar con valores por defecto (unavailable)
        commercial_pos_data = {
            "current_cost": current_cost,
            "current_sale_price": current_sale_price,
            "current_margin_pct": None,
            "market_reference_price": market_ref,
            "projected_market_price": projected_market,
            "market_trend_pct": calculated_trend / 100.0 if calculated_trend is not None else 0.0,
            "market_position_now": "unavailable",
            "market_position_projected": "unavailable",
            "price_gap_pct": None,
            "projected_gap_pct": None,
            "margin_status": "unavailable",
            "commercial_risk": "unavailable",
            "recommendation": "Aún no hay referencia suficiente para comparar esta familia con el mercado.",
            "confidence_level": proj_result.get("confidence", 0.0) if proj_result else 0.0,
            "user_message": "Referencia de mercado no disponible."
        }

        if current_sale_price is not None and current_sale_price > 0:
            if current_cost is not None:
                commercial_pos_data["current_margin_pct"] = (current_sale_price - current_cost) / current_sale_price
                
                # margin_status
                m_status = "healthy"
                if commercial_pos_data["current_margin_pct"] < 0.15: m_status = "risky"
                elif commercial_pos_data["current_margin_pct"] < 0.25: m_status = "tight"
                commercial_pos_data["margin_status"] = m_status
            
            if market_ref and market_ref > 0:
                # price_gap_pct
                gap_now = (current_sale_price - market_ref) / market_ref
                commercial_pos_data["price_gap_pct"] = gap_now
                
                # market_position_now: +/- 5% gap
                pos_now = "in_market"
                if gap_now < -0.05: pos_now = "below_market"
                elif gap_now > 0.05: pos_now = "above_market"
                commercial_pos_data["market_position_now"] = pos_now

                # Proyección
                if projected_market and projected_market > 0:
                    gap_proj = (current_sale_price - projected_market) / projected_market
                    commercial_pos_data["projected_gap_pct"] = gap_proj
                    
                    pos_proj = "in_market"
                    if gap_proj < -0.05: pos_proj = "below_market"
                    elif gap_proj > 0.05: pos_proj = "above_market"
                    commercial_pos_data["market_position_projected"] = pos_proj
                
                # commercial_risk
                m_status = commercial_pos_data["margin_status"]
                pos_now = commercial_pos_data["market_position_now"]
                
                c_risk = "low"
                if m_status == "risky":
                    c_risk = "critical" if pos_now == "above_market" else "high"
                elif m_status == "tight":
                    c_risk = "high" if pos_now == "above_market" else "medium"
                elif pos_now == "above_market":
                    c_risk = "medium"
                
                commercial_pos_data["commercial_risk"] = c_risk
                
                # TAREA 7: Interpretación comercial
                interp = self._interpret_market_position(
                    commercial_pos_data["market_position_now"], 
                    commercial_pos_data["margin_status"], 
                    commercial_pos_data["market_position_projected"]
                )
                commercial_pos_data["recommendation"] = interp["recommendation"]
                commercial_pos_data["user_message"] = interp["user_message"]
            else:
                commercial_pos_data["recommendation"] = "Aún no hay referencia suficiente para comparar esta familia con el mercado."
                commercial_pos_data["user_message"] = "Referencia de mercado no disponible."

        # TAREA 8: Clipping por Plan Basic
        if plan == "basic":
            commercial_pos_data["projected_market_price"] = None
            commercial_pos_data["market_position_projected"] = "unavailable"
            commercial_pos_data["projected_gap_pct"] = None
            commercial_pos_data["market_trend_pct"] = 0.0
            commercial_pos_data["price_gap_pct"] = None
            commercial_pos_data["commercial_risk"] = "unavailable"

        from backend.agora.schemas.agora_v2_models import AgoraV2CommercialPosition
        comm_pos_model = AgoraV2CommercialPosition(**commercial_pos_data)

        interp_result = self.interpreter.process(obs_result, margin_result, comm_rules)

        projection_series = []
        current_p = obs_result.get("current_reference_price")
        
        if data_status != "no_data" and current_p is not None:
            base_p = proj_result.get("base") or current_p
            low_p = proj_result.get("low") or current_p
            high_p = proj_result.get("high") or current_p
            
            for i in range(1, effective_horizon + 1):
                interp_base = current_p + (base_p - current_p) * (i / effective_horizon)
                interp_low = current_p + (low_p - current_p) * (i / effective_horizon)
                interp_high = current_p + (high_p - current_p) * (i / effective_horizon)
                projection_series.append(AgoraV2ProjectionPoint(
                    month_index=i,
                    label=f"M+{i}",
                    low=interp_low,
                    base=interp_base,
                    high=interp_high,
                    confidence=proj_result.get("confidence", 0.7),
                    trend_label=proj_result.get("trend_label", "estable")
                ))
            
        margin_projection_series = []
        if data_status != "no_data" and current_cost is not None and projection_series:
            for p in projection_series:
                margin_projection_series.append(AgoraV2MarginProjectionPoint(
                    month_index=p.month_index,
                    label=p.label,
                    margin_low=(p.low - current_cost) / p.low if p.low > 0 else 0,
                    margin_base=(p.base - current_cost) / p.base if p.base > 0 else 0,
                    margin_high=(p.high - current_cost) / p.high if p.high > 0 else 0
                ))

        feature_depth = plan if plan in ["basic", "pro", "enterprise"] else "basic"
        allowed_horizons = [3] if feature_depth == "basic" else [3, 6, 12]
        horizon_adjusted = (feature_depth == "basic" and horizon in [6, 12])
        
        last_snapshot_month = None
        if history_series:
            last_snapshot_month = history_series[-1].label
            
        source_mix = None
        if has_real_db_snapshot:
             last_snap_ctx = real_history_data["history"][-1].get("source_context")
             if last_snap_ctx:
                 source_mix = last_snap_ctx.get("source_mix")

        return AgoraV2PulseResponse(
            agora_enabled=True,
            plan_tier=plan,
            feature_depth=feature_depth,
            data_mode="real" if data_status == "real_available" else ("sample" if data_status == "sample_available" else "none"),
            history_status=source_ctx.coverage.history_status if source_ctx.coverage else "none",
            available_months=source_ctx.coverage.available_months if source_ctx.coverage else 0,
            required_months=6,
            projection_quality=source_ctx.coverage.projection_quality if source_ctx.coverage else "unavailable",
            allowed_horizons=allowed_horizons,
            requested_horizon=horizon,
            effective_horizon=effective_horizon,
            horizon_adjusted=horizon_adjusted,
            user_message=frontend_message,
            admin_message=None,
            source_mix=source_mix,
            last_snapshot_month=last_snapshot_month,
            
            module="AGORA",
            api_version="v2",
            market_id=c_market_id,
            safe_market_id=IdNormalizationService.build_safe_id(c_market_id),
            product_id=c_product_id,
            safe_product_id=IdNormalizationService.build_safe_id(c_product_id),
            family_id=c_family_id,
            safe_family_id=IdNormalizationService.build_safe_id(c_family_id),
            history_window_months=6,
            projection_horizon_months=effective_horizon,
            observation=obs_result,
            projection=proj_result,
            history_series=history_series,
            projection_series=projection_series,
            economic_indicators=ind_result,
            market_forces=forces_result,
            margin_reference=margin_result,
            commercial_position=comm_pos_model,
            margin_projection_series=margin_projection_series,
            commercial_interpretation=interp_result,
            cfg_context={
                "canonical_cfg_version": ConfigRegistryStub.get_canonical_version(),
                "canonical_cfg_hash": ConfigRegistryStub.get_canonical_hash(),
                "agora_v2_cfg_ready": True,
                "plan": plan
            },
            snapshot_context={
                "family_id": c_family_id,
                "snapshot_date": snapshot_date,
                "computed_at": datetime.datetime.now().isoformat()
            },
            warnings=warnings,
            frontend_message=frontend_message,
            data_status=data_status,
            snapshot_status=snapshot_status,
            source_context=source_ctx,
            legacy_context=legacy_context
        )

    def _calculate_trend_from_history(self, history: List[Dict[str, Any]]) -> float:
        """TAREA 5: Proyección de precio mercado basado en calidad de datos."""
        n = len(history)
        if n < 2:
            return 0.0
            
        # Si hay 6+ meses: usar variación mediana mensual
        if n >= 6:
            variations = []
            for i in range(1, n):
                v1 = history[i-1]["price_median"]
                v2 = history[i]["price_median"]
                if v1 > 0:
                    variations.append((v2 - v1) / v1)
            
            if variations:
                import statistics
                return statistics.median(variations) * 100.0
                
        # Si hay 3 a 5 meses: tendencia simple
        elif n >= 3:
            v_start = history[0]["price_median"]
            v_end = history[-1]["price_median"]
            if v_start > 0:
                return ((v_end - v_start) / v_start) / (n - 1) * 100.0
                
        return 0.0

    def _interpret_market_position(self, pos_now: str, m_status: str, pos_proj: str) -> Dict[str, str]:
        """TAREA 7: Lógica de interpretación comercial."""
        res = {
            "recommendation": "Monitorear posición.",
            "user_message": "Tu posición comercial está siendo analizada."
        }
        
        if pos_now == "below_market":
            if m_status == "healthy":
                res["recommendation"] = "Ajustar precio al alza."
                res["user_message"] = "Tu precio está bajo el mercado y mantienes margen sano. Podrías tener espacio para ajustar precio sin perder competitividad."
            elif m_status == "risky":
                res["recommendation"] = "Revisar costos o ajustar precio."
                res["user_message"] = "Tu precio está bajo el mercado, pero el margen es estrecho. Existe riesgo de rentabilidad."
            else: # tight
                res["recommendation"] = "Revisar costos o ajustar precio."
                res["user_message"] = "Tu precio está bajo el mercado, pero el margen es estrecho. Existe riesgo de rentabilidad."
        elif pos_now == "in_market":
            if m_status == "healthy":
                res["recommendation"] = "Mantener estrategia."
                res["user_message"] = "Tu precio está dentro del rango de mercado y el margen se mantiene sano."
            else: # tight or risky
                res["recommendation"] = "Proteger margen."
                res["user_message"] = "Estás en mercado pero con margen ajustado. Revisa eficiencia operativa."
        elif pos_now == "above_market":
            if m_status == "healthy":
                res["recommendation"] = "Monitorear rotación."
                res["user_message"] = "Tu precio está sobre el mercado. Si tu propuesta de valor lo justifica, puedes sostenerlo; si no, monitorea rotación."
            elif m_status == "risky":
                res["recommendation"] = "Revisar estrategia comercial."
                res["user_message"] = "Tu precio está sobre el mercado y el margen no es cómodo. Revisa costo, proveedor o estrategia comercial."
            else: # tight
                res["recommendation"] = "Revisar estrategia comercial."
                res["user_message"] = "Tu precio está sobre el mercado y el margen no es cómodo. Revisa costo, proveedor o estrategia comercial."
        
        # Alertas de tendencia (TAREA 7)
        if pos_proj != pos_now:
            if pos_proj == "above_market":
                res["user_message"] += " La proyección indica que tu posición podría deteriorarse si no ajustas precio o costo."
            elif pos_proj == "in_market" and pos_now == "below_market":
                res["user_message"] += " La proyección indica que tu precio podría alinearse mejor con el mercado en el horizonte consultado."
                
        return res

