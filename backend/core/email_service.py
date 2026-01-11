import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to_email: str, subject: str, body: str):
    """
    Envía un correo simple usando SMTP.
    Requiere configurar variables de entorno: SMTP_USER y SMTP_PASSWORD.
    Si no están configuradas, solo imprime en consola (Mock).
    """
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")

    # Modo Mock para desarrollo si no hay credenciales
    if not smtp_user or not smtp_password:
        print(f"==================================================")
        print(f"[EMAIL MOCK] To: {to_email}")
        print(f"[EMAIL MOCK] Subject: {subject}")
        print(f"[EMAIL MOCK] Body: {body.strip()[:100]}...")
        print(f"==================================================")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = f"OLIMPO <{smtp_user}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        print(f"[EMAIL] Enviado correctamente a {to_email}")
    except Exception as e:
        print(f"[EMAIL ERROR] Fallo al enviar a {to_email}: {e}")

def send_subscription_active_email(to_email: str, plan: str, end_date: str):
    subject = f"Bienvenido a OLIMPO {plan.upper()} - Suscripción Activada"
    body = f"""
    Hola,

    Tu suscripción al plan {plan.upper()} ha sido activada exitosamente.
    Tienes acceso a los modelos de simulación hasta el: {end_date}.

    Gracias por confiar en OLIMPO.
    """
    send_email(to_email, subject, body)

def send_subscription_expired_email(to_email: str, plan: str):
    subject = "Tu suscripción a OLIMPO ha finalizado"
    body = f"""
    Hola,

    Te informamos que tus 30 días del plan {plan.upper()} han concluido hoy.
    Para continuar usando los modelos de simulación, por favor renueva tu suscripción desde la aplicación.

    Atentamente,
    Equipo OLIMPO.
    """
    send_email(to_email, subject, body)