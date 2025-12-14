import datetime
from pathlib import Path
from typing import Dict, Any, List

# ==============================
# IMPORTACIÓN DE SUBMÓDULOS
# ==============================

# Scanners
from scanners.news_scanner import NewsScanner
from scanners.market_scanner import MarketScanner
from scanners.api_fetcher import APIFetcher
from scanners.web_scraper import WebScraper

# Analysis
from analysis.shock_detector import ShockDetector
from analysis.volatility_estimator import VolatilityEstimator
from analysis.trend_analyzer import TrendAnalyzer
from analysis.sensitivity_phi import SensitivityPhi
from analysis.impact_psi import ImpactPsi

# Proposals (NO actualizan CFG)
from config_updater.cfg_pid_updater import PIDUpdater
from config_updater.cfg_stock_updater import StockUpdater
from config_updater.cfg_risk_updater import RiskUpdater

# Dispatchers
from dispatchers.ml_dispatcher import MLDispatcher
from dispatchers.dt_dispatcher import DigitalTwinDispatcher
from dispatchers.alert_dispatcher import AlertDispatcher

# HELIOS (Digital Twin REAL)
from digital_twin.helios_engine import HeliosEngine



class OSEngine:
    """
    OSEngine CORE

    Rol:
    - Observa el entorno (scanners)
    - Analiza señales (shock, volatilidad, tendencia, φ, ψ)
    - Ejecuta HELIOS (Digital Twin)
    - Recolecta PROPUESTAS técnicas (CFGProposal)
    - Despacha estado estructurado

    OSEngine NO:
    - Decide
    - Aprende
    - Modifica CFG
    """

    # 🔧 CAMBIO 1: inyección de ml_core
    def __init__(self, ml_core, verbose: bool = True):
        self.verbose = verbose

        # ------------------------------
        # Scanners
        # ------------------------------
        self.news_scanner = NewsScanner()
        self.market_scanner = MarketScanner()
        self.api_fetcher = APIFetcher()
        self.web_scraper = WebScraper()

        # ------------------------------
        # Analysis
        # ------------------------------
        self.shock_detector = ShockDetector()
        self.volatility_estimator = VolatilityEstimator()
        self.trend_analyzer = TrendAnalyzer()
        self.phi_analyzer = SensitivityPhi()
        self.psi_analyzer = ImpactPsi()

        # ------------------------------
        # Proposal generators
        # ------------------------------
        self.pid_updater = PIDUpdater()
        self.stock_updater = StockUpdater()
        self.risk_updater = RiskUpdater()

        # ------------------------------
        # HELIOS (Digital Twin)
        # ------------------------------
        self.helios_engine = HeliosEngine()

        # ------------------------------
        # Dispatchers
        # ------------------------------
        self.ml_dispatcher = MLDispatcher(ml_core)   # ✅ correcto
        self.dt_dispatcher = DigitalTwinDispatcher()
        self.alert_dispatcher = AlertDispatcher()

    # ==============================
    # LOG SIMPLE
    # ==============================

    def log(self, message: str):
        if self.verbose:
            print(f"[OSEngine] {message}")

    # ==============================
    # 1) SCANNING
    # ==============================

    def scan_external(self) -> Dict[str, Any]:
        self.log("Iniciando SCAN externo")

        external_data = {
            "news": self.news_scanner.scan(),
            "market": self.market_scanner.scan(),
            "api": self.api_fetcher.fetch(),
            "scraper": self.web_scraper.run(),
        }

        self.log("SCAN externo completado")
        return external_data

    # ==============================
    # 2) ANALYSIS
    # ==============================

    def analyze(self, external_data: Dict[str, Any]) -> Dict[str, Any]:
        self.log("Iniciando análisis de señales")

        analysis_results = {
            "shock": self.shock_detector.detect(external_data),
            "volatility": self.volatility_estimator.estimate(external_data),
            "trend": self.trend_analyzer.analyze(external_data),
        }

        analysis_results["phi"] = self.phi_analyzer.compute(
            external_data, analysis_results
        )
        analysis_results["psi"] = self.psi_analyzer.compute(
            external_data, analysis_results
        )

        self.log("Análisis de señales completado")
        return analysis_results

    # ==============================
    # 3) PROPUESTAS (NO DECISIONES)
    # ==============================

    def collect_proposals(
        self,
        analysis_results: Dict[str, Any],
        helios_results: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        self.log("Recolectando propuestas técnicas")

        proposals: List[Dict[str, Any]] = []
        proposals += self.pid_updater.propose(analysis_results, helios_results, context)
        proposals += self.stock_updater.propose(analysis_results, helios_results, context)
        proposals += self.risk_updater.propose(analysis_results, helios_results, context)

        self.log(f"Propuestas recolectadas: {len(proposals)}")
        return proposals

    # ==============================
    # 4) DISPATCH
    # ==============================

    def dispatch(self, payload: Dict[str, Any]) -> None:
        self.ml_dispatcher.dispatch(payload)
        self.dt_dispatcher.dispatch(payload)
        self.alert_dispatcher.dispatch(payload)

    # ==============================
    # CICLO COMPLETO
    # ==============================

    def run_cycle(self, context: Dict[str, Any] = None):

        self.log("==== INICIO CICLO OSEngine ====")
        context = context or {}

        # 1) Observación
        external_data = self.scan_external()

        # 2) Análisis
        analysis_results = self.analyze(external_data)

        # 🔧 CAMBIO 2: HELIOS ejecuta la simulación (NO el dispatcher)
        helios_results = self.helios_engine.run(
            analysis_results=analysis_results,
            context=context
        )

        # 3) Propuestas
        proposals = self.collect_proposals(
            analysis_results, helios_results, context
        )

        # 🔧 CAMBIO 3: payload limpio (sin external_data)
        payload = {
            "context": context,
            "analysis_results": analysis_results,
            "helios_results": helios_results,
            "proposals": proposals,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

        # 4) Dispatch
        self.dispatch(payload)

        self.log("==== FIN CICLO OSEngine ====")


# ==============================
# EJECUCIÓN DIRECTA (OPCIONAL)
# ==============================

if __name__ == "__main__":
    from models.olimpo_ml_core.olimpo_ml_core import OlimpoMLCore

    ml_core = OlimpoMLCore(cfg_dir="backend/cfg")
    engine = OSEngine(ml_core=ml_core, verbose=True)
    engine.run_cycle()
