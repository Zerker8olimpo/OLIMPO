# ÁGORA V2 — Formato CSV Canónico Universal

Para facilitar la ingesta masiva y segura de precios, ÁGORA utiliza un formato CSV canónico universal.

## Estructura del CSV

El archivo debe contener las siguientes columnas (basadas en `CanonicalPriceObservation`):

| Columna | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `market_id` | ID canónico del mercado | `mercado_frutas_frescas` |
| `product_id` | ID canónico del producto | `naranjas_frescas` |
| `family_id` | ID canónico de la familia | `naranjas_frescas_nacional` |
| `observed_at` | Fecha de observación (ISO 8601) | `2026-05-18T12:00:00Z` |
| `price` | Precio unitario original | `1200` |
| `currency` | Moneda | `CLP` |
| `unit` | Unidad original | `kg` |
| `normalized_price`| Precio normalizado (unidad base) | `1200` |
| `source_id` | ID de la fuente | `odepa_mayoristas` |
| `source_name` | Nombre de la fuente | `ODEPA Mayoristas` |
| `is_real` | Booleano (datos reales vs muestra) | `true` |

## Preparación de Datos

Se debe utilizar el script `backend/scripts/agora_prepare_price_csv.py` para transformar datos crudos a este formato.

```bash
python backend/scripts/agora_prepare_price_csv.py \
  --source odepa_mayoristas \
  --input raw_data.csv \
  --output ready_data.csv \
  --market-id mercado_frutas_frescas \
  --product-id naranjas_frescas \
  --family-id naranjas_frescas_nacional
```
