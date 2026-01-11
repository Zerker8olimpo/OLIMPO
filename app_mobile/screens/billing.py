from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from datetime import date, timedelta


class BillingScreen(Screen):

    def on_enter(self):
        self.clear_widgets()

        layout = BoxLayout(orientation="vertical", padding=20, spacing=20)

        layout.add_widget(Label(
            text="Tu plan ha vencido.\nDebes renovar para continuar."
        ))

        btn_pay = Button(text="Renovar plan")
        btn_pay.bind(on_press=self.pay)

        layout.add_widget(btn_pay)
        self.add_widget(layout)

    def pay(self, *_):
        sm = self.manager
        sm.next_billing_date = date.today() + timedelta(days=30)
        sm.user_state = "active"
        sm.current = "hub"
