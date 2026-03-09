"""
helios_engine.py
Wrapper del motor HELIOS Digital Twin para OLIMPO / backend.

Respeta la implementación original de HELIOS_DIGITALTWIN3.py, pero:

- Usa rutas relativas al directorio backend/ (sin rutas absolutas).
- Carga automáticamente todos los CFG desde backend/cfg usando CFG_HELIOS_RUTAS.json.
- Expone métodos amigables para la API:
    * run_epsilon(epsilon_input: dict) -> dict
    * run_sigma(sigma_input: dict) -> dict
    * run_poseidon(poseidon_input: dict) -> dict
    * run_digital_twin(epsilon_input, sigma_input, poseidon_input, write_output=False) -> dict
- Permite activar o desactivar logs desde el código del servidor.
"""

import json
import math
import random
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

# ============================================================
# FLAG GLOBAL PARA LOGS (se puede cambiar desde HeliosEngine)
# ============================================================

LOG_ENABLED = True


def log(msg: str) -> None:
    """
    Log central de HELIOS.
    Se controla con la variable global LOG_ENABLED para poder
    desactivar logs en modo servidor/API si es necesario.
    """
    if LOG_ENABLED:
        print(f"[HELIOS_DT] {msg}")


def safe_load_json(path: Path, name: str) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"[HELIOS_DT] No se encontró {name}: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def clamp(value: float, vmin: float, vmax: float) -> float:
    return max(vmin, min(vmax, value))


def tanh(x: float) -> float:
    return math.tanh(x)


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def unwrap(cfg: Dict[str, Any], root_key: str) -> Dict[str, Any]:
    """
    Algunos CFG vienen envueltos en una clave raíz (ej: 'CFG_HELIOS_GENERAL').
    Esta función devuelve el contenido interno si existe.
    """
    return cfg.get(root_key, cfg)


def set_nested(cfg: Dict[str, Any], path: str, value: Any) -> bool:
    """
    Aplica un valor en una ruta anidada (ej: 'productos.item.shock').
    Replica la lógica de olimpo_ml_core para consistencia.
    """
    keys = path.split(".")
    cur = cfg
    for i, k in enumerate(keys[:-1]):
        if isinstance(cur, dict):
            if k not in cur:
                return False
            cur = cur[k]
        elif isinstance(cur, list):
            try:
                idx = int(k)
                if idx < 0 or idx >= len(cur):
                    return False
                cur = cur[idx]
            except ValueError:
                return False
        else:
            return False

    last = keys[-1]
    if isinstance(cur, dict) and last in cur:
        cur[last] = value
        return True
    elif isinstance(cur, list):
        try:
            idx = int(last)
            if 0 <= idx < len(cur):
                cur[idx] = value
                return True
        except ValueError:
            pass
    return False


# ============================================================
# Clase de rutas (usa CFG_HELIOS_RUTAS.json)
# ============================================================

class HeliosConfigRutas:
    def __init__(self, cfg_rutas: Dict[str, Any]) -> None:
        root = cfg_rutas.get("CFG_HELIOS_RUTAS", cfg_rutas)

        rutas_principales = root.get("rutas_principales", {})
        cfg_archivos = root.get("cfg_archivos", {})
        rutas_input = root.get("rutas_input", {})
        rutas_pred = root.get("rutas_prediccion_output", {})

        # NOTA:
        # Para backend usamos siempre rutas RELATIVAS al directorio
        # donde vive el backend. El JSON puede seguir definiendo
        # base_dir, cfg_dir, etc., pero aquí asumimos que son
        # relativos al proyecto (sin caminos absolutos).

        base_dir_str = rutas_principales.get("base_dir", ".")
        self.base_dir = Path(base_dir_str).resolve()

        # Si en el JSON los directorios son relativos (ej: "cfg", "entrada"),
        # se interpretan relativos a base_dir.
        cfg_dir_str = rutas_principales.get("cfg_dir", "cfg")
        entrada_dir_str = rutas_principales.get("entrada_dir", "entrada")
        pred_dir_str = rutas_principales.get("prediccion_dir", "prediccion")

        self.cfg_dir = (self.base_dir / cfg_dir_str).resolve()
        self.entrada_dir = (self.base_dir / entrada_dir_str).resolve()
        self.prediccion_dir = (self.base_dir / pred_dir_str).resolve()

        # Archivos CFG
        self.productos_cfg_file = cfg_archivos.get("productos_cfg", "CFG_HELIOS_PRODUCTOS.json")
        self.mercados_cfg_file = cfg_archivos.get("mercados_cfg", "CFG_HELIOS_MERCADOS.json")
        self.shocks_cfg_file = cfg_archivos.get("shocks_cfg", "CFG_MERCADO_SHOCKS.json")
        self.demanda_mercado_cfg_file = cfg_archivos.get("demanda_mercado_cfg", "CFG_DEMANDA_MERCADO.json")
        self.comex_cfg_file = cfg_archivos.get("comex_cfg", "CFG_HELIOS_COMEX.json")
        self.limites_sup_inf_cfg_file = cfg_archivos.get("limites_sup_inf_cfg", "CFG_LIMITES_SUP_INF.json")
        self.helios_general_cfg_file = cfg_archivos.get("helios_general_cfg", "CFG_HELIOS_GENERAL.json")

        # Inputs
        self.epsilon_input_file = rutas_input.get("epsilon_input", "CFG_INPUT_EPSILON.json")
        self.sigma_input_file = rutas_input.get("sigma_input", "CFG_INPUT_SIGMA.json")
        self.poseidon_input_file = rutas_input.get("poseidon_input", "CFG_INPUT_POSEIDON.json")

        # Output DT único
        self.dt_output_file = rutas_pred.get("resultado_digital_twin", "PREDICCION_DT.json")

        # Archivo de parches ML (Live Intelligence)
        self.patches_file = "CFG_PATCHES.json"


# ============================================================
# Motor Digital Twin (implementación original)
# ============================================================

class HeliosDigitalTwinEngine:
    def __init__(self, cfg_rutas_path: Path) -> None:
        self.cfg_rutas_path = cfg_rutas_path
        self.rutas: Optional[HeliosConfigRutas] = None

        # CFGs
        self.cfg_general: Dict[str, Any] = {}
        self.cfg_limites: Dict[str, Any] = {}
        self.cfg_mercados: Dict[str, Any] = {}
        self.cfg_productos: Dict[str, Any] = {}
        self.cfg_demanda_mercado: Dict[str, Any] = {}
        self.cfg_mercado_shocks: Dict[str, Any] = {}
        self.cfg_comex: Dict[str, Any] = {}

        # Inputs (se rellenan desde JSON o desde la API)
        self.epsilon_input: Dict[str, Any] = {}
        self.sigma_input: Dict[str, Any] = {}
        self.poseidon_input: Dict[str, Any] = {}

        # Semilla fija para Montecarlo
        random.seed(42)

    # ------------------- CARGA DE RUTAS Y CFG -------------------

    def load_rutas(self) -> None:
        log(f"Cargando CFG_HELIOS_RUTAS desde: {self.cfg_rutas_path}")
        cfg_rutas = safe_load_json(self.cfg_rutas_path, "CFG_HELIOS_RUTAS.json")
        self.rutas = HeliosConfigRutas(cfg_rutas)
        log(f"Rutas base dir: {self.rutas.base_dir}")

    def load_cfg(self) -> None:
        assert self.rutas is not None, "Rutas no inicializadas"
        cfg_dir = self.rutas.cfg_dir

        raw_general = safe_load_json(cfg_dir / self.rutas.helios_general_cfg_file,
                                     self.rutas.helios_general_cfg_file)
        raw_limites = safe_load_json(cfg_dir / self.rutas.limites_sup_inf_cfg_file,
                                     self.rutas.limites_sup_inf_cfg_file)
        raw_mercados = safe_load_json(cfg_dir / self.rutas.mercados_cfg_file,
                                      self.rutas.mercados_cfg_file)
        raw_productos = safe_load_json(cfg_dir / self.rutas.productos_cfg_file,
                                       self.rutas.productos_cfg_file)
        raw_demanda_mercado = safe_load_json(cfg_dir / self.rutas.demanda_mercado_cfg_file,
                                             self.rutas.demanda_mercado_cfg_file)
        raw_shocks = safe_load_json(cfg_dir / self.rutas.shocks_cfg_file,
                                    self.rutas.shocks_cfg_file)
        raw_comex = safe_load_json(cfg_dir / self.rutas.comex_cfg_file,
                                   self.rutas.comex_cfg_file)

        # --- INYECCIÓN DE INTELIGENCIA VIVA (ML CORE) ---
        # Mapeamos los archivos a sus objetos raw para aplicar parches
        raw_map = {
            self.rutas.helios_general_cfg_file: raw_general,
            self.rutas.limites_sup_inf_cfg_file: raw_limites,
            self.rutas.mercados_cfg_file: raw_mercados,
            self.rutas.productos_cfg_file: raw_productos,
            self.rutas.demanda_mercado_cfg_file: raw_demanda_mercado,
            self.rutas.shocks_cfg_file: raw_shocks,
            self.rutas.comex_cfg_file: raw_comex,
        }
        self._apply_ml_patches(raw_map)

        self.cfg_general = unwrap(raw_general, "CFG_HELIOS_GENERAL")
        self.cfg_limites = unwrap(raw_limites, "CFG_LIMITES_SUP_INF")
        self.cfg_mercados = raw_mercados
        self.cfg_productos = raw_productos
        self.cfg_demanda_mercado = unwrap(raw_demanda_mercado, "cfg_DEMANDA_MERCADO")
        self.cfg_mercado_shocks = unwrap(raw_shocks, "cfg_MERCADO_SHOCKS")
        self.cfg_comex = unwrap(raw_comex, "CFG_HELIOS_COMEX")

        log("Configuraciones cargadas correctamente desde carpeta CFG.")

    def _apply_ml_patches(self, raw_map: Dict[str, Any]) -> None:
        """
        Lee CFG_PATCHES.json (generado por OlimpoMLCore) y aplica los cambios
        a los diccionarios raw cargados en memoria.
        Esto asegura que el Digital Twin corra con los 'números vivos'.
        """
        assert self.rutas is not None
        patches_path = self.rutas.cfg_dir / self.rutas.patches_file
        
        if not patches_path.exists():
            return

        try:
            # Usamos json estándar aquí para evitar dependencia circular o fallos en safe_load
            with patches_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            
            patches = data.get("patches", [])
            applied_count = 0
            
            for p in patches:
                cfg_file = p.get("cfg_file")
                path = p.get("parameter_path")
                val = p.get("new_value")
                
                if cfg_file in raw_map:
                    if set_nested(raw_map[cfg_file], path, val):
                        applied_count += 1
            
            if applied_count > 0:
                log(f"[HELIOS_DT] Se aplicaron {applied_count} parches de ML Core (Live Intelligence).")
        except Exception as e:
            log(f"[HELIOS_DT] Advertencia: No se pudieron aplicar parches ML: {e}")

    def load_inputs(self) -> None:
        """
        Versión original basada en archivos ENTRADA/.
        Se mantiene para compatibilidad, pero la API usará directamente
        los atributos epsilon_input, sigma_input y poseidon_input.
        """
        assert self.rutas is not None
        entrada_dir = self.rutas.entrada_dir

        # EPSILON
        try:
            raw_eps = safe_load_json(entrada_dir / self.rutas.epsilon_input_file,
                                     self.rutas.epsilon_input_file)
            self.epsilon_input = unwrap(raw_eps, "CFG_INPUT_EPSILON")
        except FileNotFoundError:
            log(f"[HELIOS] Input EPSILON no encontrado ({self.rutas.epsilon_input_file}), se omite.")
            self.epsilon_input = {}

        # SIGMA
        try:
            raw_sig = safe_load_json(entrada_dir / self.rutas.sigma_input_file,
                                     self.rutas.sigma_input_file)
            self.sigma_input = unwrap(raw_sig, "CFG_INPUT_SIGMA")
        except FileNotFoundError:
            log(f"[HELIOS] Input SIGMA no encontrado ({self.rutas.sigma_input_file}), se omite.")
            self.sigma_input = {}

        # POSEIDON
        try:
            raw_pos = safe_load_json(entrada_dir / self.rutas.poseidon_input_file,
                                     self.rutas.poseidon_input_file)
            self.poseidon_input = unwrap(raw_pos, "CFG_INPUT_POSEIDON")
        except FileNotFoundError:
            log(f"[HELIOS] Input POSEIDON no encontrado ({self.rutas.poseidon_input_file}), se omite.")
            self.poseidon_input = {}

        log("Inputs de ENTRADA cargados (parcial o totalmente).")

    # ------------------- HELPERS CFG -------------------

    def get_producto_cfg(self, product_id: str) -> Dict[str, Any]:
        for prod in self.cfg_productos.get("productos", []):
            if prod.get("product_id") == product_id:
                return prod
        return {}

    def get_shocks_mercado_cfg(self, market_id: str) -> Optional[Dict[str, Any]]:
        for m in self.cfg_mercado_shocks.get("shocks_por_mercado", []):
            if m.get("market_id") == market_id:
                return m
        return None

    # ============================================================
    # BLOQUE φ: shocks mercado + producto + cohesión temporal
    # ============================================================

    def compute_market_shock_series(self, market_id: str, horizonte: int) -> List[float]:
        S = [0.0] * horizonte
        m_cfg = self.get_shocks_mercado_cfg(market_id)
        if not m_cfg:
            return S

        mag_prom = m_cfg.get("shock_magnitud_promedio", 0.1)
        impacto_demanda = m_cfg.get("impacto_demanda", 0.8)
        t_rec = m_cfg.get("tiempo_recuperacion_meses", 6)

        if t_rec <= 0:
            t_rec = 6

        base = mag_prom * impacto_demanda

        for t in range(horizonte):
            factor = 1.0 - math.exp(-(t + 1) / float(t_rec))
            S[t] = base * factor

        return S

    def compute_phi_series_for_product(
        self,
        product_id: str,
        market_id: str,
        horizonte: int
    ) -> Dict[str, List[float]]:
        prod_cfg = self.get_producto_cfg(product_id)
        shock_cfg = prod_cfg.get("shock", {}) if prod_cfg else {}

        sens = shock_cfg.get("shock_sensibilidad_indice", 1.0)
        t_rec_p = shock_cfg.get("shock_tiempo_recuperacion_meses", 3)

        if t_rec_p <= 0:
            t_rec_p = 3
        rho_p = math.exp(-1.0 / float(t_rec_p))

        S_m = self.compute_market_shock_series(market_id, horizonte)
        S_p = [0.0] * horizonte
        phi = [0.0] * horizonte

        for t in range(horizonte):
            S_p[t] = sens * S_m[t]
            if t == 0:
                phi[t] = (1.0 - rho_p) * S_p[t]
            else:
                phi[t] = rho_p * phi[t - 1] + (1.0 - rho_p) * S_p[t]

        return {"S_m": S_m, "S_p": S_p, "phi": phi}

    # ============================================================
    # BLOQUE Φ: filtro gaussiano / anti-spike / anti-bullwhip
    # ============================================================

    def apply_gaussian_filter(
        self,
        phi_series: List[float],
        base_series: List[float],
        base_orders: Optional[List[float]] = None,
        ventana_bw: int = 6
    ) -> List[float]:
        horizonte = len(phi_series)
        G = [0.0] * horizonte

        dt_cfg = self.cfg_general.get("digital_twin", {})
        G_max = dt_cfg.get("influencia_total", 0.5)
        k_bw = 2.0

        if horizonte == 0:
            return G

        mu_phi = sum(phi_series) / horizonte
        var_phi = sum((x - mu_phi) ** 2 for x in phi_series) / max(1, horizonte - 1)
        sigma_phi = math.sqrt(var_phi) if var_phi > 0 else 1.0

        for t in range(horizonte):
            phi_t = phi_series[t]

            phi_sat = G_max * tanh(phi_t / max(G_max, 1e-6))

            z = abs((phi_t - mu_phi) / sigma_phi)
            p_spike = sigmoid(z - 2.0)
            phi_spike = (1.0 - p_spike) * phi_sat

            if base_orders is not None and t >= ventana_bw:
                sub_Q = base_orders[max(0, t - ventana_bw + 1):t + 1]
                sub_D = base_series[max(0, t - ventana_bw + 1):t + 1]
                if len(sub_Q) > 1 and len(sub_D) > 1:
                    var_Q = self._var(sub_Q)
                    var_D = self._var(sub_D)
                    F = var_Q / var_D if var_D > 0 else 1.0
                    p_bw = sigmoid(k_bw * (F - 1.0))
                else:
                    p_bw = 0.0
            else:
                p_bw = 0.0

            G[t] = (1.0 - p_bw) * phi_spike

        return G

    @staticmethod
    def _var(data: List[float]) -> float:
        if len(data) <= 1:
            return 0.0
        m = sum(data) / len(data)
        return sum((x - m) ** 2 for x in data) / (len(data) - 1)

    # ============================================================
    # BLOQUE Ψ: perfil humano (stub) y ajuste de parámetros
    # ============================================================

    def compute_psi_for_product(self, product_id: str) -> float:
        return 0.5

    def adjust_params_with_psi(self, psi: float) -> Dict[str, float]:
        kappa_base = 0.3
        delta_max_base = 0.2

        kappa = kappa_base * (0.5 + psi)
        delta_max = delta_max_base * (0.7 + 0.6 * psi)

        return {"kappa": kappa, "delta_max": delta_max}

    # ============================================================
    # Forecast base simple para Epsilon (SES)
    # ============================================================

    @staticmethod
    def simple_ses_forecast(
        demanda_hist: List[float],
        horizonte: int,
        alpha: float
    ) -> Tuple[List[float], List[float]]:
        if not demanda_hist or horizonte <= 0:
            return [], []

        s = demanda_hist[0]
        for x in demanda_hist[1:]:
            s = alpha * x + (1.0 - alpha) * s

        forecast = [s] * horizonte

        if len(demanda_hist) > 1:
            m = sum(demanda_hist) / len(demanda_hist)
            var = sum((x - m) ** 2 for x in demanda_hist) / (len(demanda_hist) - 1)
            sigma = math.sqrt(var)
        else:
            sigma = 0.1 * s

        sigma_base = [sigma] * horizonte
        return forecast, sigma_base

    # ============================================================
    # APLICACIÓN DEL DT + CLAMP
    # ============================================================

    def apply_dt_to_forecast(
        self,
        forecast_base: List[float],
        G_series: List[float],
        kappa: float,
        delta_max: float
    ) -> List[float]:
        horizonte = len(forecast_base)
        dt_series = [0.0] * horizonte

        for t in range(horizonte):
            d0 = forecast_base[t]
            g_t = G_series[t] if t < len(G_series) else 0.0
            d_tilde = d0 * (1.0 + kappa * g_t)

            if t == 0:
                dt_series[t] = max(0.0, d_tilde)
            else:
                prev = dt_series[t - 1]
                min_val = (1.0 - delta_max) * prev
                max_val = (1.0 + delta_max) * prev
                dt_series[t] = clamp(d_tilde, min_val, max_val)

        return dt_series

    # ============================================================
    # MONTECARLO
    # ============================================================

    def montecarlo_scenarios(
        self,
        dt_series: List[float],
        sigma_base: Optional[List[float]] = None,
        n_scenarios: int = 1000,
        trunc_z: float = 3.0
    ) -> Dict[str, List[float]]:
        horizonte = len(dt_series)
        if horizonte == 0:
            return {"p50": [], "p95": []}

        escenarios = [[0.0] * horizonte for _ in range(n_scenarios)]

        for t in range(horizonte):
            mu_t = dt_series[t]

            if sigma_base is not None and t < len(sigma_base):
                sigma_t = sigma_base[t]
            else:
                sigma_t = 0.1 * mu_t

            if sigma_t <= 0:
                sigma_t = max(1.0, 0.05 * mu_t)

            for w in range(n_scenarios):
                z = random.gauss(0.0, 1.0)
                if trunc_z is not None:
                    z = max(-trunc_z, min(trunc_z, z))
                d_sim = mu_t + z * sigma_t
                escenarios[w][t] = max(0.0, d_sim)

        p50 = []
        p95 = []
        for t in range(horizonte):
            values_t = sorted(escenarios[w][t] for w in range(n_scenarios))
            p50.append(self._quantile_sorted(values_t, 0.5))
            p95.append(self._quantile_sorted(values_t, 0.95))

        return {"p50": p50, "p95": p95}

    @staticmethod
    def _quantile_sorted(sorted_list: List[float], q: float) -> float:
        if not sorted_list:
            return 0.0
        n = len(sorted_list)
        pos = q * (n - 1)
        i = int(pos)
        frac = pos - i
        if i >= n - 1:
            return sorted_list[-1]
        return sorted_list[i] * (1 - frac) + sorted_list[i + 1] * frac

    # ============================================================
    # PROCESO EPSILON
    # ============================================================

    def process_epsilon(self) -> Dict[str, Any]:
        cfg = self.epsilon_input
        demanda_hist = cfg.get("demanda_historica", [])
        product_id = cfg.get("product_id", "")
        market_id = cfg.get("market_id", "")
        horizonte = cfg.get("horizonte_meses", 3)
        margin = cfg.get("margen_bruto_pct", 0.3)

        if not demanda_hist or horizonte <= 0:
            log("[EPSILON] Sin demanda histórica o horizonte inválido; se omite cálculo.")
            return {"productos": []}

        log(f"[EPSILON] Procesando Digital Twin para producto {product_id}, mercado {market_id}")

        alpha = max(0.05, min(0.95, float(margin)))
        forecast_base, sigma_base = self.simple_ses_forecast(demanda_hist, horizonte, alpha)

        series = self.compute_phi_series_for_product(product_id, market_id, horizonte)

        G = self.apply_gaussian_filter(series["phi"], forecast_base)

        psi = self.compute_psi_for_product(product_id)
        params_dt = self.adjust_params_with_psi(psi)

        forecast_dt = self.apply_dt_to_forecast(
            forecast_base=forecast_base,
            G_series=G,
            kappa=params_dt["kappa"],
            delta_max=params_dt["delta_max"]
        )

        dt_cfg = self.cfg_general.get("digital_twin", {})
        n_mc = dt_cfg.get("n_escenarios_mc", 1000)
        mc = self.montecarlo_scenarios(forecast_dt, sigma_base=sigma_base, n_scenarios=n_mc)

        nivel_servicio = dt_cfg.get("nivel_servicio_epsilon", 0.9)
        if nivel_servicio >= 0.95:
            compra_sugerida = mc["p95"]
        else:
            compra_sugerida = mc["p50"]

        return {
            "productos": [
                {
                    "product_id": product_id,
                    "market_id": market_id,
                    "horizonte_meses": horizonte,
                    "forecast_base": forecast_base,
                    "forecast_dt": forecast_dt,
                    "p50": mc["p50"],
                    "p95": mc["p95"],
                    "compra_sugerida": compra_sugerida,
                    "shock_index": series["S_p"],
                    # --- API CONTRACT ALIASES (Frontend Compatibility) ---
                    "expected": mc["p50"],            # UI: Smooth/Expected
                    "stress": mc["p95"],              # UI: Upper/Stress
                    "recommendedPurchase": compra_sugerida,
                    # -----------------------------------------------------
                    "phi_series": series["phi"],
                    "g_series": G,
                    "alpha_ses": alpha
                }
            ]
        }

    # ============================================================
    # PROCESO SIGMA
    # ============================================================

    def process_sigma(self) -> Dict[str, Any]:
        cfg = self.sigma_input

        demanda_hist = cfg.get("demanda_historica", [])
        product_id = cfg.get("product_id", "")
        market_id = cfg.get("market_id", "")
        horizonte = int(cfg.get("horizonte_meses", 3))
        periodos = int(cfg.get("periodos", 12))

        costo_unitario = cfg.get("costo_unitario", None)
        costo_pedido = cfg.get("costo_pedido", None)
        costo_mantencion_pct = cfg.get("costo_mantencion_pct", None)

        if (
            not demanda_hist
            or not product_id
            or not market_id
            or costo_unitario is None
            or costo_pedido is None
            or costo_mantencion_pct is None
        ):
            log("[SIGMA] CFG_INPUT_SIGMA incompleto o sin demanda; se omite cálculo.")
            return {"productos": []}

        if horizonte <= 0:
            horizonte = 3

        C = float(costo_unitario)
        S = float(costo_pedido)
        i = float(costo_mantencion_pct)
        H = max(1e-6, C * i)

        avg_demanda_mensual = sum(demanda_hist) / max(1, len(demanda_hist))
        D_anual_base = max(0.0, avg_demanda_mensual * periodos)

        def eoq_clasico(D_anual: float, S_: float, H_: float) -> float:
            if D_anual <= 0 or H_ <= 0:
                return 0.0
            return math.sqrt(2.0 * D_anual * S_ / H_)

        Q_base = eoq_clasico(D_anual_base, S, H)  # se mantiene por coherencia aunque no se use directo

        alpha = 0.3
        forecast_base, sigma_base = self.simple_ses_forecast(demanda_hist, horizonte, alpha)
        if not forecast_base:
            log("[SIGMA] No se pudo generar forecast base SES; se omite cálculo.")
            return {"productos": []}

        series = self.compute_phi_series_for_product(product_id, market_id, horizonte)
        G = self.apply_gaussian_filter(series["phi"], forecast_base)

        psi = self.compute_psi_for_product(product_id)
        params_dt = self.adjust_params_with_psi(psi)

        demanda_dt = self.apply_dt_to_forecast(
            forecast_base=forecast_base,
            G_series=G,
            kappa=params_dt["kappa"],
            delta_max=params_dt["delta_max"],
        )

        dt_cfg = self.cfg_general.get("digital_twin", {})
        n_mc = int(dt_cfg.get("n_escenarios_mc", 1000))
        mc = self.montecarlo_scenarios(
            dt_series=demanda_dt,
            sigma_base=sigma_base,
            n_scenarios=n_mc,
        )

        demanda_p50 = mc["p50"]
        demanda_p95 = mc["p95"]

        prod_cfg = self.get_producto_cfg(product_id)
        lt_meses = 1.0
        if prod_cfg:
            lt_meses = float(prod_cfg.get("lead_time_meses", lt_meses))
            lt_dias = prod_cfg.get("lead_time_dias", None)
            if lt_dias is not None and lt_meses == 1.0:
                try:
                    lt_meses = float(lt_dias) / 30.0
                except Exception:
                    pass
        lt_meses = max(1e-3, lt_meses)

        nivel_servicio = float(dt_cfg.get("nivel_servicio_sigma", 0.95))
        if nivel_servicio >= 0.98:
            z = 2.05
        elif nivel_servicio >= 0.95:
            z = 1.65
        elif nivel_servicio >= 0.90:
            z = 1.28
        else:
            z = 1.0

        eoq_base = []
        eoq_dt = []
        eoq_p50 = []
        eoq_p95 = []
        rop_base = []
        rop_dt = []
        rop_p50 = []
        rop_p95 = []

        for idx in range(horizonte):
            d_mes_base = max(0.0, forecast_base[idx])
            d_mes_dt = max(0.0, demanda_dt[idx])
            d_mes_p50 = max(0.0, demanda_p50[idx])
            d_mes_p95 = max(0.0, demanda_p95[idx])

            D_base = d_mes_base * periodos
            D_dt = d_mes_dt * periodos
            D_p50 = d_mes_p50 * periodos
            D_p95 = d_mes_p95 * periodos

            q_base_mes = eoq_clasico(D_base, S, H)
            q_dt_mes = eoq_clasico(D_dt, S, H)
            q_p50_mes = eoq_clasico(D_p50, S, H)
            q_p95_mes = eoq_clasico(D_p95, S, H)

            eoq_base.append(q_base_mes)
            eoq_dt.append(q_dt_mes)
            eoq_p50.append(q_p50_mes)
            eoq_p95.append(q_p95_mes)

            if sigma_base and idx < len(sigma_base):
                sigma_t = sigma_base[idx]
            elif sigma_base:
                sigma_t = sigma_base[-1]
            else:
                sigma_t = 0.0

            ss_t = max(0.0, z * sigma_t * math.sqrt(lt_meses))

            rop_base.append(d_mes_base * lt_meses + ss_t)
            rop_dt.append(d_mes_dt * lt_meses + ss_t)
            rop_p50.append(d_mes_p50 * lt_meses + ss_t)
            rop_p95.append(d_mes_p95 * lt_meses + ss_t)

        return {
            "productos": [
                {
                    "product_id": product_id,
                    "market_id": market_id,
                    "horizonte_meses": horizonte,
                    "periodos_anuales": periodos,
                    "costo_unitario": C,
                    "costo_pedido": S,
                    "costo_mantencion_pct": i,
                    "demanda_historica": demanda_hist,
                    "forecast_base": forecast_base,
                    "demanda_dt": demanda_dt,
                    "p50": demanda_p50,
                    "p95": demanda_p95,
                    "eoq_base": eoq_base,
                    "eoq_dt": eoq_dt,
                    "eoq_p50": eoq_p50,
                    "eoq_p95": eoq_p95,
                    "rop_base": rop_base,
                    "rop_dt": rop_dt,
                    "rop_p50": rop_p50,
                    "rop_p95": rop_p95,
                    "shock_index": series["S_p"],
                    "phi_series": series["phi"],
                    "g_series": G,
                    "psi": psi,
                    "params_dt": params_dt,
                    "lead_time_meses": lt_meses,
                    "nivel_servicio": nivel_servicio,
                    # --- API CONTRACT ALIASES (Frontend Compatibility) ---
                    "demandDt": demanda_dt,
                    "eoqDt": eoq_dt,
                    "ropDt": rop_dt,
                    "leadTimeMeses": lt_meses,
                    "nivelServicio": nivel_servicio,
                    # -----------------------------------------------------
                }
            ]
        }

    # ============================================================
    # KALMAN 1D + POSEIDÓN
    # (se mantiene idéntico a tu código original)
    # ============================================================

    @staticmethod
    def kalman_filter_1d(
        observations: List[float],
        Q: float = 1.0,
        R: float = 1.0,
        x0: Optional[float] = None,
        P0: float = 1.0
    ) -> List[float]:
        n = len(observations)
        if n == 0:
            return []

        x_est = [0.0] * n
        if x0 is None:
            x_est[0] = float(observations[0])
        else:
            x_est[0] = float(x0)

        P = float(P0)

        for t in range(1, n):
            x_pred = x_est[t - 1]
            P_pred = P + Q

            z = float(observations[t])
            denom = P_pred + R
            K = P_pred / denom if denom != 0 else 0.0
            x_est[t] = x_pred + K * (z - x_pred)
            P = (1.0 - K) * P_pred

        return x_est

    def process_poseidon(self) -> Dict[str, Any]:
        cfg = self.poseidon_input
        if not cfg:
            log("[POSEIDON] Input vacío; se omite cálculo.")
            return {"productos": []}

        product_id = cfg.get("product_id", "")
        market_id = cfg.get("market_id", "")
        demanda_hist = cfg.get("demanda_historica", [])
        horizonte = int(cfg.get("horizonte_meses", 6))

        # Configuración Kalman
        k_cfg = cfg.get("kalman", {})
        usar_kalman = k_cfg.get("usar_kalman", False)
        Q = float(k_cfg.get("Q", 1.0))
        R = float(k_cfg.get("R", 1.0))
        P0 = float(k_cfg.get("P0", 1.0))
        x0 = k_cfg.get("x0")
        if x0 is not None:
            x0 = float(x0)

        # Configuración PID
        p_cfg = cfg.get("pid", {})
        Kp = float(p_cfg.get("Kp", 0.5))
        Ki = float(p_cfg.get("Ki", 0.1))
        Kd = float(p_cfg.get("Kd", 0.01))

        # Configuración Tanques
        inv_t1 = float(cfg.get("inventario_inicial_tanque1", 0.0))
        inv_t2 = float(cfg.get("inventario_inicial_tanque2", 0.0))
        capacidad_max = float(cfg.get("capacidad_max_mensual", 10000.0))
        target_cobertura = float(cfg.get("cobertura_objetivo_meses", 1.0))

        # 1. Proyección de Demanda
        demanda_proyectada = []
        if not demanda_hist:
            demanda_proyectada = [0.0] * horizonte
        else:
            if usar_kalman:
                filtered = self.kalman_filter_1d(demanda_hist, Q=Q, R=R, x0=x0, P0=P0)
                last_val = filtered[-1] if filtered else 0.0
                demanda_proyectada = [max(0.0, last_val)] * horizonte
            else:
                avg = sum(demanda_hist) / len(demanda_hist)
                demanda_proyectada = [avg] * horizonte

        # 2. Simulación Sistémica (Tanques + PID)
        t1_series = []
        t2_series = []
        flujo_t1_t2_series = []
        produccion_series = []

        curr_t1 = inv_t1
        curr_t2 = inv_t2
        integral = 0.0
        prev_error = 0.0

        avg_demanda = sum(demanda_proyectada) / max(1, len(demanda_proyectada))
        target_t2 = avg_demanda * target_cobertura

        for t in range(horizonte):
            demanda_t = demanda_proyectada[t]
            venta = min(curr_t2, demanda_t)
            curr_t2 -= venta

            error = target_t2 - curr_t2
            integral += error
            derivative = error - prev_error
            prev_error = error

            signal = Kp * error + Ki * integral + Kd * derivative
            pedido_t2 = max(0.0, signal)
            flujo = min(curr_t1, pedido_t2, capacidad_max)

            curr_t1 -= flujo
            curr_t2 += flujo
            produccion = min(capacidad_max, pedido_t2)
            curr_t1 += produccion

            t1_series.append(curr_t1)
            t2_series.append(curr_t2)
            flujo_t1_t2_series.append(flujo)
            produccion_series.append(produccion)

        return {
            "productos": [
                {
                    "product_id": product_id,
                    "market_id": market_id,
                    "horizonte_meses": horizonte,
                    "demanda_proyectada": demanda_proyectada,
                    "inventario_tanque1": t1_series,
                    "inventario_tanque2": t2_series,
                    "flujo_t1_t2": flujo_t1_t2_series,
                    "produccion_sugerida": produccion_series,
                    "pid_params": {"Kp": Kp, "Ki": Ki, "Kd": Kd},
                    "kalman_params": {"Q": Q, "R": R, "x0": x0},
                    # --- API CONTRACT ALIASES (Frontend Compatibility) ---
                    "poseidonInventario1": t1_series,
                    "poseidonInventario2": t2_series,
                    "poseidonFlujo": flujo_t1_t2_series,
                    # -----------------------------------------------------
                }
            ]
        }

    # ============================================================
    # ORQUESTADOR ORIGINAL (archivo en PREDICCION)
    # ============================================================

    def run(self, context: dict | None = None) -> None:
        """
        Versión original basada en archivos ENTRADA/ y salida en PREDICCION/.
        Se mantiene para compatibilidad con el modo script.
        """
        self.load_rutas()
        self.load_cfg()
        self.load_inputs()

        assert self.rutas is not None

        epsilon_out = self.process_epsilon()
        sigma_out = self.process_sigma()
        log(f"[SIGMA] Procesando Digital Twin para producto "
            f"{self.sigma_input.get('product_id')}, mercado {self.sigma_input.get('market_id')}")
        poseidon_out = self.process_poseidon()

        salida = {
            "HELIOS_DIGITALTWIN": {
                "version": "1.0",
                "epsilon": epsilon_out,
                "sigma": sigma_out,
                "poseidon": poseidon_out,
                "metadata": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "engine": "HELIOS_DIGITALTWIN3",
                    "descripcion": "Salida unificada del Digital Twin para Epsilon, Sigma y Poseidón."
                }
            }
        }

        output_path = self.rutas.prediccion_dir / self.rutas.dt_output_file
        safe_write_json(output_path, salida)
        log(f"Archivo Digital Twin generado: {output_path}")


# ============================================================
# FACHADA PARA BACKEND / API
# ============================================================

class HeliosEngine(HeliosDigitalTwinEngine):
    """
    Clase fachada pensada para el backend OLIMPO.

    - Fija automáticamente la ruta de CFG_HELIOS_RUTAS.json en backend/cfg.
    - Carga todas las configuraciones al inicializarse.
    - Permite activar/desactivar logs.
    - Expone métodos directos para la API:
        * run_epsilon(epsilon_input)
        * run_sigma(sigma_input)
        * run_poseidon(poseidon_input)
        * run_digital_twin(epsilon_input, sigma_input, poseidon_input, write_output=False)
    """

    # Cache estático de clase para evitar leer disco en cada petición (Alto Rendimiento)
    _cache_loaded = False
    _cache_data = {}

    def __init__(self, enable_logs: bool = True) -> None:
        # Directorio backend/ (dos niveles arriba de este archivo: digital_twin/helios_engine.py)
        backend_root = Path(__file__).resolve().parents[1]
        cfg_rutas_path = backend_root / "cfg" / "CFG_HELIOS_RUTAS.json"

        # Configuramos logs globales
        global LOG_ENABLED
        LOG_ENABLED = enable_logs

        # OPTIMIZACIÓN: Si ya cargamos la config en memoria, la reutilizamos.
        # Esto permite 1000+ req/seg sin tocar el disco duro.
        if HeliosEngine._cache_loaded:
            # Restauramos referencias desde caché (RAM)
            self.cfg_rutas_path = cfg_rutas_path
            self.rutas = HeliosEngine._cache_data["rutas"]
            
            self.cfg_general = HeliosEngine._cache_data["cfg_general"]
            self.cfg_limites = HeliosEngine._cache_data["cfg_limites"]
            self.cfg_mercados = HeliosEngine._cache_data["cfg_mercados"]
            self.cfg_productos = HeliosEngine._cache_data["cfg_productos"]
            self.cfg_demanda_mercado = HeliosEngine._cache_data["cfg_demanda_mercado"]
            self.cfg_mercado_shocks = HeliosEngine._cache_data["cfg_mercado_shocks"]
            self.cfg_comex = HeliosEngine._cache_data["cfg_comex"]

            # Inicializamos inputs vacíos para esta instancia de cálculo
            self.epsilon_input = {}
            self.sigma_input = {}
            self.poseidon_input = {}
            random.seed(42)
        else:
            # Primera vez: Leemos disco (lento)
            super().__init__(cfg_rutas_path)
            self.load_rutas()
            self.load_cfg()
            
            # Guardamos en caché de clase
            HeliosEngine._cache_data = {
                "rutas": self.rutas,
                "cfg_general": self.cfg_general,
                "cfg_limites": self.cfg_limites,
                "cfg_mercados": self.cfg_mercados,
                "cfg_productos": self.cfg_productos,
                "cfg_demanda_mercado": self.cfg_demanda_mercado,
                "cfg_mercado_shocks": self.cfg_mercado_shocks,
                "cfg_comex": self.cfg_comex,
            }
            HeliosEngine._cache_loaded = True

    # -------- Métodos friendly para la API --------

    def run_epsilon(self, epsilon_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta SOLO EPSILON usando el Digital Twin, recibiendo input
        directamente desde la API (sin usar archivos ENTRADA/).
        """
        self.epsilon_input = epsilon_input
        result = self.process_epsilon()
        if "productos" in result and result["productos"]:
            return result["productos"][0]
        return {}

    def run_sigma(self, sigma_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta SOLO SIGMA usando el Digital Twin, recibiendo input
        directamente desde la API.
        """
        self.sigma_input = sigma_input
        result = self.process_sigma()
        if "productos" in result and result["productos"]:
            return result["productos"][0]
        return {}

    def run_poseidon(self, poseidon_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta SOLO POSEIDÓN usando el Digital Twin, recibiendo input
        directamente desde la API.
        """
        self.poseidon_input = poseidon_input
        result = self.process_poseidon()
        if "productos" in result and result["productos"]:
            # P1 FIX: El mapper de frontend espera anidamiento raw['poseidon']
            # Retornamos estructura { "poseidon": { ...data... } }
            data = result["productos"][0]
            return {"poseidon": data}
        return {}

    def run_digital_twin(
        self,
        epsilon_input: Optional[Dict[str, Any]] = None,
        sigma_input: Optional[Dict[str, Any]] = None,
        poseidon_input: Optional[Dict[str, Any]] = None,
        write_output: bool = False
    ) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo del Digital Twin con los tres modelos,
        usando inputs entregados por la API.

        Si write_output=True, además escribe el JSON en la carpeta PREDICCION
        según lo definido en CFG_HELIOS_RUTAS.json.
        """
        self.epsilon_input = epsilon_input if epsilon_input is not None else {}
        self.sigma_input = sigma_input if sigma_input is not None else {}
        self.poseidon_input = poseidon_input if poseidon_input is not None else {}

        epsilon_out = self.process_epsilon()
        sigma_out = self.process_sigma()
        poseidon_out = self.process_poseidon()

        salida = {
            "HELIOS_DIGITALTWIN": {
                "version": "1.0",
                "epsilon": epsilon_out,
                "sigma": sigma_out,
                "poseidon": poseidon_out,
                "metadata": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "engine": "HELIOS_BACKEND",
                    "descripcion": "Salida unificada del Digital Twin para API OLIMPO."
                }
            }
        }

        if write_output:
            assert self.rutas is not None
            output_path = self.rutas.prediccion_dir / self.rutas.dt_output_file
            safe_write_json(output_path, salida)
            log(f"Archivo Digital Twin generado: {output_path}")

        return salida


# ============================================================
# MAIN (modo script, opcional)
# ============================================================

def main() -> None:
    """
    Modo script clásico (no usado por la app):
    - Carga inputs desde ENTRADA/
    - Ejecuta el pipeline completo
    - Escribe PREDICCION/PREDICCION_DT.json
    """
    engine = HeliosEngine(enable_logs=True)
    engine.load_inputs()
    engine.run()


if __name__ == "__main__":
    main()
