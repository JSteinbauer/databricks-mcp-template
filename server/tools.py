from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from server.utils import get_current_user_name, get_user_client

# Demo data, keyed by Databricks user name (email). Replace with your users.
ACCOUNTS: dict[str, dict] = {
    "sp3cb@s-mxs.net": {"account_id": "ACC-1001", "currency": "EUR", "current_balance": 2.23},
    "bob@example.com": {"account_id": "ACC-1002", "currency": "EUR", "current_balance": 3_200.50},
    "carol@example.com": {"account_id": "ACC-1003", "currency": "EUR", "current_balance": 48_000.00},
    "0e2c9d75-15da-4465-829d-b94306ded864": {"account_id": "ACC-1004", "currency": "USD", "current_balance": 5000.00},
}


def _get_account(user_name: str) -> dict:
    account = ACCOUNTS.get(user_name.lower())
    if account is None:
        raise ToolError(f"No account found for user '{user_name}'.")
    return account


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool
    def health() -> dict:
        """
        Check the health of the MCP server and Databricks connection.

        This is a simple diagnostic tool that confirms the server is running properly.
        It's useful for:
        - Monitoring and health checks
        - Testing the MCP connection
        - Verifying the server is responsive

        Returns:
            dict: A dictionary containing:
                - status (str): The health status ("healthy" if operational)
                - message (str): A human-readable status message

        Example response:
            {
                "status": "healthy",
                "message": "Custom MCP Server is healthy and connected to Databricks Apps."
            }
        """
        return {
            "status": "healthy",
            "message": "Custom MCP Server is healthy and connected to Databricks Apps.",
        }
    

    @mcp.tool
    def get_current_user() -> dict:
        """
        Get information about the current authenticated user.

        This tool retrieves details about the user who is currently authenticated
        with the MCP server. When deployed as a Databricks App, this returns
        information about the end user making the request. When running locally,
        it returns information about the developer's Databricks identity.

        Useful for:
        - Personalizing responses based on the user
        - Authorization checks
        - Audit logging
        - User-specific operations

        Returns:
            dict: A dictionary containing:
                - display_name (str): The user's display name
                - user_name (str): The user's username/email
                - active (bool): Whether the user account is active

        Example response:
            {
                "display_name": "John Doe",
                "user_name": "john.doe@example.com",
                "active": true
            }

        Raises:
            Returns error dict if authentication fails or user info cannot be retrieved.
        """
        try:
            user = get_user_client().current_user.me()
            return {
                "display_name": user.display_name,
                "user_name": user.user_name,
                "active": user.active,
            }
        except Exception as e:
            return {"error": str(e), "message": "Failed to retrieve user information"}


    @mcp.tool
    def get_account_details() -> dict:
        """Return the savings account details (account id, currency, current balance)
        of the signed-in Databricks user. Takes no arguments."""
        user_name = get_current_user_name()
        return {"user_name": user_name, **_get_account(user_name)}


    @mcp.tool
    def forecast_savings(
        monthly_savings: float,
        years: int,
        annual_interest_rate: float = 0.05,
    ) -> dict:
        """Forecast the future balance of the signed-in user's savings account.

        Starts from the user's current balance, adds a fixed amount at the end of
        every month and compounds interest monthly.

        Args:
            monthly_savings: Amount saved per month, in the account currency (>= 0).
            years: Saving period in years (1-100).
            annual_interest_rate: Expected annual return as a decimal, e.g. 0.05 for 5%
                (a reasonable long-term assumption for a stock portfolio).
        """
        if monthly_savings < 0:
            raise ToolError("monthly_savings must not be negative.")
        if not 1 <= years <= 100:
            raise ToolError("years must be between 1 and 100.")
        if not -1 < annual_interest_rate <= 1:
            raise ToolError("annual_interest_rate must be a decimal, e.g. 0.05 for 5%.")

        user_name = get_current_user_name()
        account = _get_account(user_name)
        start = account["current_balance"]

        r = annual_interest_rate / 12
        n = years * 12
        growth = (1 + r) ** n
        contributions_fv = monthly_savings * n if r == 0 else monthly_savings * (growth - 1) / r
        final_balance = start * growth + contributions_fv
        total_contributions = monthly_savings * n

        return {
            "user_name": user_name,
            "currency": account["currency"],
            "starting_balance": round(start, 2),
            "monthly_savings": monthly_savings,
            "years": years,
            "annual_interest_rate": annual_interest_rate,
            "total_contributions": round(total_contributions, 2),
            "interest_earned": round(final_balance - start - total_contributions, 2),
            "final_balance": round(final_balance, 2),
        }
