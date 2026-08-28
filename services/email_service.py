from core.mail.generate_mails import render_template
import aiosmtplib
from email.message import EmailMessage

from core.config import settings

async def send_email(to_email: str, subject: str, content: str):
        message = EmailMessage()
        message["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(
                "Seu cliente de email não suporta HTML. Por favor, visualize este email em um navegador.",
        )

        message.add_alternative(content, subtype="html")

        await aiosmtplib.send(
            message,
            hostname=settings.MAIL_HOST,
            port=settings.MAIL_PORT,
            username=settings.MAIL_USERNAME,
            password=settings.MAIL_PASSWORD,
            start_tls=True,
            validate_certs=True,
        )

async def send_password_reset_code(to_email: str, code: str, name: str):
        html_content = render_template(
            "password_reset.html",
            nome=name,
            app_name=settings.MAIL_FROM_NAME,
            codigo_formatado=code,
            tempo_expiracao="30 minutos",
            logo_url=settings.LOGO_URL
        )

        await send_email(
            to_email=to_email,
            subject="Código de recuperação de senha",
            content=html_content,
        )


async def send_confirmation_code(
        to_email: str, code: str, confirmation_type: str = "email_verification"
    ):
        type_labels = {
            "email_verification": "Confirmação de Email",
            "activity_confirmation": "Confirmação de Atividade",
        }

        type_label = type_labels.get(confirmation_type, "Confirmação")

        html_content = render_template(
            "sign_up_confirm.html",
            nome="Usuário",
            app_name=settings.MAIL_FROM_NAME,
            codigo_formatado=code,
            tempo_expiracao="30 minutos",
            logo_url=settings.LOGO_URL
        )

        await send_email(
            to_email=to_email,
            subject=f"Código de {type_label}",
            content=html_content,
        )