from typing import Protocol


class SmsProvider(Protocol):
    async def send(self, phone: str, message: str) -> None:
        """Deliver a text message. Raises SmsDeliveryError if it could not be sent."""


class SmsDeliveryError(RuntimeError):
    """Raised when the provider could not accept the message."""
