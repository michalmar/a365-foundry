from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from app.config import Settings


@dataclass(frozen=True)
class BotAuthResult:
    authorization_header: str | None
    user_token: str | None


class BotAuthValidator:
    """Inbound auth boundary for the Microsoft 365 Agents SDK adapter.

    Local mode is open so tests and Bot Framework Emulator-style payloads can run without a tenant.
    Production mode fails closed until the tenant-specific Agents SDK adapter is wired and configured.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def validate(self, request: Request) -> BotAuthResult:
        authorization = request.headers.get("authorization")
        user_token = request.headers.get("x-ms-token-aad-access-token")
        if self._settings.require_bot_auth:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="REQUIRE_BOT_AUTH is enabled, but tenant-specific Microsoft 365 Agents SDK "
                "JWT validation is not wired in this offline scaffold.",
            )
        return BotAuthResult(authorization_header=authorization, user_token=user_token)
