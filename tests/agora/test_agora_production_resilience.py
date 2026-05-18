
import pytest
from unittest.mock import MagicMock
from sqlalchemy.exc import ProgrammingError
from backend.agora.agora_v2_service import AgoraV2Service

@pytest.mark.anyio
async def test_pulse_resilience_when_table_missing():
    """
    TAREA 5: Validar que si la tabla no existe en DB, pulse no devuelve 500.
    Simulamos ProgrammingError (UndefinedTable en Postgres).
    """
    service = AgoraV2Service()
    
    # Mock de la DB que lanza ProgrammingError (UndefinedTable)
    mock_db = MagicMock()
    mock_db.execute.side_effect = ProgrammingError("SELECT...", params={}, orig=Exception("relation 'agora_family_monthly_snapshots' does not exist"))
    
    # Intentar obtener pulse
    market_id = "chile_construccion"
    product_id = "tubo_pvc"
    family_id = "pvc_sanitario"
    
    # No debe lanzar excepción
    pulse = await service.get_pulse(
        market_id=market_id,
        product_id=product_id,
        family_id=family_id,
        horizon=6,
        db=mock_db
    )
    
    # Validaciones
    assert pulse.history_series == []
    assert pulse.source_context.historical_window_available is False
    assert any("Histórico real aún no inicializado" in w for w in pulse.warnings)
    # Projection está vacía si no hay precio de referencia
    assert len(pulse.projection_series) == 0

@pytest.mark.anyio
async def test_history_storage_health_check():
    """
    TAREA 4: Validar el reporte de salud del almacenamiento.
    """
    service = AgoraV2Service()
    mock_db = MagicMock()
    
    # Mock del inspector
    mock_inspector = MagicMock()
    mock_inspector.get_table_names.return_value = ["users", "subscriptions"] # No están las de ÁGORA
    
    from unittest.mock import patch
    with patch("backend.agora.agora_history_service.inspect", return_value=mock_inspector):
        health = service.history_service.check_agora_history_storage(mock_db)
        assert health["tables_exist"] is False
        assert health["observations_table"] is False
        assert health["snapshots_table"] is False

    # Ahora simulamos que existen
    mock_inspector.get_table_names.return_value = ["agora_price_observations", "agora_family_monthly_snapshots"]
    with patch("backend.agora.agora_history_service.inspect", return_value=mock_inspector):
        health = service.history_service.check_agora_history_storage(mock_db)
        assert health["tables_exist"] is True
        assert health["observations_table"] is True
        assert health["snapshots_table"] is True
