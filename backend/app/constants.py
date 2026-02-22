"""Centralised application constants.

Move sensitive values to environment variables or secret storage before
deploying to production.
"""

# Default fingerprint / user-agent string for Playwright sessions.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/139.0.0.0 Safari/537.36"
)

# Internal admin role allowlists.
READ_ADMIN_ROLES = {"platform_owner", "ops", "viewer", "system"}
WRITE_ADMIN_ROLES = {"platform_owner", "ops", "system"}

__all__ = ["DEFAULT_USER_AGENT", "READ_ADMIN_ROLES", "WRITE_ADMIN_ROLES"]
