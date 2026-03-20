"""
OSEngine_CORE.py  (v1.0)
------------------------
Kernel + Orchestrator de OS_Engine.

Principios:
- El CORE es el único componente que "ve todo".
- Analysis calcula señales, no decide.
- Updaters proponen cambios (no escriben CFG).
- Dispatchers son adaptadores (no interpretan ni modifican).
- Export único: Contract estable para el resto del backend (y/o app vía API).

Entrada típica:
- context (market_id, product_id, etc.)
- product_series (demanda/precio/ventas, etc.)
- market_series (índice o proxy de mercado, opcional)
- cfg_bundle (config de análisis + límites + dispatchers)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# --- Scanners ---
from .scanners.api_fetcher import APIFetcher
from .scanners.market_scanner import MarketScanner
from .scanners.news_scanner import NewsScanner
from .scanners.web_scraper import WebScraper

# --- Analysis ---
from .analysis.shock_detector import detect_shock
from .analysis.volatility_estimator import estimate_volatility
from .analysis.trend_analyzer import analyze_trend
from .analysis.sensitivity_phi import compute_phi
from .analysis.impact_psi import compute_psi

# --- Updaters (proposals only) ---
from .config_updater.cfg_pid_updater import PIDUpdater
from .config_updater.cfg_risk_updater import RiskUpdater
from .config_updater.cfg_stock_updater import StockUpdater

# --- Dispatchers ---
from .dispatchers.alert_dispatcher import AlertDispatcher
from .dispatchers.dt_dispatcher import DTDispatcher
from .dispatchers.ml_dispatcher import MLDispatcher


# ============================================================
# Data Contracts (internos pero estables)
# ============================================================

@dataclass(frozen=True)
class EngineContext:
    product_id: str
    market_id: str
    country: str = "Chile"
    timestamp: str = ""

    def with_timestamp(self) -> "EngineContext":
        ts = self.timestamp or datetime.utcnow().isoformat()
        return EngineContext(
            product_id=self.product_id,
            market_id=self.market_id,
            country=self.country,
            timestamp=ts,
        )


@dataclass
class OSDecision:
    os_state: str                 # STABLE/WARNING/STRESSED/CRITICAL
    decision_mode: str            # NORMAL/CONSERVATIVE/DEFENSIVE/SURVIVAL
    rationale: Dict[str, Any]     # explicabilidad mínima


@dataclass
class RuntimeContext:
    multipliers: Dict[str, float]     # multiplicadores sobre CFG base (no se escribe CFG)
    guardrails: Dict[str, Any]        # límites/condiciones operativas
    flags: Dict[str, Any]             # banderas de operación (p.ej. "freeze_tuning")


# ============================================================
# CORE
# ============================================================

class OSEngineCore:
    """
    OSEngineCore v1.0

    Uso:
        core = OSEngineCore(cfg_bundle, ml_core=..., enable_scanners=True)
        contract = core.tick(context, product_series, market_series)
    """

    def __init__(
        self,
        cfg_bundle: Dict[str, Any],
        ml_core: Optional[Any] = None,
        enable_scanners: bool = True,
    ) -> None:
        self.cfg = cfg_bundle or {}
        self.enable_scanners = enable_scanners

        # --- scanners (stubs robustos) ---
        self.api_fetcher = APIFetcher()
        self.market_scanner = MarketScanner()
        self.news_scanner = NewsScanner()
        self.web_scraper = WebScraper()

        # --- updaters ---
        self.pid_updater = PIDUpdater()
        self.risk_updater = RiskUpdater()
        self.stock_updater = StockUpdater()

        # --- dispatchers ---
        self.alert_dispatcher = AlertDispatcher()
        self.dt_dispatcher = DTDispatcher()
        self.ml_dispatcher = MLDispatcher(ml_core) if ml_core is not None else None

        # --- estado interno (CUSUM) por producto ---
        self._shock_state_by_product: Dict[str, Dict[str, float]] = {}

    # ----------------------------
    # Public API
    # ----------------------------

    def tick(
        self,
        context: Dict[str, Any],
        product_series: List[float],
        market_series: Optional[List[float]] = None,
        helios_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta un ciclo lógico del OS Engine.
        Devuelve un Contract estable (JSON dict).
        """

        ctx = self._build_context(context)

        # 1) Observación externa (opcional)
        external_signals = self._scan_external_signals(ctx)

        # 2) Análisis determinístico (sensores)
        analysis_results, shock_state_out = self._run_analysis(
            ctx=ctx,
            product_series=product_series,
            market_series=market_series,
        )

        # Persistir estado cusum
        self._shock_state_by_product[ctx.product_id] = shock_state_out

        # 3) Decisión OS (estado + modo) y runtime context
        os_decision = self._evaluate_os_decision(ctx, analysis_results, external_signals)
        runtime_context = self._build_runtime_context(ctx, analysis_results, os_decision, external_signals)

        # 4) Propuestas (NO cambios)
        proposals = self._build_proposals(ctx, analysis_results)

        # 5) Dispatchers
        dispatch_status = self._dispatch_all(
            ctx=ctx,
            analysis_results=analysis_results,
            helios_results=helios_results or {},
            proposals=proposals,
            runtime_context=runtime_context,
            os_decision=os_decision,
        )

        # 6) Export contract estable
        contract = self._export_contract(
            ctx=ctx,
            analysis_results=analysis_results,
            runtime_context=runtime_context,
            os_decision=os_decision,
            proposals=proposals,
            external_signals=external_signals,
            dispatch_status=dispatch_status,
        )

        return contract

    # ============================================================
    # Internals
    # ============================================================

    def _build_context(self, context: Dict[str, Any]) -> EngineContext:
        product_id = str(context.get("product_id", "SKU_UNKNOWN"))
        market_id = str(context.get("market_id", "MARKET_UNKNOWN"))
        country = str(context.get("country", "Chile"))
        ts = str(context.get("timestamp", ""))

        return EngineContext(product_id=product_id, market_id=market_id, country=country, timestamp=ts).with_timestamp()

    def _scan_external_signals(self, ctx: EngineContext) -> Dict[str, Any]:
        if not self.enable_scanners:
            return {"enabled": False, "sources": {}, "quality": {"status": "disabled"}}

        api = self.api_fetcher.fetch()
        market = self.market_scanner.scan()
        news = self.news_scanner.scan()
        web = self.web_scraper.run()

        # Consolidación simple (sin interpretación)
        sources = {"api": api, "market": market, "news": news, "web": web}

        # Métrica agregada de calidad (conservadora)
        confidences = []
        for src in sources.values():
            q = (src or {}).get("quality", {})
            c = q.get("confidence", 0.0)
            if isinstance(c, (int, float)):
                confidences.append(float(c))

        quality = {
            "status": "ok" if confidences and min(confidences) >= 0.7 else "partial",
            "confidence_mean": round(sum(confidences) / len(confidences), 3) if confidences else 0.0,
            "confidence_min": round(min(confidences), 3) if confidences else 0.0,
        }

        return {
            "enabled": True,
            "timestamp": ctx.timestamp,
            "sources": sources,
            "quality": quality,
        }

    def _run_analysis(
        self,
        ctx: EngineContext,
        product_series: List[float],
        market_series: Optional[List[float]],
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:

        cfg_analysis = self.cfg.get("analysis", {})
        cfg_shock = cfg_analysis.get("shock", self._default_cfg_shock())
        cfg_vol = cfg_analysis.get("volatility", self._default_cfg_volatility())
        cfg_trend = cfg_analysis.get("trend", self._default_cfg_trend())
        cfg_phi = cfg_analysis.get("phi", self._default_cfg_phi())
        cfg_psi = cfg_analysis.get("psi", self._default_cfg_psi())

        prev_state = self._shock_state_by_product.get(ctx.product_id)

        shock = detect_shock(
            product_series=product_series,
            cfg=cfg_shock,
            market_series=market_series,
            context={"product_id": ctx.product_id, "market_id": ctx.market_id},
            state=prev_state,
        )

        # shock devuelve state actualizado (CUSUM pos/neg)
        shock_state_out = shock.get("state", {"pos": 0.0, "neg": 0.0})

        volatility = estimate_volatility(
            product_series=product_series,
            cfg=cfg_vol,
            shock_result=shock,
            market_series=market_series,
            context={"product_id": ctx.product_id, "market_id": ctx.market_id},
        )

        trend = analyze_trend(
            product_series=product_series,
            cfg=cfg_trend,
            shock_result=shock,
            volatility_result=volatility,
            context={"product_id": ctx.product_id, "market_id": ctx.market_id},
        )

        phi = None
        if market_series:
            phi = compute_phi(
                product_series=product_series,
                market_series=market_series,
                cfg=cfg_phi,
                trend_result=trend,
                volatility_result=volatility,
                context={"product_id": ctx.product_id, "market_id": ctx.market_id},
            )

        psi = compute_psi(
            shock_result=shock,
            volatility_result=volatility,
            phi_result=phi,
            trend_result=trend,
            cfg=cfg_psi,
            context={"product_id": ctx.product_id, "market_id": ctx.market_id},
        )

        analysis_results = {
            "shock": shock,
            "volatility": volatility,
            "trend": trend,
            "phi": phi or {"phi": {"value": 0.0, "confidence": 0.0}, "context": {"market_id": ctx.market_id}},
            "psi": psi,
        }

        return analysis_results, shock_state_out

    def _evaluate_os_decision(
        self,
        ctx: EngineContext,
        analysis_results: Dict[str, Any],
        external_signals: Dict[str, Any],
    ) -> OSDecision:

        psi_block = analysis_results.get("psi", {}).get("psi", {})
        psi_eff = float(psi_block.get("effective", 0.0))
        psi_conf = float(psi_block.get("confidence", 0.0))

        shock_flag = int(analysis_results.get("shock", {}).get("shock_flag", 0))
        vol_band = str(analysis_results.get("volatility", {}).get("risk_band", "low"))

        # Umbrales OS (kernel-level, no de modelos)
        cfg_os = self.cfg.get("os", {})
        thr_warning = float(cfg_os.get("psi_warning", 0.35))
        thr_stressed = float(cfg_os.get("psi_stressed", 0.55))
        thr_critical = float(cfg_os.get("psi_critical", 0.75))
        min_conf = float(cfg_os.get("min_confidence", 0.60))

        # Determinar OS State
        if psi_conf < min_conf and shock_flag:
            os_state = "WARNING"
        elif psi_eff >= thr_critical:
            os_state = "CRITICAL"
        elif psi_eff >= thr_stressed:
            os_state = "STRESSED"
        elif psi_eff >= thr_warning:
            os_state = "WARNING"
        else:
            os_state = "STABLE"

        # Determinar Decision Mode (operación)
        if os_state == "CRITICAL":
            decision_mode = "SURVIVAL"
        elif os_state == "STRESSED":
            decision_mode = "DEFENSIVE"
        elif os_state == "WARNING":
            decision_mode = "CONSERVATIVE"
        else:
            decision_mode = "NORMAL"

        # Ajuste por volatilidad alta
        if vol_band == "high" and decision_mode == "NORMAL":
            decision_mode = "CONSERVATIVE"

        rationale = {
            "psi_effective": round(psi_eff, 4),
            "psi_confidence": round(psi_conf, 3),
            "shock_flag": shock_flag,
            "volatility_band": vol_band,
            "external_quality": external_signals.get("quality", {}),
        }

        return OSDecision(os_state=os_state, decision_mode=decision_mode, rationale=rationale)

    def _build_runtime_context(
        self,
        ctx: EngineContext,
        analysis_results: Dict[str, Any],
        os_decision: OSDecision,
        external_signals: Dict[str, Any],
    ) -> RuntimeContext:

        psi_eff = float(analysis_results.get("psi", {}).get("psi", {}).get("effective", 0.0))
        shock_intensity = float(analysis_results.get("shock", {}).get("product", {}).get("intensity", 0.0))
        vol_total = float(analysis_results.get("volatility", {}).get("sigma", {}).get("total", 0.0))

        # Multipliers (ejemplo kernel-level): afectan cómo los modelos usan CFG base
        mult = {
            "w_shock": 1.0,
            "w_volatility": 1.0,
            "w_comex": 1.0,
            "elasticity": 1.0,
        }

        flags = {
            "freeze_tuning": False,
            "active_shock": bool(int(analysis_results.get("shock", {}).get("shock_flag", 0))),
        }

        # Regla defensiva: shock activo => freeze de tuning (no tocar PID/stock tuning en caliente)
        if flags["active_shock"] and shock_intensity >= 0.25:
            flags["freeze_tuning"] = True

        # Escalamiento simple por modo
        mode = os_decision.decision_mode
        if mode == "CONSERVATIVE":
            mult["w_shock"] = 1.10
            mult["w_volatility"] = 1.10
            mult["w_comex"] = 1.05
        elif mode == "DEFENSIVE":
            mult["w_shock"] = 1.25
            mult["w_volatility"] = 1.20
            mult["w_comex"] = 1.10
        elif mode == "SURVIVAL":
            mult["w_shock"] = 1.40
            mult["w_volatility"] = 1.30
            mult["w_comex"] = 1.15

        # Guardrails (hard constraints kernel-level)
        cfg_guard = self.cfg.get("guardrails", {})
        guardrails = {
            "min_confidence_to_act": float(cfg_guard.get("min_confidence_to_act", 0.60)),
            "max_purchase_multiplier": float(cfg_guard.get("max_purchase_multiplier", 2.5)),
            "min_purchase_multiplier": float(cfg_guard.get("min_purchase_multiplier", 0.7)),
            "psi_effective": round(psi_eff, 4),
            "volatility_total": round(vol_total, 4),
        }

        # Calidad externa: si la observación es pobre, reducimos agresividad
        q_min = float(external_signals.get("quality", {}).get("confidence_min", 0.0) or 0.0)
        if q_min < 0.4:
            mult["w_comex"] *= 0.95
            mult["w_shock"] *= 0.95

        return RuntimeContext(multipliers=mult, guardrails=guardrails, flags=flags)

    def _build_proposals(self, ctx: EngineContext, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        cfg_limits = self.cfg.get("cfg_limits", {})  # guardrails para propuestas (pid/risk/stock)

        # Si freeze_tuning activo, evitamos proponer (o proponemos freeze explícito vía PIDUpdater)
        proposals: List[Dict[str, Any]] = []

        proposals.extend(
            self.risk_updater.propose(
                analysis_results=analysis_results,
                cfg_limits=cfg_limits,
                scope="market",
                entity_id=ctx.market_id,
            )
        )

        proposals.extend(
            self.stock_updater.propose(
                analysis_results=analysis_results,
                cfg_limits=cfg_limits,
                scope="product",
                entity_id=ctx.product_id,
            )
        )

        proposals.extend(
            self.pid_updater.propose(
                analysis_results=analysis_results,
                cfg_limits=cfg_limits,
                cfg_olimpo_ml=None,
                scope="global",
                entity_id="ALL",
            )
        )

        return proposals

    def _dispatch_all(
        self,
        ctx: EngineContext,
        analysis_results: Dict[str, Any],
        helios_results: Dict[str, Any],
        proposals: List[Dict[str, Any]],
        runtime_context: RuntimeContext,
        os_decision: OSDecision,
    ) -> Dict[str, Any]:

        cfg_dispatch = self.cfg.get("dispatchers", {})
        status: Dict[str, Any] = {}

        # Alert dispatcher
        alert_cfg = cfg_dispatch.get("alerts", {"levels": {}, "confidence_min": 1.0, "notify_on_shock": False})
        system_state_for_alerts = {
            "context": asdict(ctx),
            "psi": analysis_results.get("psi", {}).get("psi", {}),
            "shock": analysis_results.get("shock", {}),
            "decision": asdict(os_decision),
        }
        status["alerts"] = self.alert_dispatcher.dispatch(system_state_for_alerts, alert_cfg)

        # DT dispatcher
        dt_cfg = cfg_dispatch.get("digital_twin", {"required_blocks": ["context", "psi", "shock", "decision"]})
        system_state_for_dt = {
            "context": asdict(ctx),
            "analysis_results": analysis_results,
            "runtime_context": asdict(runtime_context),
            "decision": asdict(os_decision),
        }
        status["digital_twin"] = self.dt_dispatcher.dispatch(system_state_for_dt, dt_cfg)

        # ML dispatcher (opcional)
        if self.ml_dispatcher is not None:
            payload = {
                "context": asdict(ctx),
                "analysis_results": analysis_results,
                "helios_results": helios_results,
                "proposals": proposals,
                "timestamp": ctx.timestamp,
            }
            status["ml"] = self.ml_dispatcher.dispatch(payload)
        else:
            status["ml"] = {"status": "disabled", "reason": "ml_core_not_provided", "timestamp": ctx.timestamp}

        return status

    def _export_contract(
        self,
        ctx: EngineContext,
        analysis_results: Dict[str, Any],
        runtime_context: RuntimeContext,
        os_decision: OSDecision,
        proposals: List[Dict[str, Any]],
        external_signals: Dict[str, Any],
        dispatch_status: Dict[str, Any],
    ) -> Dict[str, Any]:

        confidence = self._build_confidence(analysis_results, external_signals)
        signals_summary = self._build_signals_summary(analysis_results, external_signals)
        ttl = self._build_ttl(os_decision, analysis_results)
        overlay_trace = self._build_overlay_trace(ctx, runtime_context, os_decision, confidence, ttl)

        return {
            "version": "OS_ENGINE_CONTRACT_1.1",
            "timestamp": ctx.timestamp,
            "context": asdict(ctx),

            "os_state": os_decision.os_state,
            "decision_mode": os_decision.decision_mode,
            "rationale": os_decision.rationale,
            "confidence": confidence,
            "signals_summary": signals_summary,
            "ttl": ttl,
            "overlay_trace": overlay_trace,

            "analysis_results": analysis_results,
            "runtime_context": asdict(runtime_context),

            "proposals": proposals,

            "external_signals": external_signals.get("quality", {}),
            "dispatch": dispatch_status,
        }

    # ============================================================
    # Default CFG blocks (para que el CORE sea robusto si falta cfg)
    # ============================================================

    @staticmethod
    def _default_cfg_shock() -> Dict[str, Any]:
        return {
            "general": {"min_length": 6},
            "z_score": {"enabled": True, "window": 6, "threshold": 2.0},
            "cusum": {"enabled": True, "k": 0.1, "h": 3.0},
            "breakpoint": {"enabled": True, "window": 4, "threshold": 2.0},
            "weights": {"z": 0.35, "cusum": 0.35, "break": 0.30},
            "market_analysis": {"enabled": True},
        }

    @staticmethod
    def _default_cfg_volatility() -> Dict[str, Any]:
        return {
            "general": {"min_length": 6},
            "ewma": {"lambda": 0.7},
            "shock": {"multiplier": 1.0},
            "market": {"enabled": True},
            "weights": {"historical": 0.35, "ewma": 0.35, "shock": 0.20, "market": 0.10},
            "risk_bands": {"low": 0.5, "medium": 1.2},
        }

    @staticmethod
    def _default_cfg_trend() -> Dict[str, Any]:
        return {
            "general": {"min_length": 6},
            "regression": {"window": 6},
            "thresholds": {"up": 0.15, "down": 0.15},
            "confidence": {
                "full_window": 12,
                "sigma_ref": 1.2,
                "slope_ref": 0.25,
                "w_base": 0.40,
                "w_trend": 0.40,
                "w_vol": 0.10,
                "w_shock": 0.10,
            },
            "stability": {"cv_low": 0.10, "cv_high": 0.40},
            "chaos": {"sigma_threshold": 1.5, "shock_threshold": 0.35},
        }

    @staticmethod
    def _default_cfg_phi() -> Dict[str, Any]:
        return {
            "general": {"min_length": 6},
            "windows": {"short": 6, "long": 12, "stability": 6},
            "weights": {"short": 0.55, "long": 0.45},
            "limits": {"max_phi": 1.0},
            "stability": {"max_std": 0.35},
            "confidence": {"sigma_ref": 1.2},
        }

    @staticmethod
    def _default_cfg_psi() -> Dict[str, Any]:
        return {
            "weights": {"shock": 0.35, "volatility": 0.35, "phi": 0.20, "relative": 0.10},
            "limits": {"max_psi": 1.0},
            "penalties": {"trend": 0.35},
            "levels": {"minor": 0.30, "moderate": 0.60},
            "confidence_weights": {"shock": 0.40, "phi": 0.30, "trend": 0.30},
        }

    def _build_confidence(self, analysis_results: Dict[str, Any], external_signals: Dict[str, Any]) -> Dict[str, Any]:
        psi_conf = float(analysis_results.get("psi", {}).get("psi", {}).get("confidence", 0.0) or 0.0)
        trend_conf = float(analysis_results.get("trend", {}).get("trend", {}).get("confidence", 0.0) or 0.0)
        external_min = float(external_signals.get("quality", {}).get("confidence_min", 0.0) or 0.0)
        external_mean = float(external_signals.get("quality", {}).get("confidence_mean", 0.0) or 0.0)
        effective = round((psi_conf * 0.5) + (trend_conf * 0.3) + (external_mean * 0.2), 4)
        return {
            "effective": effective,
            "psi": round(psi_conf, 4),
            "trend": round(trend_conf, 4),
            "external_min": round(external_min, 4),
            "external_mean": round(external_mean, 4),
        }

    def _build_signals_summary(self, analysis_results: Dict[str, Any], external_signals: Dict[str, Any]) -> Dict[str, Any]:
        shock = analysis_results.get("shock", {})
        volatility = analysis_results.get("volatility", {})
        trend = analysis_results.get("trend", {})
        phi = analysis_results.get("phi", {})
        psi = analysis_results.get("psi", {})
        return {
            "shock_flag": int(shock.get("shock_flag", 0) or 0),
            "shock_intensity": round(float(shock.get("product", {}).get("intensity", 0.0) or 0.0), 4),
            "volatility_band": str(volatility.get("risk_band", "low") or "low"),
            "volatility_total": round(float(volatility.get("sigma", {}).get("total", 0.0) or 0.0), 4),
            "trend_direction": str(trend.get("trend", {}).get("direction", "flat") or "flat"),
            "trend_strength": round(float(trend.get("trend", {}).get("strength", 0.0) or 0.0), 4),
            "phi_value": round(float(phi.get("phi", {}).get("value", 0.0) or 0.0), 4),
            "psi_effective": round(float(psi.get("psi", {}).get("effective", 0.0) or 0.0), 4),
            "external_quality": external_signals.get("quality", {}),
        }

    def _build_ttl(self, os_decision: OSDecision, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        shock_flag = int(analysis_results.get("shock", {}).get("shock_flag", 0) or 0)
        if os_decision.decision_mode == "SURVIVAL":
            hours = 6
        elif os_decision.decision_mode == "DEFENSIVE":
            hours = 12
        elif os_decision.decision_mode == "CONSERVATIVE":
            hours = 24
        else:
            hours = 48
        if shock_flag:
            hours = max(4, hours // 2)
        return {"unit": "hours", "value": hours}

    def _build_overlay_trace(
        self,
        ctx: EngineContext,
        runtime_context: RuntimeContext,
        os_decision: OSDecision,
        confidence: Dict[str, Any],
        ttl: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "scope": {
                "product_id": ctx.product_id,
                "market_id": ctx.market_id,
                "country": ctx.country,
            },
            "decision_mode": os_decision.decision_mode,
            "os_state": os_decision.os_state,
            "multipliers": dict(runtime_context.multipliers),
            "flags": dict(runtime_context.flags),
            "guardrails": dict(runtime_context.guardrails),
            "confidence_effective": confidence.get("effective", 0.0),
            "ttl": ttl,
        }
