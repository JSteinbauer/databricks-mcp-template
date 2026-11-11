import os

from databricks.sdk import WorkspaceClient
from fastmcp.server.dependencies import get_http_request


def get_user_client() -> WorkspaceClient:
    """WorkspaceClient acting as the calling user.

    On Databricks Apps the user's token is forwarded in the
    `x-forwarded-access-token` header. Locally, fall back to the default
    auth chain (e.g. the Databricks CLI profile).
    """
    
    is_databricks_app = "DATABRICKS_APP_NAME" in os.environ

    if not is_databricks_app:
        from dotenv import load_dotenv

        load_dotenv()

        # Local dev: prefer an explicit CLI profile from DATABRICKS_CONFIG_PROFILE
        if profile := os.getenv("DATABRICKS_CONFIG_PROFILE"):
            return WorkspaceClient(profile=profile)
        return WorkspaceClient()

    try:
        token = get_http_request().headers.get("x-forwarded-access-token")
    except RuntimeError:
        token = None
    if token:
        return WorkspaceClient(token=token, auth_type="pat")
    return WorkspaceClient()


def get_current_user_name() -> str:
    return get_user_client().current_user.me().user_name
