"""SMS delivery behind an interface. The real provider is an open decision (brief §11)."""

from functools import lru_cache

from api.core.config import get_settings
from api.integrations.sms.base import SmsDeliveryError, SmsProvider
from api.integrations.sms.mock import MockSmsProvider

__all__ = ["MockSmsProvider", "SmsDeliveryError", "SmsProvider", "get_sms_provider"]


@lru_cache
def get_sms_provider() -> SmsProvider:
    # Only the mock exists today; a real adapter is added when the provider is chosen.
    _ = get_settings().sms_provider
    return MockSmsProvider()
