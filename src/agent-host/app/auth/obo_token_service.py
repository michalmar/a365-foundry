from app.config import Settings


class OboConfigurationError(RuntimeError):
    pass


class OboTokenService:
    """On-behalf-of token exchange boundary for Graph and future LOB APIs."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def acquire_graph_token(self, user_assertion: str, scopes: list[str] | None = None) -> str:
        if not self._settings.azure_tenant:
            raise OboConfigurationError("AZURE_TENANT is required for OBO")
        if not self._settings.obo_client_id or not self._settings.obo_client_secret:
            raise OboConfigurationError("OBO_CLIENT_ID and OBO_CLIENT_SECRET are required for OBO")

        from msal import ConfidentialClientApplication

        app = ConfidentialClientApplication(
            client_id=self._settings.obo_client_id,
            client_credential=self._settings.obo_client_secret,
            authority=f"https://login.microsoftonline.com/{self._settings.azure_tenant}",
        )
        result = app.acquire_token_on_behalf_of(
            user_assertion=user_assertion,
            scopes=scopes or self._settings.graph_scopes,
        )
        access_token = result.get("access_token")
        if not access_token:
            message = result.get("error_description", "OBO token exchange failed")
            raise OboConfigurationError(message)
        return access_token
