import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Configurar el path para importar el backend
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.models.subscription import Subscription
from backend.database.models.user import User

# Configuración de la DB (Asegúrate de que coincida con tu core/config.py)
DATABASE_URL = "sqlite:///backend/db/olimpo.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def send_reminder_email(email: str, days_left: int, plan: str):
    """
    Placeholder para tu servicio de correos (SendGrid, Mailgun, etc.)
    """
    print(f"📧 ENVIANDO CORREO A: {email}")
    print(f"   Mensaje: Tu plan {plan.upper()} vence en {days_left} días.")
    print(f"   Acción: ¡Renueva ahora para no perder acceso a tus modelos!")
    # Aquí iría la lógica real de smtplib o API de correos.

def check_and_notify():
    db = SessionLocal()
    try:
        print(f"🔍 [{datetime.now()}] Revisando suscripciones por vencer...")
        
        # Calculamos el rango de tiempo para "dentro de 2 días"
        today = datetime.utcnow()
        target_date_start = (today + timedelta(days=2)).replace(hour=0, minute=0, second=0)
        target_date_end = target_date_start + timedelta(days=1)

        # Buscamos suscripciones activas que venzan en esa ventana de tiempo
        expiring_subs = db.query(Subscription).join(User).filter(
            Subscription.status == "active",
            Subscription.end_date >= target_date_start,
            Subscription.end_date < target_date_end
        ).all()

        if not expiring_subs:
            print("✅ No hay suscripciones que venzan en 2 días.")
            return

        for sub in expiring_subs:
            user_email = sub.user.email
            send_reminder_email(user_email, 2, sub.plan)
            print(f"✅ Recordatorio enviado a {user_email}")

    except Exception as e:
        print(f"❌ Error en el proceso de notificación: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Este script se ejecutaría una vez al día vía Cron
    check_and_notify()