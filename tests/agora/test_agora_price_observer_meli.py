
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from backend.database.base import Base
import backend.database.models
from backend.agora.price_intelligence.price_observer import PriceObserver
from backend.agora.price_intelligence.query_builder import QueryBuilder
from backend.agora.price_intelligence.product_matcher import ProductMatcher
from backend.agora.price_intelligence.price_normalizer import PriceNormalizer
from backend.agora.price_intelligence.outlier_filter import OutlierFilter

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_query_builder_logic():
    builder = QueryBuilder()
    family_cfg = {
        "frontend_label": "Codo Cobre 1/2",
        "family_nombre": "codos cobre soldable",
        "required_terms": ["cobre", "codo"],
        "attributes_for_matching": ["diametro"]
    }
    queries = builder.build_family_queries("m", "p", "f", family_cfg)
    assert "codo cobre 1/2" in queries
    assert "cobre codo" in queries
    assert any("diametro" in q for q in queries)
    assert len(queries) <= 5

def test_product_matcher_logic():
    matcher = ProductMatcher()
    family_cfg = {
        "required_terms": ["cobre", "codo"],
        "exclude_terms": ["pvc", "plastico"],
        "include_terms": ["soldable"]
    }
    
    # 1. Match perfecto
    item_ok = {"title": "Codo de cobre soldable 1/2 pulgada"}
    res_ok = matcher.match_item_to_family(item_ok, family_cfg)
    assert res_ok["accepted"] is True
    assert res_ok["score"] >= 0.7
    
    # 2. Match rechazado por exclude
    item_bad = {"title": "Codo de cobre y pvc mixto"}
    res_bad = matcher.match_item_to_family(item_bad, family_cfg)
    assert res_bad["accepted"] is False
    
    # 3. Match rechazado por falta de required
    item_missing = {"title": "Tubo de cobre 1/2"}
    res_missing = matcher.match_item_to_family(item_missing, family_cfg)
    assert res_missing["accepted"] is False

def test_price_normalizer_pack_detection():
    normalizer = PriceNormalizer()
    item = {"title": "Pack x10 Codos Cobre", "price": 10000, "currency": "CLP"}
    res = normalizer.normalize_item_price_unit(item, {})
    assert res["unit"] == "pack_10"
    assert res["normalized_unit_price"] == 1000.0

def test_outlier_filter_logic():
    filter = OutlierFilter()
    obs = [
        {"normalized_unit_price": 1000},
        {"normalized_unit_price": 1100},
        {"normalized_unit_price": 1050},
        {"normalized_unit_price": 5000}, # Outlier alto (5x mediana aprox)
        {"normalized_unit_price": 100}   # Outlier bajo (0.1x mediana)
    ]
    filtered = filter.filter_price_outliers(obs)
    prices = [f["normalized_unit_price"] for f in filtered]
    assert 5000 not in prices
    assert 100 not in prices
    assert 1000 in prices

@pytest.mark.anyio
async def test_price_observer_orchestration(db_session):
    observer = PriceObserver()
    
    # Mocking Mercado Libre Client
    mock_items = [
        {
            "id": "MLC1", "title": "Codo Cobre 1/2", "price": 1500, "currency_id": "CLP", 
            "permalink": "http://test1", "seller": {"id": 123}, "condition": "new"
        },
        {
            "id": "MLC2", "title": "Codo Cobre 3/4", "price": 1800, "currency_id": "CLP", 
            "permalink": "http://test2", "seller": {"id": 123}, "condition": "new"
        }
    ]
    
    with patch.object(observer.meli_client, 'search_items', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            {
                "source": "mercado_libre_mlc", "source_type": "api", "source_item_id": "MLC1",
                "title": "Codo Cobre 1/2", "price": 1500, "currency": "CLP", "url": "http://test1"
            }
        ]
        
        # Mocking catalog config
        with patch.object(observer.catalog, 'get_family') as mock_cfg:
            mock_cfg.return_value = {
                "family_id": "f1", "family_nombre": "codo cobre", 
                "required_terms": ["cobre", "codo"], "include_terms": [], "exclude_terms": []
            }
            
            result = await observer.observe_family_prices(db_session, "m", "p", "f1")
            
            # El query builder genera varias queries, por cada una el mock devuelve items.
            assert result["inserted"] >= 1
            assert result["raw_count"] > 0
            assert result["snapshot_built"] is True
            assert result["data_status"] in ["real_available", "sample_available", "fallback_available"]
