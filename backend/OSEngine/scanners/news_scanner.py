from datetime import datetime
from typing import Dict, Any, List


class NewsScanner:
    """
    NewsScanner
    -----------
    Scanner de noticias.
    Captura señales narrativas crudas y declara calidad de observación.
    """

    def scan(self) -> Dict[str, Any]:
        timestamp = datetime.utcnow().isoformat()

        items: List[Dict[str, Any]] = []
        errors: List[str] = []
        missing_fields: List[str] = []

        # --------------------------------------------------
        # Aquí se incorporarán fuentes reales de noticias
        # (APIs, RSS, scraping, etc.)
        # Por ahora dejamos stub robusto
        # --------------------------------------------------
        try:
            # Ejemplo futuro:
            # items.append({
            #     "title": "...",
            #     "source": "...",
            #     "timestamp": "...",
            #     "sentiment": -0.4,
            #     "tags": ["inflation", "construction"]
            # })
            items = []
        except Exception as e:
            errors.append(str(e))

        # --------------------------------------------------
        # Métricas básicas (NO interpretación)
        # --------------------------------------------------
        sentiments = [
            item.get("sentiment", 0.0)
            for item in items
            if isinstance(item.get("sentiment"), (int, float))
        ]

        metrics = {
            "count": len(items),
            "sentiment_mean": sum(sentiments) / len(sentiments) if sentiments else 0.0,
            "sentiment_min": min(sentiments) if sentiments else 0.0,
            "sentiment_max": max(sentiments) if sentiments else 0.0
        }

        # --------------------------------------------------
        # Evaluación de calidad
        # --------------------------------------------------
        if errors:
            status = "failed"
            confidence = 0.0
        elif not items:
            status = "partial"
            confidence = 0.5
        else:
            status = "ok"
            confidence = 0.8

        return {
            "source": "news",
            "timestamp": timestamp,
            "data": {
                "items": items,
                "metrics": metrics
            },
            "quality": {
                "status": status,
                "confidence": confidence,
                "missing_fields": missing_fields,
                "errors": errors
            }
        }
