from typing import Any

from microsoft_agents.activity import Activity, ActivityTypes, Attachment
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.core.app import AgentApplication, ApplicationOptions
from microsoft_agents.hosting.core.authorization import (
    AgentAuthConfiguration,
    AuthTypes,
    ClaimsIdentity,
)
from microsoft_agents.hosting.core.authorization.access_token_provider_base import (
    AccessTokenProviderBase,
)
from microsoft_agents.hosting.core.storage import MemoryStorage
from microsoft_agents.hosting.core.turn_context import TurnContext
from microsoft_agents.hosting.fastapi import CloudAdapter

from app.agent_handler import AgentHandler
from app.config import Settings

SERVICE_CONNECTION = "SERVICE_CONNECTION"


class LocalTokenProvider(AccessTokenProviderBase):
    """Non-production token provider for tenant-free SDK adapter validation."""

    async def get_access_token(
        self, resource_url: str, scopes: list[str], force_refresh: bool = False
    ) -> str:
        return "local-token"

    async def acquire_token_on_behalf_of(self, scopes: list[str], user_assertion: str) -> str:
        return "local-token"

    async def get_agentic_application_token(
        self, tenant_id: str, agent_app_instance_id: str
    ) -> str | None:
        return "local-token"

    async def get_agentic_instance_token(
        self, tenant_id: str, agent_app_instance_id: str
    ) -> tuple[str, str]:
        return "local-token", ""

    async def get_agentic_user_token(
        self,
        tenant_id: str,
        agent_app_instance_id: str,
        agentic_user_id: str,
        scopes: list[str],
    ) -> str | None:
        return "local-token"


class LocalConnectionManager:
    def __init__(self) -> None:
        self._provider = LocalTokenProvider()
        self._configuration = AgentAuthConfiguration(
            connection_name=SERVICE_CONNECTION,
            anonymous_allowed=True,
        )

    def get_connection(self, connection_name: str) -> AccessTokenProviderBase:
        return self._provider

    def get_default_connection(self) -> AccessTokenProviderBase:
        return self._provider

    def get_token_provider(
        self, claims_identity: ClaimsIdentity, service_url: str
    ) -> AccessTokenProviderBase:
        return self._provider

    def get_default_connection_configuration(self) -> AgentAuthConfiguration:
        return self._configuration


def create_cloud_adapter(settings: Settings) -> CloudAdapter:
    return CloudAdapter(connection_manager=create_connection_manager(settings))


def create_agent_application(handler: AgentHandler) -> AgentApplication:
    application = AgentApplication(ApplicationOptions(storage=MemoryStorage()))

    @application.activity(ActivityTypes.message)
    async def on_message(context: TurnContext, state: Any) -> None:
        response = await handler.handle_activity(
            _activity_to_dict(context.activity),
            user_token=_extract_user_token(context.activity),
        )
        await context.send_activity(_response_to_activity(response))

    return application


def create_connection_manager(
    settings: Settings,
) -> LocalConnectionManager | MsalConnectionManager:
    if not settings.require_bot_auth:
        return LocalConnectionManager()

    return MsalConnectionManager(
        {
            SERVICE_CONNECTION: AgentAuthConfiguration(
                auth_type=AuthTypes.user_managed_identity,
                client_id=settings.bot_id,
                tenant_id=settings.m365_tenant or settings.azure_tenant,
                connection_name=SERVICE_CONNECTION,
            )
        }
    )


def _activity_to_dict(activity: Activity) -> dict[str, Any]:
    return activity.model_dump(by_alias=True, exclude_none=True)


def _response_to_activity(response: dict[str, Any]) -> Activity:
    attachments = []
    for attachment in response.get("attachments", []):
        payload = {
            "content_type": attachment["contentType"],
            "content": attachment.get("content"),
        }
        for source_key, target_key in (
            ("contentUrl", "content_url"),
            ("name", "name"),
            ("thumbnailUrl", "thumbnail_url"),
        ):
            value = attachment.get(source_key)
            if value is not None:
                payload[target_key] = value
        attachments.append(Attachment(**payload))
    return Activity(
        type=ActivityTypes.message,
        text=response.get("text", ""),
        attachments=attachments,
        entities=response.get("entities", []),
    )


def _extract_user_token(activity: Activity) -> str | None:
    channel_data = activity.channel_data
    if isinstance(channel_data, dict):
        token = channel_data.get("userToken") or channel_data.get("accessToken")
        if isinstance(token, str):
            return token
    return None
