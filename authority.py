from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.core.payment_models import PaymentIntent, PaymentEvent
from backend.database.models.subscription import Subscription
from backend.core.config import settings

class PaymentAuthority:
    @staticmethod
    def decide(db: Session, intent: PaymentIntent, provider_status: str, source: str, payload: dict):
        """
        Única autoridad para transicionar estados de suscripción.
        provider_status: approved | rejected | pending
        """
        # 1. Registrar el evento de auditoría
        event = PaymentEvent(
            payment_intent_id=intent.id,
            source=source,
            payload=payload
        )
        db.add(event)

        # 2. Si el pago ya estaba aprobado, no hacemos nada (Idempotencia)
        if intent.status == "approved":
            db.commit()
            return

        # 3. Actualizar estado del Intent
        intent.status = provider_status
        intent.updated_at = datetime.utcnow()

        # 4. Lógica de activación de suscripción
        if provider_status == "approved":
            # Buscamos suscripción existente para el par usuario+device
            sub = db.query(Subscription).filter(
                Subscription.user_id == intent.user_id,
                Subscription.device_id == intent.device_id
            ).first()

            now = datetime.utcnow()
            expires = now + timedelta(days=30)

            if not sub:
                sub = Subscription(
                    user_id=intent.user_id,
                    device_id=intent.device_id,
                    plan_id=intent.plan,
                    status="active",
                    start_date=now,
                    end_date=expires,
                    provider=intent.provider,
                    last_payment_intent_id=intent.id
                )
                db.add(sub)
            else:
                # Actualización de suscripción existente
                sub.plan_id = intent.plan
                sub.status = "active"
                sub.start_date = now
                sub.end_date = expires
                sub.provider = intent.provider
                sub.last_payment_intent_id = intent.id

        elif provider_status in ["rejected", "cancelled"]:
            # Si el pago falla, nos aseguramos de que la suscripción no se active
            # No cancelamos una suscripción activa previa aquí, eso es otra lógica.
            pass

        db.commit()
        db.refresh(intent)
        return intent