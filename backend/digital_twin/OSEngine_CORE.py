"""
OSEngine_CORE.py
Motor de Señales y Percepción Externa para OLIMPO.

Función:
1. Escanea fuentes externas (Simulado: Noticias, APIs financieras).
2. Detecta Shocks de Mercado (Phi) y Cambios de Perfil Humano (Psi).
3. Genera 'Parches de Inteligencia' y los escribe en CFG_PATCHES.json.
4. Helios Engine lee estos parches y adapta la simulación en tiempo real.
"""

import sys
import json
import random
from pathlib import Path
from datetime import datetime, timezone

# Configuración de rutas
current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent
cfg_dir = backend_dir / "cfg"
patches_file = cfg_dir / "CFG_PATCHES.json"

def run_os_engine():
    print(f"[OSEngine] Iniciando escaneo de señales: {datetime.now(timezone.utc)}")
    
    patches = []
    
    # ============================================================
    # 1. DETECTOR DE SHOCKS (Simulación)
    # ============================================================
    # Simulamos que leemos noticias financieras y detectamos volatilidad
    market_volatility = random.uniform(0.0, 1.0)
    
    if market_volatility > 0.7:
        print(f"[OSEngine] ⚠️ ALERTA: Alta volatilidad detectada ({market_volatility:.2f})")
        print("[OSEngine] -> Generando parche de shock para Mercado Sanitario.")
        
        # Creamos un parche que aumenta la magnitud del shock en la configuración
        # Ruta: CFG_MERCADO_SHOCKS.json -> cfg_MERCADO_SHOCKS -> shocks_por_mercado -> [0] -> shock_magnitud_promedio
        patch = {
            "cfg_file": "CFG_MERCADO_SHOCKS.json",
            "parameter_path": "cfg_MERCADO_SHOCKS.shocks_por_mercado.0.shock_magnitud_promedio",
            "new_value": 0.6,  # Aumentamos el impacto del shock
            "context": {"reason": "High Volatility Detected", "source": "NewsScraper"}
        }
        patches.append(patch)
    else:
        print("[OSEngine] Mercado estable. Sin intervenciones.")

    # ============================================================
    # 2. PUBLICACIÓN DE INTELIGENCIA
    # ============================================================
    data = {
        "version": "1.0",
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "OSEngine_CORE"
        },
        "patches": patches
    }
    
    with open(patches_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
        
    print(f"[OSEngine] Inteligencia actualizada en {patches_file}")

if __name__ == "__main__":
    run_os_engine()