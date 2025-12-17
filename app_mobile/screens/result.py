from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button


class ResultScreen(Screen):

    def on_enter(self):
        self.clear_widgets()

        sm = self.manager
        model = getattr(sm, "last_model", "N/A")
        payload = getattr(sm, "last_payload", {})

        layout = BoxLayout(orientation="vertical", padding=20, spacing=10)

        layout.add_widget(Label(text=f"Resultado modelo: {model.upper()}"))

        layout.add_widget(Label(
            text="Payload utilizado:\n" + str(payload),
            size_hint_y=None
        ))

        btn = Button(text="Volver al panel")
        btn.bind(on_press=lambda *_: setattr(self.manager, "current", "hub"))

        layout.add_widget(btn)
        self.add_widget(layout)