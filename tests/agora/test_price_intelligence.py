import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.base import Base

from backend.agora.price_intelligence.price_observation_service import PriceObservationService
from backend.agora.price_intelligence.price_normalizer import PriceNormalizer
from backend.agora.price_intelligence.snapshot_builder import SnapshotBuilder
from backend.database.models.agora import AgoraPriceObservation, AgoraFamilyMonthlySnapshot
from backend.agora.agora_v2_service import AgoraV2Service

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_save_price_observation_rejects_negative(db_session):
    service = PriceObservationService()
    obs = service.save_price_observation(
        db_session, "m", "p", "f", "test_source", "web", "raw", "norm", -100
    )
    assert obs is None
    
    obs2 = service.save_price_observation(
        db_session, "m", "p", "f", "test_source", "web", "raw", "norm", 0
    )
    assert obs2 is None

def test_save_price_observation_saves_real(db_session):
    service = PriceObservationService()
    obs = service.save_price_observation(
        db_session, "m", "p", "f", "test_source", "web", "raw", "norm", 1500, is_sample=False
    )
    assert obs is not None
    assert obs.price == 1500
    assert obs.is_real is True
    
    # Intentar duplicado el mismo día
    obs_dup = service.save_price_observation(
        db_session, "m", "p", "f", "test_source", "web", "raw", "norm", 1500, is_sample=False
    )
    assert obs.id == obs_dup.id

def test_price_normalizer_assigns_correct_family():
    normalizer = PriceNormalizer()
    # Mocking the catalog behavior for test
    def mock_resolve_market(m): return m
    def mock_resolve_product(m, p): return p
    def mock_list_families(m, p):
        return [
            {
                "family_id": "tubo_pvc_sanitario",
                "required_terms": ["pvc", "sanitario"],
                "include_terms": ["tubo"],
                "exclude_terms": ["codo"]
            },
            {
                "family_id": "codo_pvc_sanitario",
                "required_terms": ["codo", "pvc", "sanitario"],
                "include_terms": [],
                "exclude_terms": ["tubo"]
            }
        ]
    normalizer.catalog.resolve_market_id = mock_resolve_market
    normalizer.catalog.resolve_product_id = mock_resolve_product
    normalizer.catalog.list_families_by_product = mock_list_families
    
    fam, conf, reason = normalizer.normalize_price_item("Tubo de PVC Sanitario 110mm", "m", "p")
    assert fam == "tubo_pvc_sanitario"
    assert conf > 0.4
    
    fam2, conf2, reason2 = normalizer.normalize_price_item("Codo PVC sanitario", "m", "p")
    assert fam2 == "codo_pvc_sanitario"
    assert conf2 > 0.4

def test_snapshot_builder_calculates_stats(db_session):
    obs_service = PriceObservationService()
    builder = SnapshotBuilder()
    
    # Insertar observaciones
    prices = [1000, 1500, 2000, 2500]
    for p in prices:
        obs_service.save_price_observation(
            db_session, "m", "p", "f", "src", "web", "raw", "norm", p
        )
        
    now = datetime.now(timezone.utc)
    month_str = f"{now.year}-{now.month:02d}"
    
    snap = builder.build_monthly_snapshot(db_session, "m", "p", "f", month_str)
    assert snap is not None
    assert snap.price_min == 1000
    assert snap.price_max == 2500
    assert snap.price_avg == 1750
    assert snap.price_median == 1750  # 1500+2000 / 2
    assert snap.sample_size == 4
    assert snap.data_status == "real_available"

@pytest.mark.anyio
async def test_pulse_does_not_invent_prices_without_observation(db_session):
    service = AgoraV2Service()
    # Pedir familia inexistente, no debe fallar pero debe traer current_reference_price = None
    pulse = await service.get_pulse("m_test", "p_test", "f_test", 6, db=db_session)
    assert pulse.observation.current_reference_price is None
    assert pulse.data_status == "no_data"
    assert pulse.history_series == []
    
@pytest.mark.anyio
async def test_pulse_does_not_return_same_base_price_for_different_families(db_session):
    service = AgoraV2Service()
    pulse1 = await service.get_pulse("m", "p", "f1", 6, db=db_session)
    pulse2 = await service.get_pulse("m", "p", "f2", 6, db=db_session)
    
    assert pulse1.observation.current_reference_price is None
    assert pulse2.observation.current_reference_price is None
    # Ya no devuelven 4390
