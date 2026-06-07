from microsoft_agents.activity import ActivityTypes
from microsoft_agents.authentication.msal import MsalConnectionManager

from app.config import Settings
from app.m365_adapter import (
    LocalConnectionManager,
    _response_to_activity,
    create_connection_manager,
)


def test_response_to_activity_preserves_text() -> None:
    activity = _response_to_activity(
        {
            "type": "message",
            "text": "hello",
        }
    )

    assert activity.type == ActivityTypes.message
    assert activity.text == "hello"


def test_uses_local_connection_manager_without_bot_auth() -> None:
    connection_manager = create_connection_manager(Settings(ALLOW_MOCK_FOUNDRY=True))

    assert isinstance(connection_manager, LocalConnectionManager)


def test_uses_msal_connection_manager_with_bot_auth() -> None:
    connection_manager = create_connection_manager(
        Settings(
            ALLOW_MOCK_FOUNDRY=True,
            REQUIRE_BOT_AUTH=True,
            BOT_ID="00000000-0000-0000-0000-000000000000",
            M365_TENANT="00000000-0000-0000-0000-000000000001",
        )
    )

    assert isinstance(connection_manager, MsalConnectionManager)
