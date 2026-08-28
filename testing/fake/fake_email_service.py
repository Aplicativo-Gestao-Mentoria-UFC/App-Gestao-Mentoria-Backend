from dataclasses import dataclass
from typing import Any

@dataclass
class SentEmail:
    recipient: str
    template: str
    context: dict[str, Any]

class FakeEmailService:
    def __init__(self):
        self.sent_emails: list[SentEmail] = []

    async def send_verification_email(self, recipient:str, template:str, token: str) -> None: 
        self.sent_emails.append(
            SentEmail(
                recipient=recipient,
                template=template,
                context={"token": token},
            )
        )

    async def send_password_reset_code(self, recipient:str, template:str, code: str) -> None:
        self.sent_emails.append(
            SentEmail(
                recipient=recipient,
                template=template,
                context={"code": code},
            )
        )

    async def send_professor_signup_email(self, recipient:str, template:str, token: str) -> None:
        self.sent_emails.append(
            SentEmail(
                recipient=recipient,
                template=template,
                context={"token": token},
            )
        )
        