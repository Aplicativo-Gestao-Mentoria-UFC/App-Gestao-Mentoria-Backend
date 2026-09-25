from email.message import EmailMessage
import logging

import aiosmtplib

from core.config import settings
from core.mail.generate_mails import render_template

logger = logging.getLogger(__name__)


async def send_email(to_email: str, subject: str, content: str):
    message = EmailMessage()
    message["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(
        "Seu cliente de email não suporta HTML. Visualize este email em um cliente compatível."
    )
    message.add_alternative(content, subtype="html")

    kwargs = {
        "hostname": settings.MAIL_HOST,
        "port": settings.MAIL_PORT,
        "start_tls": settings.MAIL_START_TLS,
        "validate_certs": settings.MAIL_VALIDATE_CERTS,
    }
    if settings.MAIL_USERNAME:
        kwargs["username"] = settings.MAIL_USERNAME
    if settings.MAIL_PASSWORD:
        kwargs["password"] = settings.MAIL_PASSWORD

    await aiosmtplib.send(message, **kwargs)


async def send_password_reset_code(to_email: str, code: str, name: str):
    html_content = render_template(
        "password_reset.html",
        nome=name,
        app_name=settings.MAIL_FROM_NAME,
        codigo_formatado=code,
        tempo_expiracao="30 minutos",
        logo_url=settings.LOGO_URL,
    )
    await send_email(
        to_email=to_email,
        subject="Código de recuperação de senha",
        content=html_content,
    )


async def send_confirmation_code(
    to_email: str,
    code: str,
    confirmation_type: str = "email_verification",
):
    type_labels = {
        "email_verification": "Confirmação de Email",
        "activity_confirmation": "Confirmação de Atividade",
        "professor_signup": "Validação de Cadastro de Professor",
    }
    html_content = render_template(
        "sign_up_confirm.html",
        nome="Usuário",
        app_name=settings.MAIL_FROM_NAME,
        codigo_formatado=code,
        tempo_expiracao="30 minutos",
        logo_url=settings.LOGO_URL,
    )
    await send_email(
        to_email=to_email,
        subject=f"Código de {type_labels.get(confirmation_type, 'Confirmação')}",
        content=html_content,
    )


async def safe_send_confirmation_code(
    to_email: str,
    code: str,
    confirmation_type: str = "email_verification",
) -> None:
    """Wrapper para uso em BackgroundTasks.

    Falhas de SMTP são registradas, mas não propagadas para o ciclo ASGI.
    Isso evita que uma exceção ocorrida depois de a resposta HTTP ser enviada
    encerre a conexão keep-alive e faça a próxima requisição falhar.
    """
    try:
        await send_confirmation_code(to_email, code, confirmation_type)
    except Exception:
        logger.exception(
            "Falha ao enviar código de confirmação para %s (tipo=%s)",
            to_email,
            confirmation_type,
        )


async def safe_send_password_reset_code(
    to_email: str,
    code: str,
    name: str,
) -> None:
    """Versão segura para BackgroundTasks do envio de recuperação."""
    try:
        await send_password_reset_code(to_email, code, name)
    except Exception:
        logger.exception(
            "Falha ao enviar código de recuperação de senha para %s",
            to_email,
        )
