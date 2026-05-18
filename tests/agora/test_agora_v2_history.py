
import pytest
from backend.agora.agora_v2_service import AgoraV2Service
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.base import Base
from backend.database.models.agora import AgoraFamilyMonthlySnapshot
import datetime

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.mark.anyio
async def test_pulse_with_real_db_history(db_session):
    service = AgoraV2Service()
    
    market_id = "chile_construccion"
    product_id = "tubo_pvc"
    family_id = "pvc_sanitario"
    
    # 1. Insertar datos históricos en la DB
    now = datetime.datetime.now()
    for i in range(3):
        month_date = now - datetime.timedelta(days=30 * (i + 1))
        month_str = month_date.strftime("%Y-%m")
        snapshot = AgoraFamilyMonthlySnapshot(
            market_id=market_id,
            product_id=product_id,
            family_id=family_id,
            month=month_str,
            price_min=4000.0,
            price_median=4500.0 + (i * 100),
            price_avg=4550.0,
            price_max=5000.0,
            sample_size=15,
            volatility=0.05,
            data_status="real_available"
        )
        db_session.add(snapshot)
    db_session.commit()
    
    # 2. Llamar a pulse con la DB
    pulse = await service.get_pulse(
        market_id=market_id,
        product_id=product_id,
        family_id=family_id,
        horizon=6,
        db=db_session
    )
    
    # 3. Validar que history_series tiene 3 puntos (de la DB)
    assert len(pulse.history_series) == 3
    assert pulse.data_status == "real_available"
    for point in pulse.history_series:
        assert point.reference_price > 0
        assert point.data_status == "real_available"

@pytest.mark.anyio
async def test_pulse_without_history_returns_empty_list():
    service = AgoraV2Service()
    
    # Familia que no existe en DB ni tiene snapshots reales
    market_id = "non_existent"
    product_id = "non_existent"
    family_id = "non_existent"
    
    pulse = await service.get_pulse(
        market_id=market_id,
        product_id=product_id,
        family_id=family_id,
        horizon=6
    )
    
    # Debería ser fallback o sample, pero history_series vacío
    assert pulse.history_series == []
    assert "ÁGORA aún no tiene histórico suficiente" in pulse.frontend_message

@pytest.mark.anyio
async def test_pulse_never_negative_prices():
    service = AgoraV2Service()
    
    # Mocking high trend to force negative if not protected
    def mock_get_snapshot(*args, **kwargs):
        return {
            "current": {
                "price_median": 100.0,
                "price_min": 80.0,
                "price_avg": 110.0,
                "price_max": 150.0,
                "sample_size": 10,
                "volatility": 0.1,
                "historical_trend_percent": 10.0, # 1000% trend -> factor = 1 + (10 * -5 / 6) = 1 - 8.33 = -7.33
                "last_update": "2026-05-18"
            },
            "source_context": {"source_mode": "real", "real_web_observation": True}
        }
    service.get_snapshot_for_family = mock_get_snapshot
    
    pulse = await service.get_pulse("m", "p", "f", 6)
    
    for point in pulse.history_series:
        assert point.reference_price >= 0.1
        assert point.price_min >= 0.1
        assert point.price_median >= 0.1
        assert point.price_avg >= 0.1
        assert point.price_max >= 0.1
