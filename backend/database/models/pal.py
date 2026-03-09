from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from backend.core.payment_models import PaymentIntent, PaymentStatus, SubscriptionStatus, PALAuditLog, PaymentEvent
from backend.database.models.subscription import Subscription
from backend.core.config import settings
import logging

logger = logging.getLogger("olimpo.pal")

class PaymentAuthority:
    @staticmethod
    def decide_subscription_transition(db: Session, intent: PaymentIntent, provider_status: str, source: str):
        """
        Única autoridad para transicionar estados de suscripción.
        """
        old_intent_status = intent.status
        
        # Mapeo de estados del proveedor a PAL
        new_intent_status = PaymentStatus.PENDING
        if provider_status in ["approved", "authorized", "completed", "success"]:
            new_intent_status = PaymentStatus.APPROVED
        elif provider_status in ["rejected", "cancelled", "failed"]:
            new_intent_status = PaymentStatus.REJECTED

        # Evitar procesamiento si no hay cambio (excepto si es aprobación para asegurar activación)
        if new_intent_status == old_intent_status and new_intent_status != PaymentStatus.APPROVED:
            return None

        intent.status = new_intent_status
        intent.updated_at = datetime.now(timezone.utc)

        # Transición de Suscripción
        subscription = db.query(Subscription).filter(
            Subscription.user_id == intent.user_id,
            Subscription.device_id == intent.device_id
        ).first()

        if new_intent_status == PaymentStatus.APPROVED:
            if not subscription:
                subscription = Subscription(
                    user_id=intent.user_id,
                    device_id=intent.device_id,
                    plan_id=intent.plan_id,
                    status=SubscriptionStatus.ACTIVE
                )
                db.add(subscription)
            
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.plan_id = intent.plan_id
            subscription.provider = intent.provider
            subscription.last_payment_intent_id = intent.id
            subscription.start_date = datetime.now(timezone.utc)
            subscription.end_date = datetime.now(timezone.utc) + timedelta(days=30)
            subscription.updated_at = datetime.now(timezone.utc)

        # Registro de Auditoría
        audit = PALAuditLog(
            intent_id=intent.id,
            user_id=intent.user_id,
            action="AUTHORITY_DECISION",
            previous_status=old_intent_status,
            new_status=new_intent_status,
            context={
                "provider_status": provider_status,
                "source": source,
                "mode": intent.mode
            }
        )
        db.add(audit)
        
        # Registro de Evento
        event = PaymentEvent(
            intent_id=intent.id,
            type=source,
            payload={"provider_status": provider_status},
            source=source
        )
        db.add(event)
        db.commit()
        return subscription