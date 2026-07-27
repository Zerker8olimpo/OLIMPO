import pytest
from unittest.mock import AsyncMock

from backend.agora.agora_config_adapter import AgoraConfigAdapter
from backend.agora.engines.indicators_engine import IndicatorsEngine
from backend.agora.engines.market_forces_engine import MarketForcesEngine
from backend.agora.engines.projection_engine import ProjectionEngine
from backend.agora.engines.commercial_interpreter import CommercialInterpreter

INDICATORS_CFG = {
    "inflation": {"weight": 0.3, "codigo_mindicador": "ipc", "sensitivity_direction": "presiona_alza"},
    "exchange_rate": {"weight": 0.4, "codigo_mindicador": "dolar", "sensitivity_direction": "presiona_alza"},
    "logistics": {"weight": 0.3, "codigo_mindicador": None, "sensitivity_direction": "presiona_alza"},
}


def _fake_client(results):
    client = AsyncMock()
    client.get_indicators.return_value = results
    return client


# ---------------------------------------------------------------------------
# IndicatorsEngine
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_indicators_engine_computes_economic_pressure_score():
    client = _fake_client({
        "ipc": {"status": "ok", "variacion_6m": 0.02},
        "dolar": {"status": "ok", "variacion_6m": 0.05},
    })
    engine = IndicatorsEngine(client=client)

    result = await engine.process({}, INDICATORS_CFG)

    assert result["inflation"]["impact"] in ("bajo", "medio", "alto")
    assert result["exchange_rate"]["direction"] == "presiona_alza"
    assert result["logistics"]["impact"] == "sin_dato_real"

    expected_E = 0.3 * 0.02 * 1.0 + 0.4 * 0.05 * 1.0
    assert result["economic_pressure_index"]["variation_6m"] == pytest.approx(round(expected_E, 4))
    assert result["economic_pressure_index"]["direction"] == "presiona_alza"


@pytest.mark.anyio
async def test_indicators_engine_marks_failed_fetch_as_sin_dato_real_and_excludes_from_score():
    client = _fake_client({
        "ipc": {"status": "error", "error": "timeout"},
        "dolar": {"status": "ok", "variacion_6m": 0.05},
    })
    engine = IndicatorsEngine(client=client)

    result = await engine.process({}, INDICATORS_CFG)

    assert result["inflation"]["impact"] == "sin_dato_real"
    expected_E = 0.4 * 0.05 * 1.0
    assert result["economic_pressure_index"]["variation_6m"] == pytest.approx(round(expected_E, 4))


@pytest.mark.anyio
async def test_indicators_engine_no_cfg_returns_neutral_pressure_index():
    engine = IndicatorsEngine(client=_fake_client({}))

    result = await engine.process({}, {})

    assert result == {
        "economic_pressure_index": {"variation_6m": 0.0, "impact": "bajo", "direction": "estable"}
    }


# ---------------------------------------------------------------------------
# MarketForcesEngine
# ---------------------------------------------------------------------------

def test_market_forces_without_cfg_falls_back_to_snapshot_and_is_honest():
    engine = MarketForcesEngine()

    result = engine.process({"market_forces": {"supply": "desconocida", "demand": "desconocida"}}, {}, {})

    assert result["supply"] == "desconocida"
    assert result["demand"] == "desconocida"
    assert result["supply_demand_pressure"]["status"] == "sin_datos_suficientes"
    assert result["supply_demand_pressure"]["score"] is None
    assert result["substitutes_pressure"]["status"] == "sin_datos_suficientes"


def test_market_forces_with_baseline_cfg_still_reports_sin_datos_suficientes():
    engine = MarketForcesEngine()
    supply_demand_cfg = {"supply_pressure_baseline": "neutral", "demand_pressure_baseline": "media"}
    substitutes_cfg = {"substitutes": [{"substitute_id": "hdpe_sanitario"}]}

    result = engine.process({}, supply_demand_cfg, substitutes_cfg)

    assert result["supply"] == "neutral"
    assert result["demand"] == "media"
    assert result["substitutes"] == "hdpe_sanitario"
    # Baseline configurado no es telemetría real: sigue sin score fabricado.
    assert result["supply_demand_pressure"]["status"] == "sin_datos_suficientes"
    assert result["supply_demand_pressure"]["score"] is None
    assert result["substitutes_pressure"]["items"] == substitutes_cfg["substitutes"]


# ---------------------------------------------------------------------------
# ProjectionEngine
# ---------------------------------------------------------------------------

RULES = {
    "default": {
        "confidence_base": 0.8,
        "risk_factor_base": 0.05,
        "cap_adjustment": 0.25,
        "indicator_weight": 0.3,
        "target_sample_size": 15,
        "reference_history_months": 6,
    },
    "horizons": {"6": {"lambda_h": 1.0, "risk_multiplier": 1.0}},
}


def test_projection_returns_zero_confidence_without_current_price():
    engine = ProjectionEngine()
    result = engine.process({"current_reference_price": None}, RULES, 6)
    assert result["confidence"] == 0.0
    assert result["base"] is None


def test_projection_weights_economic_pressure_index_into_adjustment():
    engine = ProjectionEngine()
    observation = {"current_reference_price": 1000.0, "historical_trend_percent": 0.0, "sample_size": 15}
    indicators_result = {"economic_pressure_index": {"variation_6m": 0.05}}

    result = engine.process(observation, RULES, 6, indicators_result=indicators_result, history_months=6)

    expected_base = 1000.0 * (1 + 0.3 * 0.05)
    assert result["base"] == pytest.approx(round(expected_base, 2))


def test_projection_confidence_uses_sample_size_and_history_months():
    engine = ProjectionEngine()
    observation = {"current_reference_price": 1000.0, "historical_trend_percent": 0.0, "sample_size": 15}

    full_confidence = engine.process(observation, RULES, 6, history_months=6)["confidence"]
    partial_confidence = engine.process({**observation, "sample_size": 0}, RULES, 6, history_months=0)["confidence"]

    assert full_confidence > partial_confidence


def test_projection_confidence_falls_back_to_cn_when_history_months_unknown():
    engine = ProjectionEngine()
    observation = {"current_reference_price": 1000.0, "historical_trend_percent": 0.0, "sample_size": 15}

    result = engine.process(observation, RULES, 6, history_months=None)

    assert result["confidence"] > 0.1


# ---------------------------------------------------------------------------
# CommercialInterpreter
# ---------------------------------------------------------------------------

COMMERCIAL_RULES = AgoraConfigAdapter().get_commercial_rules()


def test_commercial_interpreter_no_market_price():
    interpreter = CommercialInterpreter()
    result = interpreter.process({"current_reference_price": None}, {"user_price": 100}, COMMERCIAL_RULES)
    assert result["market_position"] == "mercado_sin_datos_suficientes"


def test_commercial_interpreter_no_user_price():
    interpreter = CommercialInterpreter()
    result = interpreter.process({"current_reference_price": 1000.0}, {"user_price": None}, COMMERCIAL_RULES)
    assert result["market_position"] == "sin_precio_usuario"


@pytest.mark.parametrize("user_price,expected_position", [
    (850.0, "precio_usuario_muy_bajo_mercado"),
    (920.0, "precio_usuario_levemente_bajo_mercado"),
    (1000.0, "precio_usuario_alineado_mercado"),
    (1050.0, "precio_usuario_levemente_sobre_mercado"),
    (1200.0, "precio_usuario_muy_sobre_mercado"),
])
def test_commercial_interpreter_matches_config_driven_thresholds(user_price, expected_position):
    interpreter = CommercialInterpreter()
    result = interpreter.process(
        {"current_reference_price": 1000.0},
        {"user_price": user_price, "enabled": True},
        COMMERCIAL_RULES,
    )
    assert result["market_position"] == expected_position


FORBIDDEN_PHRASES = [
    "debes subir tu precio",
    "compra ahora",
    "precio exacto",
    "el mercado garantiza",
]


def test_commercial_interpretation_messages_respect_section_18_tone_rules():
    for signal in COMMERCIAL_RULES.get("signals", {}).values():
        message = signal.get("message", "").lower()
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in message
