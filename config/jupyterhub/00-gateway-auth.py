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
        # Find the IdToken cookie (Envoy uses IdToken-<suffix>)
        id_token = None
        for name, value in handler.request.cookies.items():
            if name.startswith("IdToken"):
                id_token = value.value
                break

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

        return username


if get_config("custom.external-url", ""):
    c.JupyterHub.authenticator_class = EnvoyOIDCAuthenticator
    # All users who pass Keycloak auth at the gateway are allowed
    c.Authenticator.allow_all = True
