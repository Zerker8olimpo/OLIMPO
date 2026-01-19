# Arquitectura OS_Engine (Contrato v1.0)

**Estado:** Congelado
**Componente:** OSEngine_CORE
**Versión:** 1.0

## 1. Componentes y Fronteras

### Scanners (Observation Layer)

- **Responsabilidad:** Observación externa (API, Market, News, Web).
- **Salida:** Data cruda + métricas de calidad.
- **Restricción:** No interpretan ni deciden.

### Analysis (Deterministic Sensors)

- **Responsabilidad:** Cálculo de señales (Shock, Volatility, Trend, Phi, Psi).
- **Salida:** Resultados numéricos y flags.
- **Restricción:** No toman decisiones de negocio.

### Config Updater (Proposals)

- **Responsabilidad:** Generar propuestas de ajuste (PID, Risk, Stock).
- **Salida:** Lista de propuestas (deltas/freezes).
- **Restricción:** No escriben la configuración (CFG), solo proponen.

### Dispatchers (Adaptors)

- **Responsabilidad:** Adaptar y enviar el estado del sistema a consumidores (Alerts, DT, ML).
- **Salida:** Estado del despacho.
- **Restricción:** No interpretan la lógica de negocio.

### CORE (Kernel & Orchestrator)

- **Responsabilidad:** Convergencia única. Construye `SystemState`, `RuntimeContext`, `OSState` y `DecisionMode`.
- **Salida:** Contract estable (JSON).

---

## 2. Diagrama de Componentes

```mermaid
flowchart TB
  subgraph OBS[Observation Layer - Scanners]
    API[APIFetcher.fetch()]
    MKT[MarketScanner.scan()]
    NEWS[NewsScanner.scan()]
    WEB[WebScraper.run()]
  end

  subgraph ANA[Analysis Layer - Deterministic Sensors]
    SHOCK[ShockDetector.detect_shock()]
    VOL[VolatilityEstimator.estimate_volatility()]
    TREND[TrendAnalyzer.analyze_trend()]
    PHI[SensitivityPhi.compute_phi()]
    PSI[ImpactPsi.compute_psi()]
  end

  subgraph UPD[Config Updater - Proposals Only]
    PIDU[PIDUpdater.propose()]
    RSKU[RiskUpdater.propose()]
    STKU[StockUpdater.propose()]
  end

  subgraph DSP[Dispatchers - Adaptors]
    ALRT[AlertDispatcher.dispatch()]
    DTD[DTDispatcher.dispatch()]
    MLD[MLDispatcher.dispatch()]
  end

  subgraph KERNEL[OSEngine_CORE - Kernel & Orchestrator]
    CORE[OSEngineCore.tick()]
    STATE[SystemState Builder]
    RT[RuntimeContext Builder]
    MODE[DecisionMode Selector]
    CONTRACT[Contract Exporter]
  end

  API --> CORE
  MKT --> CORE
  NEWS --> CORE
  WEB --> CORE

  CORE --> SHOCK --> CORE
  CORE --> VOL --> CORE
  CORE --> TREND --> CORE
  CORE --> PHI --> CORE
  CORE --> PSI --> CORE

  CORE --> PIDU --> CORE
  CORE --> RSKU --> CORE
  CORE --> STKU --> CORE

  CORE --> ALRT --> CORE
  CORE --> DTD --> CORE
  CORE --> MLD --> CORE

  CORE --> CONTRACT
```

## 3. Secuencia de Ejecución (Tick)

1. **Scan:** `fetch/scan/run` (api, market, news, web) -> `external_signals`.
2. **Analysis:** Ejecución secuencial de sensores (`shock` -> `volatility` -> `trend` -> `phi` -> `psi`).
3. **Evaluate:** Determinación de `os_state` y `decision_mode`.
4. **Propose:** Generación de propuestas de configuración (`updaters`).
5. **Dispatch:** Envío de estado a `alerts`, `dt`, `ml`.
6. **Export:** Generación del JSON Contract.

---

## 4. Contrato de Salida (Contract)

El CORE exporta un objeto JSON estable con la siguiente estructura mínima:

- **context**: Identificadores y timestamp (`market_id`, `product_id`, `timestamp`).
- **os_state**: Estado operativo (`STABLE`, `WARNING`, `STRESSED`, `CRITICAL`).
- **decision_mode**: Modo de decisión (`NORMAL`, `CONSERVATIVE`, `DEFENSIVE`, `SURVIVAL`).
- **analysis_results**: Resultados crudos de sensores (`shock`, `volatility`, `trend`, `phi`, `psi`).
- **runtime_context**: Multiplicadores y guardrails efectivos aplicados en este ciclo.
- **proposals**: Lista de propuestas de actualización de configuración (puede estar vacía).
- **dispatch**: Estado de los despachadores (`alerts`, `digital_twin`, `ml`).

```

### 2. Validación de Código
El archivo `OSEngine_CORE.py` proporcionado es **correcto y definitivo** para la versión 1.0. No requiere modificaciones.

<!--
[PROMPT_SUGGESTION]Crea un test unitario para OSEngine_CORE.py que simule un ciclo tick completo con datos mockeados.[/PROMPT_SUGGESTION]
[PROMPT_SUGGESTION]Implementa un script de ejemplo que instancie OSEngineCore y ejecute un tick para verificar la integración de los módulos.[/PROMPT_SUGGESTION]
-->
```
