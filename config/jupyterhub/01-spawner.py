"""KubeSpawner configuration."""
# ruff: noqa: F821 - `c` is a magic global provided by JupyterHub

import json
import logging
import os
from urllib.parse import urlencode

from tornado.httpclient import AsyncHTTPClient, HTTPRequest
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
# Nebi auto-authentication (Keycloak token exchange, RFC 8693)
# ---------------------------------------------------------------------------
# At spawn time, exchange the user's JupyterHub access token for a
# Nebi-audience ID token via Keycloak, then convert that into a Nebi JWT.
#
# Why token exchange? The IdToken in auth_state has aud=jupyterhub-client,
# but Nebi's session endpoint only accepts tokens with aud=nebi-client.
# Token exchange lets Keycloak issue a new ID token for the correct audience.


async def _refresh_access_token(refresh_token, keycloak_url, hub_client_id, hub_client_secret):
    """Use the refresh token to get a fresh access token from Keycloak.

    Access tokens expire in minutes. The refresh token (stored in auth_state
    from Envoy's RefreshToken cookie) has a much longer lifetime and can be
    used to obtain a fresh access token without user interaction.

    Returns the new access token string, or None on failure.
    """
    body = urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": hub_client_id,
        "client_secret": hub_client_secret,
    })
    try:
        resp = await AsyncHTTPClient().fetch(HTTPRequest(
            keycloak_url,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            body=body,
            request_timeout=10,
        ))
    except Exception as exc:
        resp_body = getattr(exc, "response", None)
        if resp_body is not None:
            resp_body = resp_body.body.decode() if resp_body.body else ""
        log.error("Keycloak token refresh error: %s response=%s", exc, resp_body)
        raise
    return json.loads(resp.body).get("access_token", "")


async def _exchange_access_token_for_nebi_id_token(
    access_token, keycloak_url, nebi_client_id, hub_client_id, hub_client_secret,
):
    """Exchange a JupyterHub access token for a Nebi-audience ID token via Keycloak.

    The access token proves the user is authenticated. Keycloak validates it
    and issues a new ID token with aud=nebi-client-id.

    Returns the Nebi ID token string, or None on failure.
    """
    body = urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": access_token,
        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "audience": nebi_client_id,
        "client_id": hub_client_id,
        "client_secret": hub_client_secret,
    })
    try:
        resp = await AsyncHTTPClient().fetch(HTTPRequest(
            keycloak_url,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            body=body,
            request_timeout=10,
        ))
    except Exception as exc:
        resp_body = getattr(exc, "response", None)
        if resp_body is not None:
            resp_body = resp_body.body.decode() if resp_body.body else ""
        log.error("Keycloak token exchange error: %s response=%s", exc, resp_body)
        raise
    data = json.loads(resp.body)
    # Prefer id_token if present (has user identity claims), fall back to access_token
    return data.get("id_token") or data.get("access_token", "")


async def _exchange_nebi_id_token_for_jwt(nebi_id_token, nebi_internal_url):
    """Exchange a Nebi-audience ID token for a Nebi JWT via the session endpoint.

    Nebi verifies the ID token (aud must match nebi-client-id), finds/creates
    the user, syncs roles from groups, and returns a Nebi JWT (24h expiry).

    Returns the Nebi JWT string, or None on failure.
    """
    session_url = f"{nebi_internal_url.rstrip('/')}/api/v1/auth/session"
    resp = await AsyncHTTPClient().fetch(HTTPRequest(
        session_url,
        method="GET",
        headers={"Cookie": f"IdToken={nebi_id_token}"},
        request_timeout=10,
        follow_redirects=False,
    ))
    return json.loads(resp.body).get("token", "")


async def _nebi_pre_spawn_hook(spawner):
    """Authenticate the user with the remote Nebi server at spawn time.

    Reads the Keycloak access token from auth_state, exchanges it for a
    Nebi JWT, and injects it as NEBI_AUTH_TOKEN into the pod environment.
    Non-fatal: if any step fails, the pod still spawns without auto-auth.
    """
    auth_state = await spawner.user.get_auth_state()
    if not auth_state:
        log.warning("No auth_state for %s, skipping Nebi auto-auth", spawner.user.name)
        return

    keycloak_url = get_config("custom.keycloak-token-url", "")
    nebi_cid = get_config("custom.nebi-client-id", "")
    hub_cid = get_config("custom.jupyterhub-client-id", "")
    # Read from env var (mounted from K8s secret) to avoid plaintext in Helm values.
    hub_secret = os.environ.get("JUPYTERHUB_OIDC_CLIENT_SECRET", "")
    nebi_url = get_config("custom.nebi-internal-url", "")

    if not all([keycloak_url, nebi_cid, hub_cid, hub_secret, nebi_url]):
        log.warning("Nebi auto-auth not fully configured, skipping")
        return

    try:
        # Refresh the access token first — it expires in minutes, but the
        # refresh token (from Envoy's RefreshToken cookie) lasts much longer.
        access_token = auth_state.get("access_token") or ""
        refresh_token = auth_state.get("refresh_token")
        if refresh_token:
            access_token = await _refresh_access_token(
                refresh_token, keycloak_url, hub_cid, hub_secret,
            )
            if not access_token:
                log.warning("Token refresh returned no access token for %s", spawner.user.name)
                return
        elif not access_token:
            log.warning("No access_token or refresh_token for %s, skipping", spawner.user.name)
            return

        nebi_id_token = await _exchange_access_token_for_nebi_id_token(
            access_token, keycloak_url, nebi_cid, hub_cid, hub_secret,
        )
        if not nebi_id_token:
            log.warning("Keycloak token exchange returned no token for %s", spawner.user.name)
            return

        nebi_jwt = await _exchange_nebi_id_token_for_jwt(nebi_id_token, nebi_url)
        if not nebi_jwt:
            log.warning("Nebi session returned no token for %s", spawner.user.name)
            return

        spawner.environment = {**spawner.environment, "NEBI_AUTH_TOKEN": nebi_jwt}
        log.info("Nebi auto-auth succeeded for %s", spawner.user.name)
    except Exception:
        log.exception("Nebi auto-auth failed for %s (pod will still spawn)", spawner.user.name)


# Only register the hook when Nebi integration is configured.
if nebi_remote_url and get_config("custom.nebi-internal-url", ""):
    c.KubeSpawner.pre_spawn_hook = _nebi_pre_spawn_hook
