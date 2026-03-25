"""Authenticator for Envoy Gateway OIDC.

When Envoy Gateway handles OIDC authentication, it stores the ID token
in a cookie (IdToken-<suffix>). This authenticator reads that cookie,
decodes the JWT, and extracts the username — so users are automatically
logged into JupyterHub after authenticating with Keycloak at the gateway.
"""

# ruff: noqa: F821 - `c` is a magic global provided by JupyterHub

import base64
import json

from jupyterhub.auth import Authenticator
from z2jh import get_config


class EnvoyOIDCAuthenticator(Authenticator):
    """Authenticate users from Envoy Gateway's OIDC IdToken cookie."""

    auto_login = True

    async def authenticate(self, handler, data=None):
        # Envoy Gateway stores two tokens as cookies after OIDC authentication:
        #
        # IdToken (IdToken-<suffix>):
        #   JWT containing user identity claims (sub, email, groups, etc.).
        #   The `aud` claim is set to THIS client (JupyterHub's Keycloak client).
        #   Used here to extract the username and groups.
        #
        # AccessToken (AccessToken-<suffix>):
        #   Credential for accessing resources. Can be exchanged at Keycloak's
        #   token endpoint (RFC 8693) for a token with a different audience —
        #   e.g., exchanging a JupyterHub access token for a Nebi ID token.
        #   Stored in auth_state for the spawner's pre_spawn_hook to use.
        #
        # RefreshToken (RefreshToken-<suffix>):
        #   Long-lived token for obtaining fresh access tokens. Access tokens
        #   expire in minutes, so the pre_spawn_hook uses the refresh token
        #   to get a fresh access token before doing the exchange.
        id_token = None
        access_token = None
        refresh_token = None
        for name, value in handler.request.cookies.items():
            if name.startswith("IdToken"):
                id_token = value.value
            elif name.startswith("AccessToken"):
                access_token = value.value
            elif name.startswith("RefreshToken"):
                refresh_token = value.value

        if not id_token:
            self.log.warning("No IdToken cookie found")
            return None

        try:
            # Decode JWT payload without verification — Envoy already validated it
            payload_b64 = id_token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload_b64))
        except Exception:
            self.log.exception("Failed to decode IdToken JWT")
            return None

        username = claims.get("preferred_username") or claims.get("sub")
        if not username:
            self.log.warning("No username claim in IdToken: %s", list(claims.keys()))
            return None

        # Extract groups from the token (set by the "groups" scope / group mapper)
        groups = claims.get("groups", [])
        # Keycloak returns groups as paths (e.g. "/admin"), strip leading slash
        groups = [g.strip("/") for g in groups]

        # Determine admin from group membership
        admin_groups = set(get_config("custom.admin-groups", ["admin"]))
        is_admin = bool(admin_groups & set(groups))

        return {
            "name": username,
            "admin": is_admin,
            "groups": groups,
            "auth_state": {
                "id_token": id_token,
                "access_token": access_token,
                "refresh_token": refresh_token,
            },
        }


if get_config("custom.external-url", ""):
    c.JupyterHub.authenticator_class = EnvoyOIDCAuthenticator
    # All users who pass Keycloak auth at the gateway are allowed
    c.Authenticator.allow_all = True
    c.Authenticator.enable_auth_state = True
