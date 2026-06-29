# ÁGORA V2 — Matriz de Fuentes de Precios (Chile)

Este documento define la estrategia de captura de precios para los 18 mercados de ÁGORA, priorizando fuentes públicas, APIs oficiales y datos abiertos fidedignos.

## Estrategia de Selección

1. **ODEPA Mayoristas/Consumidor**: Referencia primaria para el sector agroalimentario (frutas, verduras, carnes, lácteos).
2. **CNE (Comisión Nacional de Energía)**: API oficial para combustibles y energía.
3. **ChileCompra / Mercado Público**: Referencia para precios transados en B2B institucional (construcción, salud, equipos).
4. **INE (Instituto Nacional de Estadísticas)**: Índices de Precios Productor (IPP) para materiales de construcción e industria.
5. **SERNAC Observatorio**: Precios de consumo masivo y retail supermercado.
6. **Banco Central / CMF**: Indicadores macroeconómicos y financieros (UF, Dólar, IPC).
7. **Aduanas / COMEX**: Referencias de importación para bienes transables.
8. **Mercado Libre API**: Referencia de marketplace para retail, ferretería y repuestos.

---

## Mapeo por Mercado

| Mercado ID | Fuente Primaria | Tipo de Precio | Confiabilidad |
| :--- | :--- | :--- | :--- |
| `mercado_frutas_hortalizas` | ODEPA Mayoristas | Mayorista Real | Alta |
| `mercado_carnicos_lacteos` | ODEPA Consumidor | Retail Consumo | Alta |
| `mercado_agro_insumos` | ODEPA Insumos | Precio Productor | Media/Alta |
| `mercado_combustibles_energia` | CNE API | Tarifa Regulada | Alta |
| `mercado_construccion_ferreteria` | ChileCompra / INE IPP | Transacción / Índice | Alta |
| `mercado_consumo_masivo` | SERNAC / ODEPA | Retail Consumo | Media/Alta |
| `mercado_salud_farmacia` | CENABAST / ChileCompra | Transacción | Alta |
| `mercado_financiero` | Banco Central / BDE | Índice | Alta |
| `mercado_repuestos_automotriz` | Mercado Libre API | Marketplace | Media |

---

## Gobernanza de Datos

* **is_real**: Solo se marca como `true` si proviene de una observación trazable (no sample, no fallback).
* **source_context**: Debe incluir metadatos de la fuente original (URL, fecha de captura, ID de registro).
* **Frecuencia**: La mayoría de las fuentes públicas se actualizan diaria o mensualmente.
* **Normalización**: Todas las fuentes pasan por el `PriceNormalizer` para asegurar unidades comparables.
