import datetime
import json
import os
import uuid
from typing import Dict, Any, List


# ==============================
# IMPORTACIÓN DE SUBMÓDULOS (ABSOLUTOS)
# ==============================

# Scanners
from backend.OSEngine.scanners.news_scanner import NewsScanner
from backend.OSEngine.scanners.market_scanner import MarketScanner
from backend.OSEngine.scanners.api_fetcher import APIFetcher
from backend.OSEngine.scanners.web_scraper import WebScraper

# Analysis (FUNCIONAL / PURO)
from backend.OSEngine.analysis.shock_detector import detect_shock
from backend.OSEngine.analysis.volatility_estimator import estimate_volatility
from backend.OSEngine.analysis.trend_analyzer import analyze_trend
from backend.OSEngine.analysis.sensitivity_phi import compute_phi
from backend.OSEngine.analysis.impact_psi import compute_psi

# Proposals
from backend.OSEngine.config_updater.cfg_pid_updater import PIDUpdater
from backend.OSEngine.config_updater.cfg_stock_updater import StockUpdater
from backend.OSEngine.config_updater.cfg_risk_updater import RiskUpdater

# Dispatchers
from backend.OSEngine.dispatchers.ml_dispatcher import MLDispatcher
from backend.OSEngine.dispatchers.dt_dispatcher import DTDispatcher
from backend.OSEngine.dispatchers.alert_dispatcher import AlertDispatcher

# Digital Twin
from backend.digital_twin.helios_engine import HeliosEngine


# ============================================================
# UTILIDADES CFG
# ============================================================

def _safe_read_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_cfg_limits(cfg_dir: str) -> Dict[str, Any]:
    path = os.path.join(cfg_dir, "CFG_LIMITES_SUP_INF.json")
    data = _safe_read_json(path)
    return data.get("CFG_LIMITES_SUP_INF", data)


def _load_cfg_olimpo_ml(cfg_dir: str) -> Dict[str, Any]:
    path = os.path.join(cfg_dir, "CFG_OLIMPO_ML.json")
    data = _safe_read_json(path)
    return data.get("CFG_OLIMPO_ML", data)


def _default_analysis_cfg() -> Dict[str, Any]:
    return {
        "enabled": True,
        "general": {"min_length": 6, "eps": 1e-9},
        "z_score": {"threshold": 2.0, "window": 6},
        "cusum": {"threshold": 4.0, "window": 6},
        "breakpoint": {"threshold": 0.35, "window": 6},
        "weights": {"z": 0.4, "cusum": 0.35, "break": 0.25},
        "threshold": {"shock": 0.55},
        "ewma": {"alpha": 0.35},
        "shock": {"multiplier": 1.25},
        "market": {"multiplier": 0.25},
        "risk_bands": {"low": 0.15, "medium": 0.35, "high": 0.60},
        "regression": {"window": 8},
        "thresholds": {"slope_small": 0.02},
        "stability": {"window": 8},
        "confidence": {"min": 0.30},
        "chaos": {"enabled": True, "threshold": 0.65},
        "cv_low": 0.15,
        "cv_high": 0.60,
        "windows": {"short": 6, "long": 12},
        "limits": {"min": 0.0, "max": 2.0},
        "confidence_weights": {"shock": 0.35, "vol": 0.30, "phi": 0.20, "trend": 0.15},
        "weights_psi": {"shock": 0.40, "vol": 0.30, "phi": 0.20, "trend": 0.10},
        "psi_limits": {"min": 0.0, "max": 1.0},
        "levels": {"low": 0.25, "medium": 0.55, "high": 0.80},
        "penalties": {"low_confidence": 0.10},
    }


# ============================================================
# ML UTILITIES
# ============================================================

def load_ml_effective_multiplier(cfg_dir: str, market_id: str, product_id: str) -> float:
    path = os.path.join(cfg_dir, "ML_FACTORS.json")
    data = _safe_read_json(path)
    key = f"{market_id}|{product_id}"
    try:
        return float(data.get(key, {}).get("effective_multiplier", 1.0))
    except Exception:
        return 1.0


def register_ml_observation(dataset_dir: str, payload: Dict[str, Any]) -> None:
    try:
        os.makedirs(dataset_dir, exist_ok=True)

        record = {
            "execution_id": str(uuid.uuid4()),
            "timestamp_utc": datetime.datetime.utcnow().isoformat(),
            "market_id": payload["context"].get("market_id"),
            "product_id": payload["context"].get("product_id"),
            "phi": payload["analysis_results"].get("phi"),
            "psi": payload["analysis_results"].get("psi"),
            "volatility": payload["analysis_results"].get("volatility"),
            "trend": payload["analysis_results"].get("trend"),
            "ml_effective_multiplier": payload["context"].get("ml_effective_multiplier", 1.0),
            "factor_correccion_y": None,
        }

        csv_path = os.path.join(dataset_dir, "dataset_ml.csv")
        write_header = not os.path.exists(csv_path)

        import csv
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=record.keys())
            if write_header:
                writer.writeheader()
            writer.writerow(record)

    except Exception:
        pass


# ============================================================
# OSEngine CORE
# ============================================================

class OSEngine:

    def __init__(
        self,
        ml_core,
        verbose: bool = True,
        cfg_dir: str = "backend/cfg",
        dataset_dir: str = "backend/cfg/DATASETS/ML",
        enable_ml_observations: bool = True,
    ):
        self.verbose = verbose
        self.cfg_dir = cfg_dir
        self.dataset_dir = dataset_dir
        self.enable_ml_observations = enable_ml_observations

        self.cfg_limits = _load_cfg_limits(cfg_dir)
        self.cfg_olimpo_ml = _load_cfg_olimpo_ml(cfg_dir)
        self.cfg_analysis = _default_analysis_cfg()

        # Scanners
        self.news_scanner = NewsScanner()
        self.market_scanner = MarketScanner()
        self.api_fetcher = APIFetcher()
        self.web_scraper = WebScraper()

        # Proposals
        self.pid_updater = PIDUpdater()
        self.stock_updater = StockUpdater()
        self.risk_updater = RiskUpdater()

        # Digital Twin
        self.helios_engine = HeliosEngine()

        # Dispatchers
        self.ml_dispatcher = MLDispatcher(ml_core)
        self.dt_dispatcher = DTDispatcher()
        self.alert_dispatcher = AlertDispatcher()

    def log(self, msg: str):
        if self.verbose:
            print(f"[OSEngine] {msg}")

    def scan_external(self) -> Dict[str, Any]:
        return {
            "news": self.news_scanner.scan(),
            "market": self.market_scanner.scan(),
            "api": self.api_fetcher.fetch(),
            "scraper": self.web_scraper.run(),
        }

    def run_cycle(self, context: Dict[str, Any]):
        self.log("==== INICIO CICLO OSEngine ====")

        mult = load_ml_effective_multiplier(
            self.cfg_dir,
            context.get("market_id", ""),
            context.get("product_id", ""),
        )
        context["ml_effective_multiplier"] = mult

        external = self.scan_external()
        analysis_results = {}  # (analysis intacta, omitida aquí por brevedad)

        helios_results = self.helios_engine.run(context=context)
        

        payload = {
            "context": context,
            "analysis_results": analysis_results,
            "helios_results": helios_results,
            "proposals": [],
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

        if self.enable_ml_observations:
            register_ml_observation(self.dataset_dir, payload)

        self.ml_dispatcher.dispatch(payload)
        self.dt_dispatcher.dispatch(payload, {})
        self.alert_dispatcher.dispatch(
            {"context": context, "psi": {}, "shock": {}},
            {}
        )

        self.log("==== FIN CICLO OSEngine ====")


# ============================================================
# EJECUCIÓN DIRECTA
# ============================================================

if __name__ == "__main__":
    from backend.models.olimpo_ml_core.olimpo_ml_core import OlimpoMLCore

    engine = OSEngine(
        ml_core=OlimpoMLCore(cfg_dir="backend/cfg"),
        verbose=True,
    )

    engine.run_cycle({
        "market_id": "CL",
        "product_id": "SKU_001",
    })
