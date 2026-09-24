from pydantic import BaseModel, Field

from api.models.enums import Language
from api.schemas.user import UserOut


class OtpRequestIn(BaseModel):
    # Saudi mobile in any common format; Arabic-Indic digits are accepted.
    phone: str = Field(min_length=6, max_length=20, examples=["0501234567"])
    language: Language = Language.AR


class OtpRequestOut(BaseModel):
    # Echoed back in E.164 so the client can show which number was used.
    phone: str
    expires_in_s: int
    # Present only when OTP_EXPOSE_CODE is enabled (local development).
    debug_code: str | None = None


class OtpVerifyIn(BaseModel):
    phone: str = Field(min_length=6, max_length=20)
    code: str = Field(min_length=4, max_length=8)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=200)


class TokensOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - the OAuth scheme name
    expires_in_s: int
    user: UserOut
