from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button


class BaseScreen(Screen):
    title = "BASE"

    def build_layout(self, next_screen=None, back_screen=None):
        layout = BoxLayout(orientation="vertical", padding=20, spacing=20)

        layout.add_widget(Label(text=self.title, font_size=24))

        if next_screen:
            layout.add_widget(
                Button(
                    text="Continuar",
                    on_press=lambda *_: self.go(next_screen)
                )
            )

        if back_screen:
            layout.add_widget(
                Button(
                    text="Volver",
                    on_press=lambda *_: self.go(back_screen)
                )
            )

        return layout

    def go(self, screen_name):
        self.manager.current = screen_name
