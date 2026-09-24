"""Phone-OTP login."""

from fastapi import APIRouter, Header, Request, status

from api.core.deps import ClientIp, CurrentUser, RedisDep, SessionDep, SettingsDep, SmsDep
from api.core.errors import ApiError
from api.schemas.auth import OtpRequestIn, OtpRequestOut, OtpVerifyIn, RefreshIn, TokensOut
from api.schemas.common import Ack, ErrorResponse
from api.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

ERRORS: dict[int | str, dict[str, object]] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
}


def _invalid_phone() -> ApiError:
    return ApiError(status.HTTP_400_BAD_REQUEST, "phone_invalid")


@router.post(
    "/otp/request",
    name="request_otp",
    response_model=OtpRequestOut,
    responses=ERRORS,
    summary="Send a login code by SMS",
)
async def request_otp(
    payload: OtpRequestIn,
    session: SessionDep,
    redis: RedisDep,
    sms: SmsDep,
    settings: SettingsDep,
    ip: ClientIp,
) -> OtpRequestOut:
    try:
        challenge = await auth_service.request_otp(
            session,
            redis,
            sms,
            settings,
            raw_phone=payload.phone,
            client_ip=ip,
            language=payload.language,
        )
    except auth_service.InvalidPhoneError as exc:
        raise _invalid_phone() from exc

    return OtpRequestOut(
        phone=challenge.phone,
        expires_in_s=challenge.expires_in_s,
        debug_code=challenge.debug_code,
    )


@router.post(
    "/otp/verify",
    name="verify_otp",
    response_model=TokensOut,
    responses=ERRORS,
    summary="Exchange a login code for tokens",
)
async def verify_otp(
    payload: OtpVerifyIn,
    request: Request,
    session: SessionDep,
    redis: RedisDep,
    settings: SettingsDep,
    user_agent: str | None = Header(default=None),
) -> TokensOut:
    try:
        pair = await auth_service.verify_otp(
            session,
            redis,
            settings,
            raw_phone=payload.phone,
            code=payload.code,
            user_agent=user_agent or request.headers.get("user-agent"),
        )
    except auth_service.InvalidPhoneError as exc:
        raise _invalid_phone() from exc

    return TokensOut(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in_s=pair.expires_in_s,
        user=pair.user,
    )


@router.post(
    "/refresh",
    name="refresh_tokens",
    response_model=TokensOut,
    responses=ERRORS,
    summary="Rotate a refresh token",
)
async def refresh_tokens(
    payload: RefreshIn,
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    user_agent: str | None = Header(default=None),
) -> TokensOut:
    pair = await auth_service.refresh_tokens(
        session,
        settings,
        refresh_token=payload.refresh_token,
        user_agent=user_agent or request.headers.get("user-agent"),
    )
    return TokensOut(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in_s=pair.expires_in_s,
        user=pair.user,
    )


@router.post("/logout", name="logout", response_model=Ack, summary="Sign out this device")
async def logout(payload: RefreshIn, session: SessionDep) -> Ack:
    await auth_service.revoke_refresh_token(session, refresh_token=payload.refresh_token)
    return Ack()


@router.post(
    "/logout-all",
    name="logout_all_devices",
    response_model=Ack,
    responses={401: {"model": ErrorResponse}},
    summary="Sign out everywhere",
)
async def logout_all_devices(user: CurrentUser, session: SessionDep) -> Ack:
    await auth_service.revoke_all_for_user(session, user.id)
    await session.commit()
    return Ack()
