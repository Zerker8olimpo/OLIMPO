# screens/auth.py

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button

from core.auth_client import login_google
from core.errors import OlimpoError
from ui.colors import BLACK, YELLOW


class AuthScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.layout = BoxLayout(
            orientation="vertical",
            padding=40,
            spacing=20
        )

        self.title = Label(
            text="OLIMPO",
            font_size=32,
            color=BLACK
        )

        self.subtitle = Label(
            text="Autenticación (Google Token)",
            font_size=14,
            color=BLACK
        )

        self.token_input = TextInput(
            hint_text="Pega aquí el Google ID Token",
            multiline=False
        )

        self.status = Label(
            text="",
            color=BLACK
        )

        btn = Button(
            text="Ingresar",
            background_color=YELLOW,
            color=BLACK,
            size_hint_y=None,
            height=48
        )
        btn.bind(on_press=self.login)

        self.layout.add_widget(self.title)
        self.layout.add_widget(self.subtitle)
        self.layout.add_widget(self.token_input)
        self.layout.add_widget(btn)
        self.layout.add_widget(self.status)

        self.add_widget(self.layout)

    def login(self, *_):
        sm = self.manager
        app = self.manager.app if hasattr(self.manager, "app") else None

        google_token = self.token_input.text.strip()

        if not google_token:
            self.status.text = "Debe ingresar un Google Token"
            return

        try:
            jwt = login_google(sm.http, google_token)
            sm.jwt = jwt
            self.status.text = "Autenticado correctamente"

            # Routing central
            App = self.manager.parent
            app = self.manager.parent if hasattr(self.manager, "parent") else None
            if app and hasattr(app, "route_user"):
                app.route_user()
            else:
                sm.current = "hub"

        except OlimpoError as e:
            self.status.text = str(e)
