"""KubeSpawner configuration."""
# ruff: noqa: F821 - `c` is a magic global provided by JupyterHub

import asyncio
import json
import logging
import os
import urllib.error
import urllib.request
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from z2jh import get_config

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
# Dynamic PVC per user via the cluster's default StorageClass.
# We configure volumes here instead of via singleuser.storage in values.yaml because
# jhub-apps' JHubSpawner expects volumes as a list, but the subchart's dynamic storage
# generates a dict, causing a TraitError on startup.
#
# Using fixed /home/jovyan mount path because {username} expands differently in
# KubeSpawner (escaped slug) vs base Spawner traits like notebook_dir (raw username),
# causing a path mismatch when usernames contain special characters (e.g. emails).
# Each user still gets an isolated PVC via claim-{username}.
c.KubeSpawner.storage_pvc_ensure = True
c.KubeSpawner.storage_capacity = "10Gi"
c.KubeSpawner.storage_access_modes = ["ReadWriteOnce"]
c.KubeSpawner.volumes = [
    {
        "name": "home",
        "persistentVolumeClaim": {
            "claimName": "claim-{username}",
        },
    },
]
c.KubeSpawner.volume_mounts = [
    {
        "name": "home",
        "mountPath": "/home/jovyan",
    },
]

c.KubeSpawner.notebook_dir = "/home/jovyan"
c.KubeSpawner.working_dir = "/home/jovyan"


# ---------------------------------------------------------------------------
# Nebi binary (init container)
# ---------------------------------------------------------------------------
# Copy the nebi binary from the nebi server image into the JupyterLab pod
# so the version matches what the deployment specifies, not what was baked
# into the jupyterlab image at build time.
nebi_image = get_config("custom.nebi-image", "")
if nebi_image:
    c.KubeSpawner.volumes.append({
        "name": "nebi-bin",
        "emptyDir": {},
    })
    c.KubeSpawner.volume_mounts.append({
        "name": "nebi-bin",
        "mountPath": "/usr/local/bin/nebi",
        "subPath": "nebi",
    })
    c.KubeSpawner.init_containers.append({
        "name": "install-nebi",
        "image": nebi_image,
        "command": ["sh", "-c", "cp /app/nebi /nebi-bin/nebi && chmod +x /nebi-bin/nebi"],
        "imagePullPolicy": get_config("custom.nebi-image-pull-policy", "IfNotPresent"),
        "volumeMounts": [{
            "name": "nebi-bin",
            "mountPath": "/nebi-bin",
        }],
    })


# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
# Start with extraEnv from values.yaml so deployers can inject env vars
# (e.g. MLFLOW_TRACKING_URI) without modifying this config file.
env = dict(get_config("singleuser.extraEnv", {}))
env["HOME"] = "/home/jovyan"

nebi_remote_url = get_config("custom.nebi-remote-url", "")
if nebi_remote_url:
    env["NEBI_REMOTE_URL"] = nebi_remote_url

c.KubeSpawner.environment = env


# ---------------------------------------------------------------------------
# Keycloak token exchange helpers (synchronous, shared)
# ---------------------------------------------------------------------------
# These synchronous functions are the single implementation of the 3-step
# Keycloak → Nebi token exchange.  They are used by:
#   - _nebi_pre_spawn_hook (below) via asyncio.to_thread()
#   - 03-nebi-envs.py directly (jhub-apps calls conda_envs synchronously)
#
# Using urllib.request (not Tornado AsyncHTTPClient) so the same code works
# in both sync and async contexts.


def _extract_error_body(exc):
    """Extract HTTP response body from an exception for diagnostic logging.

    urllib.error.HTTPError exposes the body via .read(); other exceptions
    do not.  Returns an empty string if the body cannot be read.
    """
    if hasattr(exc, "read"):
        try:
            return exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
    return ""


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
        resp_body = _extract_error_body(exc)
        log.error(
            "Keycloak token refresh failed: %s response=%s (url=%s, client_id=%s)",
            exc, resp_body, keycloak_url, hub_client_id,
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
        resp_body = _extract_error_body(exc)
        log.error(
            "Keycloak token exchange failed: %s response=%s (url=%s, audience=%s, client_id=%s)",
            exc, resp_body, keycloak_url, nebi_client_id, hub_client_id,
        )
        return ""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevent urllib from following redirects (matches Tornado follow_redirects=False)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(newurl, code, msg, headers, fp)


def _sync_exchange_nebi_id_token_for_jwt(nebi_id_token, nebi_internal_url):
    """Exchange a Nebi-audience ID token for a Nebi JWT via the session endpoint.

    Uses a no-redirect opener so auth failures surface as errors instead of
    silently following a redirect to a login page.
    Returns the Nebi JWT string, or empty string on failure.
    """
    session_url = f"{nebi_internal_url.rstrip('/')}/api/v1/auth/session"
    req = Request(
        session_url,
        headers={"Cookie": f"IdToken={nebi_id_token}"},
        method="GET",
    )
    opener = urllib.request.build_opener(_NoRedirectHandler)
    try:
        with opener.open(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("token", "")
    except Exception as exc:
        resp_body = _extract_error_body(exc)
        log.error(
            "Nebi session exchange failed: %s response=%s (url=%s)",
            exc, resp_body, session_url,
        )
        return ""


def get_nebi_jwt(refresh_token, access_token, keycloak_url, nebi_cid, hub_cid, hub_secret, nebi_url):
    """Run the full 3-step token exchange and return a Nebi JWT.

    This is a synchronous, self-contained helper used by both the spawner hook
    (via asyncio.to_thread) and the jhub-apps environment listing callable
    (03-nebi-envs.py).

    Returns the Nebi JWT string, or empty string on any failure.
    """
    # Step 1: Refresh the access token (preferred) or use the existing one
    if refresh_token:
        access_token = _sync_refresh_access_token(
            refresh_token, keycloak_url, hub_cid, hub_secret,
        )
        if not access_token:
            return ""
    if not access_token:
        return ""

    # Step 2: Exchange access token for Nebi-audience ID token
    nebi_id_token = _sync_exchange_access_token_for_nebi_id_token(
        access_token, keycloak_url, nebi_cid, hub_cid, hub_secret,
    )
    if not nebi_id_token:
        return ""

    # Step 3: Exchange Nebi ID token for Nebi JWT
    return _sync_exchange_nebi_id_token_for_jwt(nebi_id_token, nebi_url)


# ---------------------------------------------------------------------------
# Nebi auto-authentication (pre-spawn hook)
# ---------------------------------------------------------------------------


async def _nebi_pre_spawn_hook(spawner):
    """Authenticate the user with the remote Nebi server at spawn time.

    Exchanges the user's Keycloak token for a Nebi JWT and injects it as
    NEBI_AUTH_TOKEN into the pod environment.
    Non-fatal: if any step fails, the pod still spawns without auto-auth.
    """
    # Tell jhub-app-proxy to use pixi activation (instead of conda) for app pods.
    # Set this first, before any early returns, because pixi activation is needed
    # regardless of whether the token exchange succeeds — the nebi binary in the
    # pod handles workspace pull and pixi env activation independently.
    spawner.environment = {**spawner.environment, "JHUB_APP_ENV_MANAGER": "pixi"}

    auth_state = await spawner.user.get_auth_state()
    if not auth_state:
        log.warning("No auth_state for %s, skipping Nebi auto-auth", spawner.user.name)
        return

    keycloak_url = get_config("custom.keycloak-token-url", "")
    nebi_cid = get_config("custom.nebi-client-id", "")
    hub_cid = get_config("custom.jupyterhub-client-id", "")
    hub_secret = os.environ.get("JUPYTERHUB_OIDC_CLIENT_SECRET", "")
    nebi_url = get_config("custom.nebi-internal-url", "")

    if not all([keycloak_url, nebi_cid, hub_cid, hub_secret, nebi_url]):
        log.warning("Nebi auto-auth not fully configured, skipping")
        return

    try:
        refresh_token = auth_state.get("refresh_token")
        access_token = auth_state.get("access_token") or ""

        if not refresh_token and not access_token:
            log.warning("No access_token or refresh_token for %s, skipping", spawner.user.name)
            return

        # Run the synchronous token exchange in a thread to avoid blocking
        # the Tornado event loop.
        nebi_jwt = await asyncio.to_thread(
            get_nebi_jwt,
            refresh_token, access_token,
            keycloak_url, nebi_cid, hub_cid, hub_secret, nebi_url,
        )
        if not nebi_jwt:
            log.warning("Nebi token exchange returned no JWT for %s", spawner.user.name)
            return

        spawner.environment = {**spawner.environment, "NEBI_AUTH_TOKEN": nebi_jwt}
        log.info("Nebi auto-auth succeeded for %s", spawner.user.name)
    except Exception:
        log.exception("Nebi auto-auth failed for %s (pod will still spawn)", spawner.user.name)


# Only register the hook when Nebi integration is configured.
if nebi_remote_url and get_config("custom.nebi-internal-url", ""):
    c.KubeSpawner.pre_spawn_hook = _nebi_pre_spawn_hook
