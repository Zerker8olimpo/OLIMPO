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
    AgoraV2MarginProjectionPoint
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
        unit_cost: Optional[float] = None,
        user_price: Optional[float] = None,
        legacy_context: Optional[Dict[str, str]] = None,
        db: Optional[Session] = None
    ) -> AgoraV2PulseResponse:
        
        warnings = []
        frontend_message = "ÁGORA está analizando el pulso del mercado para esta familia."
        
        # 1. Resolver IDs Canónicos (El router ya debería hacerlo, pero aseguramos aquí)
        c_market_id = self.catalog.resolve_market_id(market_id)
        c_product_id = self.catalog.resolve_product_id(c_market_id, product_id)
        c_family_id = self.catalog.resolve_family_id(c_market_id, c_product_id, family_id)
        
        # 2. Validar existencia en catálogo
        if not self.catalog.validate_market_product_family(c_market_id, c_product_id, c_family_id):
            warnings.append(f"La familia {family_id} no se encontró en el catálogo canónico.")
        
        # 3. Obtener Snapshot
        snapshot = self.get_snapshot_for_family(c_market_id, c_product_id, c_family_id)
        
        # 4. Determinar status y calidad de datos (Eliminando fallback silencioso)
        if snapshot:
            source_mode = snapshot.get("source_context", {}).get("source_mode", "sample")
            real_web_observation = snapshot.get("source_context", {}).get("real_web_observation", False)
            
            if source_mode == "sample":
                data_status = "sample_available"
                snapshot_status = "sample_snapshot"
                warnings.append("No existe snapshot real para esta familia. Se entrega referencia de muestra/controlada.")
                frontend_message = "ÁGORA aún no tiene suficientes observaciones reales para esta familia. Los valores mostrados son referenciales."
            else:
                data_status = "real_available"
                snapshot_status = "real_snapshot"
        else:
            # Fallback estructurado
            warnings.append("No existe snapshot (real ni muestra) para esta familia. Se entrega fallback genérico.")
            frontend_message = "ÁGORA aún no tiene mediciones específicas para esta familia. Los valores mostrados son referenciales y se actualizarán cuando existan mediciones."
            data_status = "fallback_available"
            snapshot_status = "missing_snapshot"
            source_mode = "fallback"
            real_web_observation = False
            
            snaps = self.get_sample_snapshots()
            if snaps:
                snapshot = snaps[0]
                snapshot_status = "fallback_snapshot"
            else:
                # Fallback de último recurso (schema-safe)
                snapshot = {
                    "current": {
                        "price_median": 0, 
                        "price_min": 0, 
                        "price_avg": 0, 
                        "price_max": 0, 
                        "sample_size": 0, 
                        "volatility": 0, 
                        "historical_trend_percent": 0.0,
                        "last_update": datetime.datetime.now().strftime("%Y-%m-%d")
                    }
                }
                data_status = "no_data"

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
        proj_result = self.proj_engine.process(obs_result, rules, horizon)
        ind_result = self.ind_engine.process(adapted_snapshot_data)
        forces_result = self.forces_engine.process(adapted_snapshot_data)
        margin_result = self.margin_engine.process(obs_result["current_reference_price"], proj_result, unit_cost, user_price)
        interp_result = self.interpreter.process(obs_result, margin_result, comm_rules)

        # 6. Construir Respuesta (Hotfix: Todos los campos requeridos por Pydantic V2)
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
        
        # TAREA 5: Pulse debe usar fuente histórica real si está disponible
        real_history_data = None
        if db:
            real_history_data = self.history_service.get_last_6_months_history(
                db, c_market_id, c_product_id, c_family_id
            )

        if real_history_data and real_history_data["history"]:
            # Usar histórico real de la DB
            h_list = real_history_data["history"]
            for idx, h in enumerate(h_list):
                # Calculamos month_index relativo al último (que es idx = len-1)
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
            
            # Sincronizar estados
            source_ctx.historical_window_available = True
            source_ctx.historical_backfill_months = len(h_list)
            if real_history_data["data_status"] == "real_available":
                data_status = "real_available"
                snapshot_status = "real_snapshot"
        
        elif data_status == "real_available":
            # TAREA 1: Reconstrucción matemática segura (Guardia contra negativos)
            trend = obs_result.get("historical_trend_percent", 0.0)
            if source_ctx.historical_window_available:
                for i in range(-5, 1):
                    factor = 1 + (trend * i / 6)
                    ref_p = max(0.1, obs_result["current_reference_price"] * factor)
                    min_p = max(0.1, obs_result["price_min"] * factor)
                    med_p = max(0.1, obs_result["price_median"] * factor)
                    avg_p = max(0.1, obs_result["price_avg"] * factor)
                    max_p = max(0.1, obs_result["price_max"] * factor)
                    
                    history_series.append(AgoraV2HistoryPoint(
                        month_index=i,
                        label=f"M{i}" if i < 0 else "Actual",
                        reference_price=ref_p,
                        price_min=min_p,
                        price_median=med_p,
                        price_avg=avg_p,
                        price_max=max_p,
                        confidence=snapshot.get("current", {}).get("confidence", 0.7),
                        data_status=data_status
                    ))
        else:
            # TAREA 2: Si no hay histórico real ni reconstrucción posible, vacío
            history_series = []
            source_ctx.historical_window_available = False
            source_ctx.historical_backfill_months = 0
            if data_status != "no_data":
                frontend_message = "ÁGORA aún no tiene histórico suficiente para esta familia."
            
        if source_mode in ["sample", "fallback"] and history_series:
             warnings.append("Serie histórica generada desde muestra controlada; no corresponde a observaciones reales mes a mes.")

        projection_series = []
        if data_status != "no_data":
            base_p = proj_result.get("base", obs_result["current_reference_price"])
            low_p = proj_result.get("low", obs_result["current_reference_price"])
            high_p = proj_result.get("high", obs_result["current_reference_price"])
            current_p = obs_result["current_reference_price"]
            
            for i in range(1, horizon + 1):
                interp_base = current_p + (base_p - current_p) * (i / horizon)
                interp_low = current_p + (low_p - current_p) * (i / horizon)
                interp_high = current_p + (high_p - current_p) * (i / horizon)
                projection_series.append(AgoraV2ProjectionPoint(
                    month_index=i,
                    label=f"M+{i}",
                    low=interp_low,
                    base=interp_base,
                    high=interp_high,
                    confidence=proj_result.get("confidence", 0.7),
                    trend_label=proj_result.get("trend_label", "estable")
                ))
            warnings.append("Proyección mensual derivada desde el escenario base; usar como referencia.")
            
        margin_projection_series = []
        if data_status != "no_data" and unit_cost is not None and projection_series:
            for p in projection_series:
                margin_projection_series.append(AgoraV2MarginProjectionPoint(
                    month_index=p.month_index,
                    label=p.label,
                    margin_low=(p.low - unit_cost) / p.low if p.low > 0 else 0,
                    margin_base=(p.base - unit_cost) / p.base if p.base > 0 else 0,
                    margin_high=(p.high - unit_cost) / p.high if p.high > 0 else 0
                ))

        return AgoraV2PulseResponse(
            module="AGORA",
            api_version="v2",
            market_id=c_market_id,
            safe_market_id=IdNormalizationService.build_safe_id(c_market_id),
            product_id=c_product_id,
            safe_product_id=IdNormalizationService.build_safe_id(c_product_id),
            family_id=c_family_id,
            safe_family_id=IdNormalizationService.build_safe_id(c_family_id),
            history_window_months=6,
            projection_horizon_months=horizon,
            observation=obs_result,
            projection=proj_result,
            history_series=history_series,
            projection_series=projection_series,
            economic_indicators=ind_result,
            market_forces=forces_result,
            margin_reference=margin_result,
            margin_projection_series=margin_projection_series,
            commercial_interpretation=interp_result,
            cfg_context={
                "canonical_cfg_version": ConfigRegistryStub.get_canonical_version(),
                "canonical_cfg_hash": ConfigRegistryStub.get_canonical_hash(),
                "agora_v2_cfg_ready": True
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
