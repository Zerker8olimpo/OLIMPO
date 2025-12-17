from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.clock import Clock


class ProcessingScreen(Screen):

    def on_enter(self):
        self.clear_widgets()
        self.add_widget(Label(text="Procesando escenario...\nEspere unos segundos"))

        # Simulación de procesamiento
        Clock.schedule_once(self.finish_processing, 1.2)

    def finish_processing(self, *_):
        sm = self.manager

        if hasattr(sm, "epsilon_payload"):
            sm.last_model = "epsilon"
            sm.last_payload = sm.epsilon_payload

        elif hasattr(sm, "sigma_payload"):
            sm.last_model = "sigma"
            sm.last_payload = sm.sigma_payload

        elif hasattr(sm, "poseidon_payload"):
            sm.last_model = "poseidon"
            sm.last_payload = sm.poseidon_payload

        else:
            sm.last_model = "unknown"
            sm.last_payload = {}

        self.manager.current = "result"