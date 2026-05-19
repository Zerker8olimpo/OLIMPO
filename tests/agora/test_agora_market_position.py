import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from backend.database.base import Base
from backend.agora.agora_v2_service import AgoraV2Service

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.mark.anyio
async def test_market_position_calculation(db_session):
    service = AgoraV2Service()
    
    # Mocking historical data (rising trend)
    mock_history = {
        "history": [
            {"month": "2026-01", "price_median": 10000, "price_min": 9000, "price_avg": 10000, "price_max": 11000, "sample_size": 10, "volatility": 0.1, "data_status": "real_available"},
            {"month": "2026-02", "price_median": 11000, "price_min": 10000, "price_avg": 11000, "price_max": 12000, "sample_size": 10, "volatility": 0.1, "data_status": "real_available"}
        ],
        "data_status": "real_available",
        "coverage": {"history_status": "partial", "available_months": 2, "projection_quality": "low", "required_months": 6, "missing_months": 4}
    }
    
    with patch.object(service.history_service, 'get_last_6_months_history', return_value=mock_history):
        # Case 1: Below market + Healthy margin
        # Market ref: 11000. User: 9000. Cost: 5000.
        # Margin: (9000-5000)/9000 = 44% (Healthy)
        # Gap: (9000-11000)/11000 = -18% (Below)
        res = await service.get_pulse(
            market_id="m1", product_id="p1", family_id="f1", horizon=3,
            current_cost=5000, current_sale_price=9000, db=db_session
        )
        
        cp = res.commercial_position
        assert cp is not None
        assert cp.market_position_now == "below_market"
        assert cp.margin_status == "healthy"
        assert "ajustar precio al alza" in cp.recommendation.lower()
        assert cp.current_margin_pct == pytest.approx(0.444, 0.01)
        
        # Case 2: Above market + Risky margin
        # Market ref: 11000. User: 13000. Cost: 12000.
        # Margin: (13000-12000)/13000 = 7.7% (Risky)
        # Gap: (13000-11000)/11000 = 18% (Above)
        res2 = await service.get_pulse(
            market_id="m1", product_id="p1", family_id="f1", horizon=3,
            current_cost=12000, current_sale_price=13000, db=db_session
        )
        cp2 = res2.commercial_position
        assert cp2.market_position_now == "above_market"
        assert cp2.margin_status == "risky"
        assert "revisar estrategia comercial" in cp2.recommendation.lower()

@pytest.mark.anyio
async def test_plan_horizon_clipping(db_session):
    service = AgoraV2Service()
    
    # Basic plan clips 12 to 3
    res_basic = await service.get_pulse(
        market_id="m1", product_id="p1", family_id="f1", horizon=12,
        plan="basic", db=db_session
    )
    assert res_basic.projection_horizon_months == 3
    assert any("Basic" in w for w in res_basic.warnings)
    
    # Pro plan allows 12
    res_pro = await service.get_pulse(
        market_id="m1", product_id="p1", family_id="f1", horizon=12,
        plan="pro", db=db_session
    )
    assert res_pro.projection_horizon_months == 12

@pytest.mark.anyio
async def test_no_history_no_market_reference(db_session):
    service = AgoraV2Service()
    
    # Empty history
    mock_history = {
        "history": [],
        "data_status": "no_data",
        "coverage": {"history_status": "none", "available_months": 0, "projection_quality": "unavailable", "required_months": 6, "missing_months": 6}
    }
    
    with patch.object(service.history_service, 'get_last_6_months_history', return_value=mock_history):
        # Force observation to be empty too
        mock_obs = {
            "current_reference_price": 0,
            "price_min": 0, "price_median": 0, "price_avg": 0, "price_max": 0,
            "historical_trend_percent": 0, "volatility": 0, "sample_size": 0,
            "last_update": "N/A"
        }
        with patch.object(service.obs_engine, 'process', return_value=mock_obs):
            res = await service.get_pulse(
                market_id="m1", product_id="p1", family_id="f1", horizon=3,
                current_cost=5000, current_sale_price=9000, db=db_session
            )
            
            cp = res.commercial_position
            assert cp.market_reference_price is None
            assert cp.market_position_now == "unavailable"
            assert "Aún no hay referencia suficiente" in cp.recommendation

@pytest.mark.anyio
async def test_basic_plan_clipping(db_session):
    service = AgoraV2Service()
    
    mock_history = {
        "history": [
            {"month": "2026-01", "price_median": 10000, "price_min": 9000, "price_avg": 10000, "price_max": 11000, "sample_size": 10, "volatility": 0.1, "data_status": "real_available"}
        ],
        "data_status": "real_available",
        "coverage": {"history_status": "partial", "available_months": 1, "projection_quality": "low", "required_months": 6, "missing_months": 5}
    }
    
    with patch.object(service.history_service, 'get_last_6_months_history', return_value=mock_history):
        res = await service.get_pulse(
            market_id="m1", product_id="p1", family_id="f1", horizon=3,
            current_cost=8000, current_sale_price=10000, plan="basic", db=db_session
        )
        
        cp = res.commercial_position
        assert cp.market_position_now == "in_market"
        assert cp.margin_status == "tight" # (10000-8000)/10000 = 20%
        
        # Clipped fields for Basic
        assert cp.projected_market_price is None
        assert cp.market_position_projected == "unavailable"
        assert cp.commercial_risk == "unavailable"
        assert cp.price_gap_pct is None

@pytest.mark.anyio
async def test_robust_trend_calculation_6_months(db_session):
    service = AgoraV2Service()
    
    # 6 months of data with steady 5% monthly increase
    history = []
    base_price = 10000
    for i in range(6):
        price = base_price * (1.05 ** i)
        history.append({
            "month": f"2026-0{i+1}",
            "price_median": price, "price_min": price*0.9, "price_avg": price, "price_max": price*1.1,
            "sample_size": 10, "volatility": 0.05, "data_status": "real_available"
        })
    
    mock_history = {
        "history": history,
        "data_status": "real_available",
        "coverage": {"history_status": "complete", "available_months": 6, "projection_quality": "usable", "required_months": 6, "missing_months": 0}
    }
    
    with patch.object(service.history_service, 'get_last_6_months_history', return_value=mock_history):
        res = await service.get_pulse(
            market_id="m1", product_id="p1", family_id="f1", horizon=3,
            current_cost=8000, current_sale_price=10000, plan="pro", db=db_session
        )
        
        # Median variation should be 5%
        # market_trend_pct in commercial_position is trend/100
        assert res.commercial_position.market_trend_pct == pytest.approx(0.05, 0.001)
        
        # Observation result should have trend in percent
        assert res.observation.historical_trend_percent == pytest.approx(5.0, 0.1)
