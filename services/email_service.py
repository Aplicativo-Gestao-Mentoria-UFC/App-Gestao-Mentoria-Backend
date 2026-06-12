from email.message import EmailMessage
import aiosmtplib

from core.config import settings

async def send_email(to_email: str, subject: str, content: str):
    message = EmailMessage()
    message["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(content)

    await aiosmtplib.send(
        message,
        hostname=settings.MAIL_HOST,
        port=settings.MAIL_PORT,
        username=settings.MAIL_USERNAME,
        password=settings.MAIL_PASSWORD,
        start_tls=True,
        validate_certs=False,
    )

async def send_password_reset_code(to_email: str, code: str):
    content = f"""
Olá!

Recebemos uma solicitação para redefinir sua senha.

Seu código de recuperação é:

{code}

Esse código expira em 30 minutos e só pode ser usado uma vez.

Se você não solicitou essa recuperação, ignore este email.
"""

    await send_email(
        to_email=to_email,
        subject="Código de recuperação de senha",
        content=content,
    )