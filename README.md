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
