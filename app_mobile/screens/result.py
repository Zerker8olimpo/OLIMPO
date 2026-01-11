# screens/processing.py

from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.clock import Clock

from core.errors import OlimpoError


class ProcessingScreen(Screen):

    def on_enter(self):
        self.clear_widgets()
        self.add_widget(Label(text="Procesando escenario...\nConectando con OLIMPO"))

        # Ejecutar backend en el siguiente frame
        Clock.schedule_once(self.run_backend, 0.2)

    def run_backend(self, *_):
        sm = self.manager

        # Detectar modelo
        if sm.epsilon_payload:
            sm.last_model = "epsilon"
            sm.last_payload = sm.epsilon_payload

        elif sm.sigma_payload:
            sm.last_model = "sigma"
            sm.last_payload = sm.sigma_payload

        elif sm.poseidon_payload:
            sm.last_model = "poseidon"
            sm.last_payload = sm.poseidon_payload

        else:
            sm.last_model = "unknown"
            sm.last_payload = {}

        try:
            response = sm.http.post(
                f"/simulate/{sm.last_model}",
                sm.last_payload
            )

            sm.last_result = response
            sm.current = "result"

        except OlimpoError as e:
            sm.last_result = {
                "error": str(e),
                "model": sm.last_model
            }
            sm.current = "result"
