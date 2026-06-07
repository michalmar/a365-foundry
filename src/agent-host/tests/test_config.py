from app.config import Settings


def test_defaults_to_operations_engineering() -> None:
    settings = Settings(ALLOW_MOCK_FOUNDRY=True)

    assert settings.foundry_agent == "OperationsEngineering"
    assert settings.should_use_mock_foundry is True


def test_graph_scopes_parse_csv() -> None:
    settings = Settings(ALLOW_MOCK_FOUNDRY=True, GRAPH_SCOPES="openid, profile, User.Read")

    assert settings.graph_scopes == ["openid", "profile", "User.Read"]


def test_foundry_agent_version_is_optional_nextgen_config() -> None:
    settings = Settings(
        APP_ENVIRONMENT="production",
        PROJECT_ENDPOINT="https://foundry.example.test/api/projects/demo",
        FOUNDRY_AGENT="OperationsEngineering",
        FOUNDRY_AGENT_VERSION="9",
    )

    settings.validate_production()
    assert settings.foundry_agent_version == "9"
