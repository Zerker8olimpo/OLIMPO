# ÁGORA Historical Bootstrap Strategy

## Context
Market price history is not always available via public APIs for a 6-month window (e.g., Mercado Libre). To provide a robust experience similar to price comparison tools (like Knasta), ÁGORA must build and maintain its own historical database.

## Principles
1. **Proprietary Data**: ÁGORA accumulates its own observations to build history.
2. **Bootstrap Support**: Allow initial history load via CSV/Manual Import to jumpstart families.
3. **Continuous Capture**: Monthly snapshots consolidate daily/weekly observations.
4. **No Inventions**: If data is missing for a month, it's reported as missing. We do not invent prices.
5. **Coverage-Based Projections**: Projections are only considered "Usable" if at least 6 months of historical data are available.

## History Coverage Levels
- **None**: 0 months. Projections unavailable.
- **Partial**: 1-5 months. Projections low/medium quality.
- **Complete**: 6+ months. Projections usable/robust.

## Implementation Steps
1. **Import CSV**: Enhanced to support `observed_at` to backfill history.
2. **Snapshots**: Improved to include percentiles (P25, P75) and dispersion metrics.
3. **Pulse API**: Reflects `history_status` and `projection_quality` based on available months.
