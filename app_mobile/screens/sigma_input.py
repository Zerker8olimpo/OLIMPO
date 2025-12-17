from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch


class SigmaInputScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.demanda_inputs = []

        root = BoxLayout(orientation="vertical", padding=20, spacing=10)
        root.add_widget(Label(text="Σ  Gestión de Inventarios", font_size=18))

        self.spinner_mercado = Spinner(text="Mercado", values=("Sanitario", "Industrial", "Construcción"))
        self.spinner_producto = Spinner(text="Producto", values=("Producto A", "Producto B", "Producto C"))

        root.add_widget(self.spinner_mercado)
        root.add_widget(self.spinner_producto)

        self.spinner_horizonte = Spinner(text="6", values=("6", "12"))
        self.spinner_horizonte.bind(text=self.build_demanda_inputs)
        root.add_widget(self.spinner_horizonte)

        self.scroll = ScrollView()
        self.grid = GridLayout(cols=2, spacing=10, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.scroll.add_widget(self.grid)
        root.add_widget(self.scroll)

        for label, attr in [
            ("Costo unitario", "input_costo_unitario"),
            ("Costo por pedido", "input_costo_pedido"),
            ("Costo mantención (%)", "input_costo_mantencion")
        ]:
            root.add_widget(Label(text=label, size_hint_y=None, height=30))
            ti = TextInput(
                input_filter="float",
                size_hint_y=None,
                height=40
            )
            setattr(self, attr, ti)
            root.add_widget(ti)

        twin = BoxLayout(size_hint_y=None, height=40)
        twin.add_widget(Label(text="Activar Digital Twin"))
        self.switch_twin = Switch(active=True)
        twin.add_widget(self.switch_twin)
        root.add_widget(twin)

        btn = Button(text="Evaluar escenario", size_hint_y=None, height=45)
        btn.bind(on_press=self.submit)
        root.add_widget(btn)

        self.add_widget(root)
        self.build_demanda_inputs(self.spinner_horizonte, self.spinner_horizonte.text)

    def build_demanda_inputs(self, _, value):
        self.grid.clear_widgets()
        self.demanda_inputs = []

        for i in range(1, int(value) + 1):
            self.grid.add_widget(Label(text=f"Demanda mes {i}", size_hint_y=None, height=30))
            ti = TextInput(input_filter="int", size_hint_y=None, height=40)
            self.demanda_inputs.append(ti)
            self.grid.add_widget(ti)

    def submit(self, *_):
        if self.spinner_mercado.text == "Mercado" or self.spinner_producto.text == "Producto":
            print("SIGMA: contexto incompleto")
            return

        demanda = [int(t.text) for t in self.demanda_inputs if t.text.strip()]

        payload = {
            "market_id": self.spinner_mercado.text,
            "product_id": self.spinner_producto.text,
            "pais_principal": "CL",
            "activar_digital_twin": self.switch_twin.active,
            "horizonte_meses": int(self.spinner_horizonte.text),
            "periodos": len(demanda),
            "demanda_historica": demanda,
            "costo_unitario": float(self.input_costo_unitario.text) if self.input_costo_unitario.text else 0.0,
            "costo_pedido": float(self.input_costo_pedido.text) if self.input_costo_pedido.text else 0.0,
            "costo_mantencion_pct": float(self.input_costo_mantencion.text) if self.input_costo_mantencion.text else 0.0
        }

        self.manager.sigma_payload = payload
        self.manager.current = "processing"
