from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label


class PlanScreen(Screen):

    def set_plan(self, plan_name):
        self.manager.plan = plan_name
        print("PLAN SETEADO:", plan_name)
        self.manager.current = "hub"

    def on_enter(self):
        self.clear_widgets()

        layout = BoxLayout(orientation="vertical", padding=20, spacing=15)

        layout.add_widget(Label(
            text="Selecciona tu plan",
            size_hint_y=None,
            height=40
        ))

        btn_basic = Button(text="Básico", size_hint_y=None, height=48)
        btn_basic.bind(on_press=lambda *_: self.set_plan("basic"))

        btn_pro = Button(text="Profesional", size_hint_y=None, height=48)
        btn_pro.bind(on_press=lambda *_: self.set_plan("pro"))

        btn_ent = Button(text="Enterprise", size_hint_y=None, height=48)
        btn_ent.bind(on_press=lambda *_: self.set_plan("enterprise"))

        layout.add_widget(btn_basic)
        layout.add_widget(btn_pro)
        layout.add_widget(btn_ent)

        self.add_widget(layout)
