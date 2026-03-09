import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from backend.observatory.services.observatory_service import ObservatoryService
from backend.observatory.storage.observatory_repository import ObservatoryRepository
from backend.observatory.contracts.trend_snapshot import TrendSnapshot

class TestObservatoryFlow:
    """
    Tests de integración para verificar el flujo completo de ObservatoryService.
    Cubre: Extracción de datos -> Cálculo (Risk/Trend) -> Persistencia.
    """

    @pytest.fixture
    def mock_repo(self):
        return MagicMock(spec=ObservatoryRepository)

    @pytest.fixture
    def service(self, mock_repo):
        return ObservatoryService(
            cfg_quality={},
            cfg_risk={},
            repository=mock_repo,
            enabled=True
        )

    def test_observe_execution_calculates_and_stores_trend(self, service, mock_repo):
        """
        Verifica que una ejecución con valores numéricos genera y persiste un TrendSnapshot.
        """
        # 1. Arrange
        context = {
            "gmail": "test_user@example.com",
            "device_id": "device_001",
            "app_version": "1.0.0",
            "platform": "web",
            "timestamp": datetime.now(timezone.utc)
        }
        
        # Serie con tendencia clara UP
        inputs = {
            "values": [10.0, 12.0, 14.0, 16.0, 18.0], 
            "other_param": "ignored"
        }
        
        outputs = {"result": "ok"}
        model_name = "TEST_MODEL"

        # 2. Act
        service.observe_execution(context, inputs, outputs, model_name)

        # 3. Assert
        # Verificar que se llamó a store_trend_snapshot
        assert mock_repo.store_trend_snapshot.called
        
        # Capturar el argumento
        args, _ = mock_repo.store_trend_snapshot.call_args
        snapshot = args[0]
        
        # Validar integridad del snapshot
        assert isinstance(snapshot, TrendSnapshot)
        assert snapshot.account_id == "test_user@example.com"
        assert snapshot.trend_direction == "UP"
        assert snapshot.slope > 0
        assert snapshot.confidence == 1.0 # window = len(values) -> confidence = 1.0
        assert snapshot.observation_window == 5

    def test_observe_execution_handles_empty_values(self, service, mock_repo):
        """
        Verifica comportamiento cuando no hay 'values' en inputs.
        """
        context = {"gmail": "user"}
        inputs = {"param": 1} # Sin 'values'
        
        service.observe_execution(context, inputs, {}, "TEST")
        
        assert mock_repo.store_trend_snapshot.called
        args, _ = mock_repo.store_trend_snapshot.call_args
        snapshot = args[0]
        
        # Debe ser STABLE por defecto con confianza 0
        assert snapshot.trend_direction == "STABLE"
        assert snapshot.confidence == 0.0

    def test_fail_open_on_repo_error(self, service, mock_repo):
        """
        Verifica que el servicio no explota si el repositorio falla.
        """
        mock_repo.store_trend_snapshot.side_effect = Exception("DB Connection Failed")
        
        try:
            service.observe_execution({"gmail": "u"}, {"values": [1, 2]}, {}, "TEST")
        except Exception:
            pytest.fail("ObservatoryService debe ser fail-open y capturar excepciones del repo")
            
        # Confirmamos que intentó guardar a pesar del error
        assert mock_repo.store_trend_snapshot.called