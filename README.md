# OLIMPO — Backend Analítico, Digital Twin y Observatorio Estadístico

OLIMPO es una **plataforma analítica avanzada para Supply Chain, Inventarios y Operaciones**, diseñada para **apoyar la toma de decisiones humanas bajo incertidumbre** mediante modelos matemáticos, control, simulación y Digital Twin.

Este repositorio contiene la **arquitectura completa del backend**, desarrollada en **Python + FastAPI**, estructurada bajo principios de **separación estricta de responsabilidades, no‑interferencia decisional y auditabilidad**.

---

## 🎯 Propósito del Backend

El backend de OLIMPO tiene como objetivo:

- Exponer modelos analíticos avanzados vía API.
- Orquestar señales de mercado y simulación sistémica.
- Ejecutar Digital Twin para contraste de escenarios.
- Registrar evidencia estadística **sin modificar decisiones ni modelos**.
- Servir como base para app móvil, dashboards y futuras integraciones ERP/BI.

OLIMPO **no automatiza decisiones**: entrega escenarios, rangos y contexto para que el decisor conserve el control.

---

## 🧠 Modelos Analíticos Incluidos

- **EPSILON**
  Forecast SES + Control PID + sensibilidad a shocks (φ, Φ, Ψ).

- **SIGMA**
  EOQ dinámico + ROP + simulación Monte Carlo + control de riesgo.

- **POSEIDÓN**
  Modelo de doble tanque + filtro de Kalman + estabilidad sistémica.

- **HELIOS**
  Motor central de **Digital Twin**, que simula el comportamiento del sistema bajo distintos escenarios de mercado, demanda y shocks.

---

## 📐 Arquitectura General del Backend

```
backend/
│
├── api/                      # Capa de exposición (FastAPI)
│   ├── main.py               # App principal
│   ├── routers/              # Endpoints por modelo
│   │   ├── epsilon.py
│   │   ├── sigma.py
│   │   ├── poseidon.py
│   │   └── helios.py
│   └── utils/                # Schemas Pydantic
│       ├── epsilon_schema.py
│       ├── sigma_schema.py
│       ├── poseidon_schema.py
│       └── helios_schema.py
│
├── models/                   # Modelos analíticos (intocables)
│   ├── epsilon/
│   │   └── EPSILON_SERVICE.py
│   ├── sigma/
│   │   └── SIGMA_SERVICE.py
│   ├── poseidon/
│   │   └── POSEIDON_SERVICE.py
│   └── helios/
│       └── HELIOS_SERVICE.py
│
├── digital_twin/             # Digital Twin
│   ├── helios_engine.py      # Motor HELIOS
│   └── __init__.py
│
├── OSEngine/                 # Motor de señales (φ, ψ, Φ)
│   └── OSEngine_CORE.py
│
├── observatory/              # Observatorio Estadístico (side‑channel)
│   ├── contracts/            # Schemas de eventos
│   ├── collectors/           # Construcción y validación de eventos
│   ├── risk/                 # Cálculo de riesgo implícito
│   ├── twin/                 # Contraste vs HELIOS (read‑only)
│   ├── analytics/            # Estadística descriptiva e inferencial
│   ├── storage/              # Persistencia y agregados
│   ├── services/             # Fachada del Observatorio
│   └── cfg/                  # Configuración propia
│
├── cfg/                      # Configuración del sistema
│   ├── CFG_HELIOS_*.json
│   ├── CFG_INPUT_*.json
│   └── CFG_OLIMPO_ML.json
│
├── ENTRADA/                  # Modo script / pruebas offline
├── tests/                    # Tests unitarios e integración
└── docs/                     # Documentación arquitectónica
```

---

## 🧩 Observatorio Estadístico (Fail‑Safe)

El Observatorio Estadístico es un **módulo independiente**, diseñado bajo el principio arquitectónico oficial:

> _Observa, registra y contextualiza. Nunca decide, corrige ni optimiza._

Características clave:

- Post‑ejecución (no bloqueante).
- Read‑only sobre resultados.
- No acoplado a modelos, HELIOS ni OLIMPO Core.
- Registra patrones decisionales, errores, riesgo implícito y tendencias.
- Usa estadística descriptiva, inferencial no paramétrica y análisis longitudinal.

📄 Principio formal: `docs/architecture/observatory_principle.md`

---

## 🧠 Flujo Conceptual del Sistema

```
Usuario
  ↓
API / App
  ↓
OSEngine (señales)
  ↓
Modelos (EPSILON / SIGMA / POSEIDÓN)
  ↓
HELIOS Digital Twin
  ↓
Resultado al usuario
  ↓
Observatorio Estadístico (side‑channel)
```

---

## 🚀 Ejecución en local

### 1. Crear entorno virtual

```bash
python -m venv venv
```

### 2. Activar entorno

```bash
# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Levantar servidor

```bash
uvicorn api.main:app --reload
```

Servidor disponible en: `http://127.0.0.1:8000`

---

## 🛡️ Principios no negociables

- Separación estricta de responsabilidades.
- Modelos analíticos **intocables**.
- Digital Twin como testigo, no actor.
- Observatorio sin feedback ni control.
- Decisión siempre humana.

---

## 📌 Estado del proyecto

- Backend operativo y versionado.
- Arquitectura definida y documentada.
- Observatorio Estadístico integrado como capa silenciosa.
- Preparado para app móvil y escalamiento.

---

## ✨ Filosofía OLIMPO

> _No se trata de predecir el futuro, sino de entender el riesgo antes de decidir._
