# screens/auth.py

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button

from ui.colors import WHITE, BLACK, YELLOW


class AuthScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(
            orientation="vertical",
            padding=40,
            spacing=20
        )

        title = Label(
            text="OLIMPO",
            font_size=32,
            color=BLACK
        )

        subtitle = Label(
            text="Plataforma de decisión logística",
            font_size=14,
            color=BLACK
        )

        email = TextInput(
            hint_text="Correo electrónico",
            multiline=False
        )

        password = TextInput(
            hint_text="Contraseña",
            multiline=False,
            password=True
        )

        btn = Button(
            text="Ingresar",
            background_color=YELLOW,
            color=BLACK,
            size_hint_y=None,
            height=48
        )

        btn.bind(on_press=self.login)

        layout.add_widget(title)
        layout.add_widget(subtitle)
        layout.add_widget(email)
        layout.add_widget(password)
        layout.add_widget(btn)

        self.add_widget(layout)

    def login(self, instance):
        # Placeholder: luego va autenticación real
        self.manager.current = "hub"
