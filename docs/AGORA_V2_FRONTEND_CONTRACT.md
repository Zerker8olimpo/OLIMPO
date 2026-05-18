# ÁGORA V2 — Frontend Contract (Flutter/Web)

## 1. Introducción
ÁGORA V2 es la versión canónica de la capa de observación de mercado de OLIMPO. Utiliza una jerarquía estricta de `mercado → producto → familia`.

## 2. Flujo Recomendado para UI
1.  **Cargar Mercados:** `GET /agora/v2/markets`
2.  **Filtrar Productos:** `GET /agora/v2/products?market_id={id}`
3.  **Filtrar Familias:** `GET /agora/v2/families?market_id={id}&product_id={id}`
4.  **Obtener Pulso:** `GET /agora/v2/pulse?market_id={id}&product_id={id}&family_id={id}&horizon={3|6|12}`

## 3. Estrategia de IDs (Safe IDs)
Muchos IDs canónicos contienen tildes. Para evitar errores de encoding en las URLs, el backend expone un campo `safe_id`.
**Regla:** Flutter DEBE usar `safe_id` (o los campos `safe_market_id`, `safe_product_id`, `safe_family_id`) para realizar las peticiones HTTP.

## 4. Estados de Datos (`data_status`)
Cada familia y respuesta de pulso incluye un estado que la UI debe interpretar:

- `real_available`: Datos provenientes de observaciones reales autorizadas. Mostrar con confianza alta.
- `sample_available`: Datos de muestra controlada. Mostrar con aviso de "Referencial".
- `fallback_available`: Datos genéricos de respaldo. Mostrar con advertencia clara.
- `no_data`: No hay datos para esta familia.

## 5. Manejo de Advertencias
La respuesta de `/pulse` incluye:
- `warnings`: Lista de strings técnicos/operativos.
- `frontend_message`: Mensaje amigable para el usuario final (ej: "Valores referenciales").

## 6. Ejemplo de Respuesta de Pulso (Resumida)
```json
{
  "module": "AGORA",
  "api_version": "v2",
  "market_id": "mercado_sanitario_hidraulico",
  "safe_market_id": "mercado_sanitario_hidraulico",
  "data_status": "sample_available",
  "snapshot_status": "sample_snapshot",
  "frontend_message": "ÁGORA aún no tiene suficientes observaciones reales para esta familia. Los valores mostrados son referenciales.",
  "observation": {
    "current_reference_price": 4390,
    "last_update": "2026-05-17"
  },
  "source_context": {
    "source_mode": "sample",
    "real_web_observation": false,
    "message": "..."
  }
}
```

## 7. Errores Comunes
El backend devuelve objetos de error con códigos estandarizados:
- `MARKET_NOT_FOUND`
- `PRODUCT_NOT_FOUND`
- `FAMILY_NOT_FOUND`
- `INVALID_HORIZON`
