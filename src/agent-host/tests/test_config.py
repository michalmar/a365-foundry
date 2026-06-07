from app.config import Settings


def test_defaults_to_operations_engineering() -> None:
    settings = Settings(ALLOW_MOCK_FOUNDRY=True)

    assert settings.foundry_agent == "OperationsEngineering"
    assert settings.should_use_mock_foundry is True


def test_graph_scopes_parse_csv() -> None:
    settings = Settings(ALLOW_MOCK_FOUNDRY=True, GRAPH_SCOPES="openid, profile, User.Read")

    assert settings.graph_scopes == ["openid", "profile", "User.Read"]
