"""Nebi environment listing for jhub-apps environment selector."""
# ruff: noqa: F821 - `c` is a magic global provided by JupyterHub

import json
import logging
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from z2jh import get_config

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Synchronous Keycloak token exchange helpers
# ---------------------------------------------------------------------------
# jhub-apps calls the conda_envs callable synchronously from its FastAPI
# service, so we MUST use urllib.request (not async Tornado).
# The token exchange logic mirrors 01-spawner.py but is synchronous.


def _sync_refresh_access_token(refresh_token, keycloak_url, hub_client_id, hub_client_secret):
    """Use the refresh token to get a fresh access token from Keycloak.

    Returns the new access token string, or empty string on failure.
    """
    body = urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": hub_client_id,
        "client_secret": hub_client_secret,
    }).encode("utf-8")
    req = Request(
        keycloak_url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("access_token", "")
    except Exception as exc:
        log.error(
            "nebi-envs: Keycloak token refresh failed: %s (url=%s, client_id=%s)",
            exc, keycloak_url, hub_client_id,
        )
        return ""


def _sync_exchange_access_token_for_nebi_id_token(
    access_token, keycloak_url, nebi_client_id, hub_client_id, hub_client_secret,
):
    """Exchange a JupyterHub access token for a Nebi-audience ID token via Keycloak.

    Returns the Nebi ID token string, or empty string on failure.
    """
    body = urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": access_token,
        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "audience": nebi_client_id,
        "client_id": hub_client_id,
        "client_secret": hub_client_secret,
    }).encode("utf-8")
    req = Request(
        keycloak_url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            # Prefer id_token if present (has user identity claims), fall back to access_token
            return data.get("id_token") or data.get("access_token", "")
    except Exception as exc:
        log.error(
            "nebi-envs: Keycloak token exchange failed: %s (url=%s, audience=%s, client_id=%s)",
            exc, keycloak_url, nebi_client_id, hub_client_id,
        )
        return ""


def _sync_exchange_nebi_id_token_for_jwt(nebi_id_token, nebi_internal_url):
    """Exchange a Nebi-audience ID token for a Nebi JWT via the session endpoint.

    Returns the Nebi JWT string, or empty string on failure.
    """
    session_url = f"{nebi_internal_url.rstrip('/')}/api/v1/auth/session"
    req = Request(
        session_url,
        headers={"Cookie": f"IdToken={nebi_id_token}"},
        method="GET",
    )
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("token", "")
    except Exception as exc:
        log.error(
            "nebi-envs: Nebi session exchange failed: %s (url=%s)",
            exc, session_url,
        )
        return ""


# ---------------------------------------------------------------------------
# Nebi environment listing callable
# ---------------------------------------------------------------------------

def get_nebi_environments(user):
    """Return list of ready nebi workspaces as '{owner_username}/{workspace_name}' strings.

    Called synchronously by jhub-apps to populate the environment selector dropdown.
    The `user` parameter is a dict from the JupyterHub API, containing:
      {"name": "alice", "auth_state": {"access_token": "...", "refresh_token": "..."}, ...}

    On any failure, returns an empty list (graceful degradation).
    """
    username = user.get("name", "<unknown>")

    # Read config values
    keycloak_url = get_config("custom.keycloak-token-url", "")
    nebi_cid = get_config("custom.nebi-client-id", "")
    hub_cid = get_config("custom.jupyterhub-client-id", "")
    hub_secret = os.environ.get("JUPYTERHUB_OIDC_CLIENT_SECRET", "")
    nebi_url = get_config("custom.nebi-internal-url", "")

    if not all([keycloak_url, nebi_cid, hub_cid, hub_secret, nebi_url]):
        missing = []
        if not keycloak_url:
            missing.append("keycloak-token-url")
        if not nebi_cid:
            missing.append("nebi-client-id")
        if not hub_cid:
            missing.append("jupyterhub-client-id")
        if not hub_secret:
            missing.append("JUPYTERHUB_OIDC_CLIENT_SECRET")
        if not nebi_url:
            missing.append("nebi-internal-url")
        log.error(
            "nebi-envs: cannot list environments for %s, missing config: %s",
            username, ", ".join(missing),
        )
        return []

    # Extract auth_state from user dict
    auth_state = user.get("auth_state")
    if not auth_state:
        log.warning("nebi-envs: no auth_state for user %s, cannot list environments", username)
        return []

    refresh_token = auth_state.get("refresh_token")
    access_token = auth_state.get("access_token", "")

    if not refresh_token and not access_token:
        log.warning(
            "nebi-envs: no access_token or refresh_token for user %s, cannot list environments",
            username,
        )
        return []

    try:
        # Step 1: Refresh the access token (preferred) or use existing one
        if refresh_token:
            access_token = _sync_refresh_access_token(
                refresh_token, keycloak_url, hub_cid, hub_secret,
            )
            if not access_token:
                log.warning(
                    "nebi-envs: token refresh returned no access token for %s", username,
                )
                return []

        # Step 2: Exchange access token for Nebi-audience ID token
        nebi_id_token = _sync_exchange_access_token_for_nebi_id_token(
            access_token, keycloak_url, nebi_cid, hub_cid, hub_secret,
        )
        if not nebi_id_token:
            log.warning(
                "nebi-envs: Keycloak token exchange returned no token for %s", username,
            )
            return []

        # Step 3: Exchange Nebi ID token for Nebi JWT
        nebi_jwt = _sync_exchange_nebi_id_token_for_jwt(nebi_id_token, nebi_url)
        if not nebi_jwt:
            log.warning(
                "nebi-envs: Nebi session returned no JWT for %s", username,
            )
            return []

        # Step 4: Fetch workspaces from Nebi API
        workspaces_url = f"{nebi_url.rstrip('/')}/api/v1/workspaces"
        req = Request(
            workspaces_url,
            headers={"Authorization": f"Bearer {nebi_jwt}"},
            method="GET",
        )
        try:
            with urlopen(req, timeout=10) as resp:
                workspaces = json.loads(resp.read())
        except Exception as exc:
            log.error(
                "nebi-envs: failed to fetch workspaces for %s: %s (url=%s)",
                username, exc, workspaces_url,
            )
            return []

        # Step 5: Filter to ready workspaces and format as owner/name
        envs = []
        for ws in workspaces:
            if ws.get("status") != "ready":
                continue
            owner = ws.get("owner", {})
            owner_username = owner.get("username", "")
            ws_name = ws.get("name", "")
            if owner_username and ws_name:
                envs.append(f"{owner_username}/{ws_name}")

        log.info(
            "nebi-envs: listed %d ready environments for %s (total workspaces: %d)",
            len(envs), username, len(workspaces),
        )
        return envs

    except Exception:
        log.exception(
            "nebi-envs: unexpected error listing environments for %s", username,
        )
        return []


# ---------------------------------------------------------------------------
# Register the callable with jhub-apps (only when enabled)
# ---------------------------------------------------------------------------
_nebi_env_selector = get_config("custom.nebi-environment-selector", False)
_nebi_internal_url = get_config("custom.nebi-internal-url", "")

if _nebi_env_selector and _nebi_internal_url:
    c.JAppsConfig.conda_envs = get_nebi_environments
    log.info("nebi-envs: environment selector enabled (nebi_url=%s)", _nebi_internal_url)
else:
    if _nebi_env_selector and not _nebi_internal_url:
        log.warning(
            "nebi-envs: nebi-environment-selector is true but nebi-internal-url is not set, "
            "environment selector will not be enabled"
        )
