from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button


class TermsScreen(Screen):

    def on_enter(self):
        self.clear_widgets()

        layout = BoxLayout(orientation="vertical", padding=20, spacing=20)

        layout.add_widget(Label(
            text="Términos y Condiciones de OLIMPO\n\n(Aquí irá el texto legal)",
            halign="left"
        ))

        btn_accept = Button(text="Acepto los términos")
        btn_accept.bind(on_press=self.accept_terms)

        layout.add_widget(btn_accept)
        self.add_widget(layout)

    def accept_terms(self, *_):
        sm = self.manager
        sm.terms_accepted = True
        sm.user_state = "plan_pending"
        sm.current = "plan"
