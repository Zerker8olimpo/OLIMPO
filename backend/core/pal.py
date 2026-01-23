from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.core.payment_intent import PaymentIntent, PaymentStatus
from backend.database.models.subscription import Subscription
from backend.core.audit_log import PALAuditLog
from backend.core.config import settings
import logging

logger = logging.getLogger("olimpo.pal")

class PaymentAuthority:
    @staticmethod
    def decide_subscription_transition(db: Session, intent: PaymentIntent, provider_status: str):
        """
        Única autoridad para transicionar estados de suscripción.
        """
        old_status = intent.status
        
        # Lógica de mapeo de estados del proveedor a estados PAL
        if provider_status in ["approved", "authorized", "completed"]:
            new_intent_status = PaymentStatus.APPROVED
        elif provider_status in ["rejected", "cancelled", "failed"]:
            new_intent_status = PaymentStatus.REJECTED
        else:
            new_intent_status = PaymentStatus.PENDING

        if new_intent_status == old_status and new_intent_status != PaymentStatus.APPROVED:
            return None

        # Actualizar Intent
        intent.status = new_intent_status
        
        # Si es aprobado, transicionar suscripción
        subscription = None
        if new_intent_status == PaymentStatus.APPROVED:
            subscription = db.query(Subscription).filter(
                Subscription.user_id == intent.user_id,
                Subscription.device_id == intent.device_id
            ).first()
            
            if not subscription:
                subscription = Subscription(
                    user_id=intent.user_id,
                    device_id=intent.device_id,
                    plan_id=intent.plan_id,
                    status="active"
                )
                db.add(subscription)
            
            subscription.status = "active"
            subscription.plan_id = intent.plan_id
            subscription.start_date = datetime.utcnow()
            subscription.end_date = datetime.utcnow() + timedelta(days=30)
            subscription.provider = intent.provider

        # Auditoría
        audit = PALAuditLog(
            intent_id=intent.id,
            user_id=intent.user_id,
            action="DECISION_MADE",
            previous_status=old_status,
            new_status=new_intent_status,
            context={"provider_status": provider_status, "mode": settings.PAYMENTS_MODE}
        )
        db.add(audit)
        db.commit()
        return subscription