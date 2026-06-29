# ÁGORA V2 — Adaptadores de Fuentes de Precios

Este documento describe la arquitectura de los adaptadores utilizados para conectar ÁGORA con diversas fuentes de precios.

## Arquitectura

Cada fuente de datos tiene un adaptador dedicado que hereda de `PriceSourceAdapter`. La responsabilidad del adaptador es:

1. **Load**: Cargar los datos crudos (CSV, JSON, API).
2. **Normalize**: Mapear los campos crudos a un formato intermedio común.
3. **To Canonical**: Transformar el registro normalizado al formato `CanonicalPriceObservation`.

## Adaptadores Implementados (Skeletons)

* `OdepaAdapter`: Para frutas, hortalizas e insumos.
* `ChileCompraAdapter`: Para precios de licitaciones y compras públicas.
* `CneAdapter`: Para precios de energía y combustibles.
* `IneAdapter`: Para índices de precios productor (IPP).
* `SernacAdapter`: Para precios de retail y consumo masivo.

## Flujo de Trabajo

Para agregar una nueva fuente:
1. Crear el archivo `backend/agora/price_intelligence/source_adapters/nuevo_adapter.py`.
2. Implementar los métodos `load`, `normalize` y `to_canonical`.
3. Registrar la fuente en `backend/agora/price_intelligence/source_registry.py`.
4. Actualizar la matriz en `backend/agora/price_intelligence/source_matrix.json`.
