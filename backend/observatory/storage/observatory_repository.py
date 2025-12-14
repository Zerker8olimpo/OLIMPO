"""
Observatory Repository
----------------------

Capa de persistencia del Observatorio Estadístico de OLIMPO.

Responsabilidad única:
- Guardar eventos observacionales
- Proveer lectura básica para agregaciones

INVARIANTES:
- Side-effect único permitido del Observatorio
- Fail-open
- No lógica analítica
- No dependencia de modelos core
"""

from typing import List

from observatory.contracts.interaction_event import InteractionEvent


class ObservatoryRepository:
    """
    Repositorio simple en memoria.

    Esta implementación es intencionalmente básica y puede
    ser reemplazada por SQLite / PostgreSQL / Data Lake
    sin cambiar la interfaz.
    """

    def __init__(self):
        # Almacenamiento en memoria (append-only)
        self._events: List[InteractionEvent] = []

    # -------------------------------------------------
    # Escritura
    # -------------------------------------------------

    def save_event(self, event: InteractionEvent) -> None:
        """
        Persiste un evento observacional.
        Nunca lanza excepciones hacia arriba.
        """
        try:
            self._events.append(event)
        except Exception:
            # Fail-open: no romper el pipeline
            return

    # -------------------------------------------------
    # Lectura (para analytics)
    # -------------------------------------------------

    def get_all_events(self) -> List[InteractionEvent]:
        """
        Retorna todos los eventos almacenados.
        """
        return list(self._events)

    def clear(self) -> None:
        """
        Limpia el repositorio (solo para tests / desarrollo).
        """
        self._events.clear()
