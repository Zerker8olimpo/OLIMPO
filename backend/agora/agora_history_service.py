from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError
from backend.database.models.agora import AgoraFamilyMonthlySnapshot
from backend.agora.id_normalization_service import IdNormalizationService
from datetime import datetime, timedelta

class AgoraHistoryService:
    def check_agora_history_storage(self, db: Session) -> Dict[str, bool]:
        """
        TAREA 4: Validación de almacenamiento ÁGORA.
        Verifica si las tablas necesarias existen en la base de datos.
        """
        try:
            inspector = inspect(db.get_bind())
            tables = inspector.get_table_names()
            return {
                "tables_exist": "agora_price_observations" in tables and "agora_family_monthly_snapshots" in tables,
                "observations_table": "agora_price_observations" in tables,
                "snapshots_table": "agora_family_monthly_snapshots" in tables
            }
        except Exception:
            return {
                "tables_exist": False,
                "observations_table": False,
                "snapshots_table": False
            }

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
        # Normalizar IDs a safe para búsqueda en DB
        s_market_id = IdNormalizationService.build_safe_id(market_id)
        s_product_id = IdNormalizationService.build_safe_id(product_id)
        s_family_id = IdNormalizationService.build_safe_id(family_id)

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
            AgoraFamilyMonthlySnapshot.market_id == s_market_id,
            AgoraFamilyMonthlySnapshot.product_id == s_product_id,
            AgoraFamilyMonthlySnapshot.family_id == s_family_id,
            AgoraFamilyMonthlySnapshot.month.in_(target_months)
        ).order_by(desc(AgoraFamilyMonthlySnapshot.month)).limit(6)
        
        try:
            results = db.execute(stmt).scalars().all()
        except (OperationalError, ProgrammingError):
            # TAREA 1: Capturar tanto error de SQLite como de PostgreSQL (UndefinedTable)
            # para evitar 500 en producción si la tabla no existe aún.
            return {
                "history": [],
                "data_status": "no_data",
                "snapshot_status": "missing_history",
                "coverage": {
                    "required_months": 6,
                    "available_months": 0,
                    "missing_months": 6,
                    "history_status": "none",
                    "projection_quality": "unavailable"
                },
                "source_context": {
                    "historical_window_available": False, 
                    "historical_backfill_months": 0,
                    "message": "ÁGORA aún no tiene histórico suficiente para esta familia."
                },
                "warnings": ["Histórico real aún no inicializado en base de datos."]
            }
        
        if not results:
            return {
                "history": [],
                "data_status": "no_data",
                "snapshot_status": "missing_history",
                "coverage": {
                    "required_months": 6,
                    "available_months": 0,
                    "missing_months": 6,
                    "history_status": "none",
                    "projection_quality": "unavailable"
                },
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

        # TAREA 5: Calcular cobertura histórica
        available_months = len(history_points)
        required_months = 6
        missing_months = max(0, required_months - available_months)

        history_status = "none"
        if available_months >= required_months:
            history_status = "complete"
        elif available_months > 0:
            history_status = "partial"

        projection_quality = "unavailable"
        if history_status == "complete":
            projection_quality = "usable"
        elif available_months >= 3:
            projection_quality = "medium"
        elif available_months > 0:
            projection_quality = "low"

        return {
            "history": history_series if (history_series := history_points) else [],
            "data_status": results[0].data_status if results else "no_data",
            "snapshot_status": ("real_snapshot" if results[0].data_status == "real_available" else "sample_snapshot") if results else "missing_history",
            "coverage": {
                "required_months": required_months,
                "available_months": available_months,
                "missing_months": missing_months,
                "history_status": history_status,
                "projection_quality": projection_quality
            },
            "source_context": {
                "historical_window_available": available_months > 0,
                "historical_backfill_months": available_months,
                "message": "Histórico real recuperado." if (results and results[0].data_status == "real_available") else "Histórico insuficiente para una proyección robusta."
            }
        }

