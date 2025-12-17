from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label


class HubScreen(Screen):

    def on_enter(self):
        self.clear_widgets()

        layout = BoxLayout(
            orientation="vertical",
            padding=20,
            spacing=15
        )

        layout.add_widget(Label(
            text="Panel de Modelos OLIMPO",
            size_hint_y=None,
            height=40
        ))

        plan ="enterprise"

        # EPSILON – siempre disponible
        btn_eps = Button(
            text="ε · Previsión de Demanda",
            size_hint_y=None,
            height=48
        )
        btn_eps.bind(
            on_press=lambda *_: setattr(self.manager, "current", "epsilon")
        )
        layout.add_widget(btn_eps)

        # SIGMA – PRO / ENTERPRISE
        btn_sig = Button(
            text="Σ · Gestión de Inventarios",
            size_hint_y=None,
            height=48
        )
        if plan in ("pro", "enterprise"):
            btn_sig.bind(
                on_press=lambda *_: setattr(self.manager, "current", "sigma")
            )
        else:
            btn_sig.disabled = True
        layout.add_widget(btn_sig)

        # POSEIDÓN – solo ENTERPRISE
        btn_pos = Button(
            text="Π · Gestión de Producción",
            size_hint_y=None,
            height=48
        )
        if plan == "enterprise":
            btn_pos.bind(
                on_press=lambda *_: setattr(self.manager, "current", "poseidon")
            )
        else:
            btn_pos.disabled = True
        layout.add_widget(btn_pos)

        self.add_widget(layout)