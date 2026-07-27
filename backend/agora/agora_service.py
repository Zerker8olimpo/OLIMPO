import datetime
from typing import Optional, Dict, Any, List

from backend.agora.agora_config_adapter import AgoraConfigAdapter
from backend.agora.config_registry_stub import ConfigRegistryStub
from backend.agora.engines.observation_engine import ObservationEngine
from backend.agora.engines.projection_engine import ProjectionEngine
from backend.agora.engines.indicators_engine import IndicatorsEngine
from backend.agora.engines.market_forces_engine import MarketForcesEngine
from backend.agora.engines.margin_engine import MarginEngine
from backend.agora.engines.commercial_interpreter import CommercialInterpreter
from backend.agora.schemas.agora_models import AgoraPulseResponse, CfgContext, SnapshotContext

class AgoraService:
    def __init__(self):
        self.adapter = AgoraConfigAdapter()
        self.obs_engine = ObservationEngine()
        self.proj_engine = ProjectionEngine()
        self.ind_engine = IndicatorsEngine()
        self.forces_engine = MarketForcesEngine()
        self.margin_engine = MarginEngine()
        self.interpreter = CommercialInterpreter()

    async def get_pulse(
        self,
        market: str,
        product: str,
        subfamily: str,
        horizon: int,
        unit_cost: Optional[float] = None,
        user_price: Optional[float] = None
    ) -> AgoraPulseResponse:
        
        # Cargar datos
        snapshots = self.adapter.get_snapshots()
        snapshot_data = snapshots.get(subfamily)
        
        warnings = []
        if not snapshot_data:
            # En un caso real buscaríamos el mercado/producto por defecto
            # Para el MVP, si no hay snapshot del subfamily específico, devolvemos error o mock
            warnings.append(f"No se encontraron datos recientes para la subfamilia {subfamily}. Usando datos de referencia general.")
            # Intentar cargar un default o fallar controlado
            snapshot_data = snapshots.get("pvc_sanitario", {}) # Fallback para demo

        rules = self.adapter.get_projection_rules()
        comm_rules = self.adapter.get_commercial_rules()
        indicators_cfg = self.adapter.get_indicators_cfg().get(market, {})
        supply_demand_cfg = self.adapter.get_supply_demand_cfg().get(market, {}).get("subfamilies", {}).get(subfamily, {})
        substitutes_cfg = self.adapter.get_substitutes_cfg().get(subfamily, {})

        # 1. Observación
        obs_result = self.obs_engine.process(snapshot_data)

        # 2. Indicadores
        ind_result = await self.ind_engine.process(snapshot_data, indicators_cfg)

        # 3. Fuerzas de Mercado
        forces_result = self.forces_engine.process(snapshot_data, supply_demand_cfg, substitutes_cfg)

        # 4. Proyección (pondera tendencia histórica + presión económica de indicadores)
        proj_result = self.proj_engine.process(obs_result, rules, horizon, indicators_result=ind_result)

        # 5. Margen
        margin_result = self.margin_engine.process(
            obs_result["current_reference_price"],
            proj_result,
            unit_cost,
            user_price
        )
        
        # 6. Interpretación
        interp_result = self.interpreter.process(obs_result, margin_result, comm_rules)

        # Contextos
        cfg_ctx = CfgContext(
            canonical_cfg_version=ConfigRegistryStub.get_canonical_version(),
            canonical_cfg_hash=ConfigRegistryStub.get_canonical_hash(),
            agora_cfg_version="1.0.0",
            agora_cfg_hash="hash_agora_mock"
        )
        
        snap_ctx = SnapshotContext(
            price_snapshot_id=f"price_snap_{subfamily}_{datetime.datetime.now().strftime('%Y%m%d')}",
            indicator_snapshot_id=f"ind_snap_{market}_{datetime.datetime.now().strftime('%Y%m%d')}",
            history_window_start=(datetime.datetime.now() - datetime.timedelta(days=180)).strftime("%Y-%m-%d"),
            history_window_end=datetime.datetime.now().strftime("%Y-%m-%d"),
            computed_at=datetime.datetime.now()
        )

        return AgoraPulseResponse(
            market=market,
            product=product,
            subfamily=subfamily,
            projection_horizon_months=horizon,
            observation=obs_result,
            projection=proj_result,
            economic_indicators=ind_result,
            market_forces=forces_result,
            margin_reference=margin_result,
            commercial_interpretation=interp_result,
            cfg_context=cfg_ctx,
            snapshot_context=snap_ctx,
            warnings=warnings
        )

    def get_markets(self) -> List[Dict[str, Any]]:
        markets = self.adapter.get_markets()
        return list(markets.values())

    def get_products(self, market_id: str) -> List[Dict[str, Any]]:
        products = self.adapter.get_products()
        return [p for p in products.values() if p.get("market_id") == market_id]

    def get_subfamilies(self, product_id: str) -> List[Dict[str, Any]]:
        subfamilies = self.adapter.get_subfamilies()
        return [s for s in subfamilies.values() if s.get("product_id") == product_id]
