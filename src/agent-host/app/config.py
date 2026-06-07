from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration sourced from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        case_sensitive=False,
    )

    app_environment: str = Field(default="local", alias="APP_ENVIRONMENT")
    allow_mock_foundry: bool = Field(default=False, alias="ALLOW_MOCK_FOUNDRY")
    project_endpoint: str | None = Field(default=None, alias="PROJECT_ENDPOINT")
    foundry_agent: str = Field(default="OperationsEngineering", alias="FOUNDRY_AGENT")
    foundry_agent_version: str | None = Field(default=None, alias="FOUNDRY_AGENT_VERSION")
    azure_openai_chat_deployment_name: str | None = Field(
        default=None, alias="AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
    )
    azure_openai_summary_deployment_name: str | None = Field(
        default=None, alias="AZURE_OPENAI_SUMMARY_DEPLOYMENT_NAME"
    )
    azure_tenant: str | None = Field(default=None, alias="AZURE_TENANT")
    m365_tenant: str | None = Field(default=None, alias="M365_TENANT")
    bot_id: str | None = Field(default=None, alias="BOT_ID")
    require_bot_auth: bool = Field(default=False, alias="REQUIRE_BOT_AUTH")
    obo_client_id: str | None = Field(default=None, alias="OBO_CLIENT_ID")
    obo_client_secret: str | None = Field(default=None, alias="OBO_CLIENT_SECRET")
    graph_scopes: list[str] = Field(
        default_factory=lambda: ["openid", "profile", "offline_access", "User.Read"],
        alias="GRAPH_SCOPES",
    )
    port: int = Field(default=3978, alias="PORT")

    @field_validator("graph_scopes", mode="before")
    @classmethod
    def parse_graph_scopes(cls, value: str | list[str] | None) -> list[str]:
        if value is None or value == "":
            return ["openid", "profile", "offline_access", "User.Read"]
        if isinstance(value, str):
            return [scope.strip() for scope in value.split(",") if scope.strip()]
        return value

    @property
    def is_local(self) -> bool:
        return self.app_environment.lower() in {"local", "dev", "development", "test"}

    @property
    def should_use_mock_foundry(self) -> bool:
        return self.allow_mock_foundry or (self.is_local and not self.project_endpoint)

    def validate_production(self) -> None:
        missing = []
        if not self.project_endpoint:
            missing.append("PROJECT_ENDPOINT")
        if not self.foundry_agent:
            missing.append("FOUNDRY_AGENT")
        if missing and not self.should_use_mock_foundry:
            raise ValueError("Missing required production configuration: " + ", ".join(missing))
        if self.require_bot_auth:
            auth_missing = []
            if not self.bot_id:
                auth_missing.append("BOT_ID")
            if not (self.m365_tenant or self.azure_tenant):
                auth_missing.append("M365_TENANT or AZURE_TENANT")
            if auth_missing:
                raise ValueError(
                    "Missing required bot auth configuration: " + ", ".join(auth_missing)
                )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_production()
    return settings
