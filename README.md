# OLIMPO — Ecosistema de Modelos Analíticos y Digital Twin para Supply Chain

OLIMPO es una plataforma analítica compuesta por modelos avanzados de predicción, optimización, simulación y Digital Twin, diseñada para apoyar la toma de decisiones en logística, inventarios y operaciones.

Este repositorio contiene la **arquitectura backend** desarrollada en **Python + FastAPI**, incluyendo los modelos:

- **EPSILON** — Forecast SES + PID + Digital Twin (φ, Φ, Ψ)
- **SIGMA** — EOQ + ROP + Montecarlo + Digital Twin
- **POSEIDÓN** — Doble tanque + Kalman + Digital Twin
- **HELIOS** — Motor central Digital Twin que integra todos los modelos

La API expone endpoints limpios para consumo desde una **app móvil**, dashboards o sistemas externos (ERP, BI, etc.).

---

## 📐 Arquitectura General del Backend

backend/
│
├── api/
│ ├── main.py → FastAPI principal
│ ├── routers/ → Endpoints expuestos
│ │ ├── epsilon.py
│ │ ├── sigma.py
│ │ ├── poseidon.py
│ │ └── helios.py
│ └── utils/ → Esquemas Pydantic
│ ├── epsilon_schema.py
│ ├── sigma_schema.py
│ ├── poseidon_schema.py
│ └── helios_schema.py
│
├── models/
│ ├── epsilon/
│ │ └── EPSILON_SERVICE.py
│ ├── sigma/
│ │ └── SIGMA_SERVICE.py
│ ├── poseidon/
│ │ └── POSEIDON_SERVICE.py
│ └── helios/
│ └── HELIOS_SERVICE.py
│
├── digital_twin/
│ ├── helios_engine.py → Motor completo HELIOS Digital Twin
│ └── init.py
│
├── cfg/ → Archivos de configuración del Digital Twin
│ ├── CFG_HELIOS_RUTAS.json
│ ├── CFG_HELIOS_GENERAL.json
│ ├── CFG_HELIOS_PRODUCTOS.json
│ ├── CFG_HELIOS_MERCADOS.json
│ ├── CFG_HELIOS_PIPELINE.json
│ ├── CFG_MERCADO_SHOCKS.json
│ ├── CFG_DEMANDA_MERCADO.json
│ ├── CFG_LIMITES_SUP_INF.json
│ ├── CFG_HELIOS_COMEX.json
│ ├── CFG_OLIMPO_ML.json
│ ├── CFG_INPUT_EPSILON.json
│ ├── CFG_INPUT_SIGMA.json
│ └── CFG_INPUT_POSEIDON.json
│
└── ENTRADA/ → Modo script (no usado en API)

## 🚀 Cómo ejecutar el backend en local

### 1. Crear entorno virtual

```bash
python -m venv venv
```
