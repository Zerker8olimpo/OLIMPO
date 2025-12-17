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


class OlimpoApp(App):
    """
    OLIMPO APP
    Núcleo lógico de la aplicación.
    Contiene:
    - Estados de usuario
    - Routing centralizado
    - Registro completo de pantallas
    """

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

        # ===== ESTADO GLOBAL DEL USUARIO =====
        sm.user_state = "new_user"

        sm.terms_accepted = False

        sm.plan_active = False
        sm.plan_type = None
        sm.plan_started_at = None
        sm.next_billing_date = None

        # Payloads temporales
        sm.epsilon_payload = None
        sm.sigma_payload = None
        sm.poseidon_payload = None

        # Última ejecución
        sm.last_model = None
        sm.last_payload = None

        sm.current = "auth"
        return sm

    # =====================================================
    # ROUTING CENTRALIZADO (CORAZÓN DE LA APP)
    # =====================================================
    def route_user(self):
        sm = self.root
        today = date.today()

        # 1. Términos y condiciones
        if not sm.terms_accepted:
            sm.user_state = "terms_pending"
            sm.current = "terms"
            return

        # 2. Plan no activo
        if not sm.plan_active:
            sm.user_state = "plan_pending"
            sm.current = "plan"
            return

        # 3. Cobranza vencida
        if sm.next_billing_date and today >= sm.next_billing_date:
            sm.user_state = "billing_due"
            sm.current = "billing"
            return

        # 4. Usuario activo
        sm.user_state = "active"
        sm.current = "hub"


if __name__ == "__main__":
    OlimpoApp().run()