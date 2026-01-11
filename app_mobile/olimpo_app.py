from datetime import date

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager

# ===== SCREENS BASE =====
from screens.auth import AuthScreen
from screens.terms import TermsScreen
from screens.plan import PlanScreen
from screens.billing import BillingScreen
from screens.hub import HubScreen

# ===== MODELOS =====
from screens.epsilon_input import EpsilonInputScreen
from screens.sigma_input import SigmaInputScreen
from screens.poseidon_input import PoseidonInputScreen

# ===== FLUJO =====
from screens.processing import ProcessingScreen
from screens.result import ResultScreen

# ===== CORE FASE 5 =====
from core.device import get_or_create_device_id
from core.http_client import OlimpoHTTPClient
from core.storage import load_json


class OlimpoApp(App):

    def build(self):
        sm = ScreenManager()

        # ===== REGISTRO DE SCREENS =====
        sm.add_widget(AuthScreen(name="auth"))
        sm.add_widget(TermsScreen(name="terms"))
        sm.add_widget(PlanScreen(name="plan"))
        sm.add_widget(BillingScreen(name="billing"))
        sm.add_widget(HubScreen(name="hub"))

        sm.add_widget(EpsilonInputScreen(name="epsilon"))
        sm.add_widget(SigmaInputScreen(name="sigma"))
        sm.add_widget(PoseidonInputScreen(name="poseidon"))

        sm.add_widget(ProcessingScreen(name="processing"))
        sm.add_widget(ResultScreen(name="result"))

        # ===== ESTADO GLOBAL =====
        sm.user_state = "new_user"
        sm.terms_accepted = False

        sm.plan_active = False
        sm.plan_type = None
        sm.plan_started_at = None
        sm.next_billing_date = None

        sm.epsilon_payload = None
        sm.sigma_payload = None
        sm.poseidon_payload = None

        sm.last_model = None
        sm.last_payload = None

        # ===== FASE 5 =====
        sm.device_id = get_or_create_device_id()

        session = load_json("data/session.json")
        sm.jwt = session.get("jwt") if session else None

        sm.http = OlimpoHTTPClient(
            base_url="https://TU_BACKEND_AQUI",
            device_id=sm.device_id,
            token=sm.jwt
        )

        sm.current = "auth"
        return sm
