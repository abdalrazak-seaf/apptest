import logging
from dataclasses import dataclass, field

from api.core.phone import mask_phone

logger = logging.getLogger("api.sms.mock")


@dataclass
class SentSms:
    phone: str
    message: str


@dataclass
class MockSmsProvider:
    """Logs messages instead of sending them, and keeps them for assertions in tests.

    In local development the login code is printed to the API log, so you can sign in
    without a real SMS provider.
    """

    sent: list[SentSms] = field(default_factory=list)

    async def send(self, phone: str, message: str) -> None:
        self.sent.append(SentSms(phone=phone, message=message))
        # `message` is reserved by logging.LogRecord, so the body goes under `sms_body`.
        logger.info(
            "sms_sent_mock",
            extra={"phone": mask_phone(phone), "sms_body": message},
        )

    def last_for(self, phone: str) -> SentSms | None:
        return next((s for s in reversed(self.sent) if s.phone == phone), None)
