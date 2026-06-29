import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone, timedelta
import os
import csv
import tempfile

from backend.database.base import Base
import backend.database.models
from backend.agora.price_intelligence.manual_ingestion import ManualIngestionService
from backend.agora.price_intelligence.snapshot_builder import SnapshotBuilder
from backend.agora.agora_history_service import AgoraHistoryService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_import_csv_historical_success(db_session):
    service = ManualIngestionService()
    
    # Crear CSV temporal
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp:
        writer = csv.writer(tmp)
        writer.writerow(["market_id", "product_id", "family_id", "source_id", "raw_product_name", "price", "currency", "observed_at"])
        writer.writerow(["m1", "p1", "f1", "src1", "Item 1", "1000", "CLP", "2026-01-01"])
        writer.writerow(["m1", "p1", "f1", "src1", "Item 2", "1100", "CLP", "2026-01-05"])
        tmp_path = tmp.name

    try:
        res = service.ingest_price_observations_csv(db_session, tmp_path)
        assert res["inserted"] == 2
        
        # Verificar en DB
        from backend.database.models.agora import AgoraPriceObservation
        obs = db_session.query(AgoraPriceObservation).all()
        assert len(obs) == 2
        assert obs[0].observed_at.year == 2026
        assert obs[0].observed_at.month == 1
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_import_csv_rejects_invalid(db_session):
    service = ManualIngestionService()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp:
        writer = csv.writer(tmp)
        writer.writerow(["market_id", "product_id", "family_id", "source_id", "raw_product_name", "price", "currency", "observed_at"])
        writer.writerow(["m1", "p1", "f1", "src1", "Bad Price", "-100", "CLP", "2026-01-01"])
        writer.writerow(["m1", "p1", "f1", "fallback", "Fallback Data", "1000", "CLP", "2026-01-01"])
        writer.writerow(["m1", "p1", "f1", "src1", "No Date", "1000", "CLP", ""])
        tmp_path = tmp.name

    try:
        res = service.ingest_price_observations_csv(db_session, tmp_path)
        assert res["inserted"] == 0
        assert res["skipped"] == 3
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_snapshot_builder_statistics(db_session):
    from backend.database.models.agora import AgoraPriceObservation
    
    # Insertar observaciones: 15 para calidad 'high'
    prices = [1000 + i*100 for i in range(15)]
    for p in prices:
        obs = AgoraPriceObservation(
            market_id="m1", product_id="p1", family_id="f1",
            observed_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
            source="src1", source_type="test", raw_product_name="item",
            normalized_product_name="item", price=p, currency="CLP",
            confidence=1.0, is_real=True, unit="unidad"
        )
        db_session.add(obs)
    db_session.commit()
    
    builder = SnapshotBuilder()
    snap = builder.build_monthly_snapshot(db_session, "m1", "p1", "f1", "2026-01")
    
    assert snap is not None
    assert snap.price_min == 1000
    assert snap.price_max == 2400
    assert snap.data_quality == "high" # since size is 15

def test_history_coverage_calculation(db_session):
    from backend.database.models.agora import AgoraFamilyMonthlySnapshot
    
    history_service = AgoraHistoryService()
    
    # Caso 1: Sin datos
    res_none = history_service.get_last_6_months_history(db_session, "m1", "p1", "f1")
    assert res_none["coverage"]["history_status"] == "none"
    assert res_none["coverage"]["projection_quality"] == "unavailable"
    
    # Caso 2: Parcial (2 meses)
    for m in ["2026-01", "2026-02"]:
        snap = AgoraFamilyMonthlySnapshot(
            market_id="m1", product_id="p1", family_id="f1",
            month=m, price_min=100, price_median=110, price_avg=110, price_max=120,
            sample_size=5, volatility=0.1, data_status="real_available"
        )
        db_session.add(snap)
    db_session.commit()
    
    # Mock current month to be 2026-02 or later
    with patch("backend.agora.agora_history_service.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 3, 1)
        res_partial = history_service.get_last_6_months_history(db_session, "m1", "p1", "f1")
        assert res_partial["coverage"]["history_status"] == "partial"
        assert res_partial["coverage"]["available_months"] == 2
        assert res_partial["coverage"]["projection_quality"] == "low"

    # Caso 3: Completo (6 meses)
    for m in ["2025-09", "2025-10", "2025-11", "2025-12"]:
        snap = AgoraFamilyMonthlySnapshot(
            market_id="m1", product_id="p1", family_id="f1",
            month=m, price_min=100, price_median=110, price_avg=110, price_max=120,
            sample_size=5, volatility=0.1, data_status="real_available"
        )
        db_session.add(snap)
    db_session.commit()

    with patch("backend.agora.agora_history_service.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 3, 1)
        res_complete = history_service.get_last_6_months_history(db_session, "m1", "p1", "f1")
        assert res_complete["coverage"]["history_status"] == "complete"
        assert res_complete["coverage"]["available_months"] == 6
        assert res_complete["coverage"]["projection_quality"] == "usable"
