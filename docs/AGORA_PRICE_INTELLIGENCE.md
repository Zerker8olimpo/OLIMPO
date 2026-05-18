# AGORA Price Intelligence

ÁGORA Price Intelligence es el motor de captura y análisis de precios reales de mercado de OLIMPO. 
Permite que el sistema pase de usar datos de muestra (referenciales) a datos observados mes a mes.

## 1. Funcionamiento General

1. **Observaciones:** Se capturan precios individuales desde diversas fuentes (CSV, Scrapers futuros, APIs).
2. **Normalización:** Los nombres crudos de productos se mapean a familias canónicas de OLIMPO usando el `PriceNormalizer`.
3. **Snapshots:** Periódicamente (ej: fin de mes), se consolidan las observaciones en la tabla `agora_family_monthly_snapshots`, calculando mínimos, medianas y volatilidad.
4. **Pulse:** El endpoint de usuario final consume los snapshots reales para mostrar tendencias y proyecciones basadas en datos verídicos.

## 2. Seguridad Administrativa

Los endpoints de administración de ÁGORA están protegidos por el header `X-AGORA-ADMIN-TOKEN`. 
Este token debe estar configurado en el servidor mediante la variable de entorno `AGORA_ADMIN_TOKEN`.

## 3. Carga de Precios (CSV)

La carga manual se realiza mediante un archivo CSV. Existe una plantilla oficial en `docs/agora_price_observations_template.csv`.

### Columnas del CSV:
- `market_id`: ID del mercado (ej: `mercado_sanitario_hidraulico`).
- `product_id`: ID del producto.
- `family_id`: ID de la familia (opcional, si está vacío el normalizador intentará derivarlo).
- `source`: Nombre de la fuente (ej: `sodimac_chile`).
- `source_type`: Tipo de fuente (`manual`, `web`, `api`).
- `raw_product_name`: Nombre tal cual aparece en la fuente.
- `normalized_product_name`: Nombre limpio.
- `price`: Valor numérico positivo.
- `currency`: CLP por defecto.
- `observed_at`: Fecha de la observación (YYYY-MM-DD).

### Comandos Operativos

#### Crear tablas (idempotente):
```bash
python backend/scripts/create_agora_history_tables.py
```

#### Ingestar CSV:
```bash
python backend/scripts/ingest_agora_prices_csv.py --file ruta/al/archivo.csv
```

#### Construir Snapshots:
```bash
python backend/scripts/build_agora_snapshots.py --month 2026-05
```

## 4. Interpretación de `data_status`

- `real_available`: Existen 3 o más observaciones reales en el mes. Los datos son confiables.
- `sample_available`: Existen 1 o 2 observaciones reales. Se muestran pero se advierte que la muestra es pequeña.
- `no_data`: No existen mediciones reales. El sistema no inventa precios y muestra proyecciones macroeconómicas generales.

## 5. Observador Mercado Libre Chile

ÁGORA cuenta con un observador automático que utiliza la API de Mercado Libre Chile para obtener precios de mercado actualizados.

### Configuración
Opcionalmente, se puede configurar un token de acceso para aumentar los límites de la API:
- Variable de entorno: `MERCADO_LIBRE_ACCESS_TOKEN`

### Ejecución por Endpoint Admin
Se pueden disparar observaciones mediante POST (requiere `X-AGORA-ADMIN-TOKEN`):
- `/agora/v2/admin/observe-family`: Observa una familia específica.
- `/agora/v2/admin/observe-market`: Observa múltiples familias de un mercado (con límite).

### Ejecución por Script
```bash
python backend/scripts/run_agora_price_observer.py --market-id mercado_sanitario_hidraulico --product-id tuberias_y_fittings_cobre_soldable --family-id tuberias_y_fittings_cobre_soldable_codos_cobre_soldable --build-snapshot
```

### Lógica de Filtrado y Calidad
1. **Query Building:** Genera hasta 5 términos de búsqueda optimizados.
2. **Matching:** Evalúa títulos contra términos requeridos e incluidos. Score mínimo: 0.70.
3. **Packs:** Detecta automáticamente packs (x10, unidades) y calcula el precio unitario.
4. **Outliers:** Elimina precios que se desvían drásticamente de la mediana (ej: <0.25x o >4x).

## 6. Próximas Etapas
