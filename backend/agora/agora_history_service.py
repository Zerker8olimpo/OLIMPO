from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from sqlalchemy.exc import OperationalError
from backend.database.models.agora import AgoraFamilyMonthlySnapshot
from datetime import datetime, timedelta

class AgoraHistoryService:
    def get_last_6_months_history(
        self,
        db: Session,
        market_id: str,
        product_id: str,
        family_id: str
    ) -> Dict[str, Any]:
        """
        TAREA 4: Servicio lector de histórico real.
        Busca los últimos 6 meses de snapshots para una familia en la base de datos.
        """
        # Calcular los meses de interés (últimos 6 meses aproximados para búsqueda)
        now = datetime.now()
        target_months = []
        for i in range(7): # Buscamos hasta 7 por si el actual está incompleto
            # Restamos meses de forma simple para el filtro IN
            year = now.year
            month = now.month - i
            while month <= 0:
                month += 12
                year -= 1
            target_months.append(f"{year}-{month:02d}")
        
        stmt = select(AgoraFamilyMonthlySnapshot).where(
            AgoraFamilyMonthlySnapshot.market_id == market_id,
            AgoraFamilyMonthlySnapshot.product_id == product_id,
            AgoraFamilyMonthlySnapshot.family_id == family_id,
            AgoraFamilyMonthlySnapshot.month.in_(target_months)
        ).order_by(desc(AgoraFamilyMonthlySnapshot.month)).limit(6)
        
        try:
            results = db.execute(stmt).scalars().all()
        except OperationalError:
            # TAREA 2: Si la tabla no existe (transición o tests sin migración), 
            # devolvemos no_data de forma controlada.
            return {
                "history": [],
                "data_status": "no_data",
                "snapshot_status": "missing_history",
                "source_context": {
                    "historical_window_available": False, 
                    "historical_backfill_months": 0,
                    "message": "ÁGORA aún no tiene histórico suficiente para esta familia."
                }
            }
        
        if not results:
            return {
                "history": [],
                "data_status": "no_data",
                "snapshot_status": "missing_history",
                "source_context": {
                    "historical_window_available": False, 
                    "historical_backfill_months": 0,
                    "message": "ÁGORA aún no tiene histórico suficiente para esta familia."
                }
            }
            
        history_points = []
        for r in results:
            # TAREA 1: Nunca permitir precios <= 0
            if r.price_median <= 0:
                continue
                
            history_points.append({
                "month": r.month,
                "price_min": max(0.1, r.price_min),
                "price_median": max(0.1, r.price_median),
                "price_avg": max(0.1, r.price_avg),
                "price_max": max(0.1, r.price_max),
                "sample_size": r.sample_size,
                "volatility": r.volatility,
                "data_status": r.data_status,
                "source_context": r.source_context
            })
            
        # Ordenar por fecha ascendente para la serie del frontend
        history_points.sort(key=lambda x: x["month"])
            
        return {
            "history": history_points,
            "data_status": results[0].data_status, # El más reciente manda
            "snapshot_status": "real_snapshot" if results[0].data_status == "real_available" else "sample_snapshot",
            "source_context": {
                "historical_window_available": len(history_points) > 0,
                "historical_backfill_months": len(history_points),
                "message": "Histórico real recuperado." if results[0].data_status == "real_available" else "Histórico referencial recuperado."
            }
        }
