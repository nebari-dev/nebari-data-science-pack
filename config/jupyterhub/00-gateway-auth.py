"""JupyterHub authenticator that does its own OAuth flow with Keycloak.

This module replaces the earlier EnvoyOIDCAuthenticator path where Envoy
Gateway acted as the OAuth client. Envoy v1.6 does not rotate cookie
contents on every request, so `auth_state` went stale for paths that
bypassed hub (e.g. `/services/japps/*`).

With this module, hub is the OAuth client. JupyterHub's built-in
refresh_user uses the stored refresh_token to keep auth_state fresh
without depending on browser cookies or gateway-injected headers.

The chart mounts the operator-created KC client Secret at
``/etc/oauth/`` (overridable via ``OAUTH_SECRET_DIR``); ``OAUTH_CALLBACK_URL``
and ``OAUTH_EXTERNAL_URL`` come from chart-rendered envs.
"""

# ruff: noqa: F821 - `c` is a magic global provided by JupyterHub

import json
import os
from pathlib import Path
from urllib.parse import urlencode

from oauthenticator.generic import GenericOAuthenticator
from oauthenticator.oauth2 import OAuthLogoutHandler
from tornado.httpclient import HTTPClientError


def _build_logout_url(
    *,
    end_session_url: str,
    id_token: str | None,
    post_logout_redirect_uri: str,
) -> str:
    """Build a KC end-session URL with id_token_hint + post_logout_redirect_uri.

    Keycloak v18+ rejects logout without ``id_token_hint`` when a
    ``post_logout_redirect_uri`` is also given. ``id_token`` may be None
    if the user's auth_state was never populated (legacy session); fall
    back to just the redirect.
    """
    params = {"post_logout_redirect_uri": post_logout_redirect_uri}
    if id_token:
        params["id_token_hint"] = id_token
    return f"{end_session_url}?{urlencode(params)}"


class KeyCloakLogoutHandler(OAuthLogoutHandler):
    """Bounce hub logout through Keycloak's end_session endpoint.

    KC requires ``id_token_hint`` when ``post_logout_redirect_uri`` is
    present. The token lives in the user's auth_state, so it must be
    read at request time. Override ``get`` (not ``render_logout_page``)
    because ``LogoutHandler.get`` clears ``self._jupyterhub_user`` BEFORE
    calling ``render_logout_page`` — by the time the latter runs,
    ``current_user`` is None and auth_state is unreachable.
    """

    async def get(self):
        user = self.current_user
        id_token = None
        if user is not None:
            try:
                auth_state = await user.get_auth_state()
                if auth_state:
                    id_token = auth_state.get("id_token")
            except Exception:
                self.log.warning(
                    "logout: failed reading auth_state for %s — proceeding "
                    "without id_token_hint", user.name, exc_info=True,
                )
        # Standard cleanup from base LogoutHandler.get (token revocation,
        # cookie clear, server shutdown).
        await self.default_handle_logout()
        await self.handle_logout()
        self._jupyterhub_user = None
        url = _build_logout_url(
            end_session_url=self.authenticator._kc_end_session_url,
            id_token=id_token,
            post_logout_redirect_uri=self.authenticator._kc_post_logout_redirect_uri,
        )
        self.redirect(url)


class KeyCloakOAuthenticator(GenericOAuthenticator):
    """Keycloak-flavoured GenericOAuthenticator.

    Swaps in :class:`KeyCloakLogoutHandler` via the ``logout_handler``
    class hook on :class:`oauthenticator.OAuthenticator`, which is what
    ``get_handlers`` reads when registering the ``/logout`` route.
    """

    logout_handler = KeyCloakLogoutHandler

    # Stashed by configure() so the logout handler can build URLs at request time.
    _kc_end_session_url: str = ""
    _kc_post_logout_redirect_uri: str = ""

    async def refresh_user(self, user, handler=None):
        """Run KC's refresh_token grant and persist rotated tokens to auth_state.

        JupyterHub's default Authenticator.refresh_user is a no-op (returns
        True), and GenericOAuthenticator doesn't override it. Result: the
        refresh_token stored in auth_state at OAuth-callback time stays
        frozen until KC's SSO idle timeout invalidates it (~30 min by
        default). The next sync caller — nebi-envs's 3-step exchange —
        then fails at step 1 with `invalid_grant: Token is not active`,
        env list returns [], and the Create-App Software Environment
        dropdown vanishes for the user.

        Contract (per JupyterHub Authenticator.refresh_user docstring):
          - return dict  -> JupyterHub merges these fields into auth_state
          - return True  -> auth_state is fine, leave it
          - return False -> auth_state is invalid, force re-login

        We always return a dict on a successful grant so KC's rotated
        refresh_token gets written back. On `invalid_grant` we return False
        to force re-auth (silent no-op would leave the session stale until
        next manual login). Transient errors keep the existing auth_state.
        """
        auth_state = await user.get_auth_state()
        if not auth_state or not auth_state.get("refresh_token"):
            return True

        body = urlencode({
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": auth_state["refresh_token"],
        })
        try:
            token_info = await self.httpfetch(
                self.token_url,
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                body=body,
            )
        except HTTPClientError as e:
            err_kind = ""
            if e.response is not None and e.response.body:
                try:
                    err_kind = json.loads(e.response.body).get("error", "")
                except Exception:
                    pass
            if e.code == 400 and err_kind == "invalid_grant":
                self.log.warning(
                    "KC refresh_token expired for %s — forcing re-login",
                    user.name,
                )
                return False
            self.log.warning(
                "KC refresh failed for %s: HTTP %s %s — keeping current auth_state",
                user.name, e.code, err_kind or e.message,
            )
            return True

        # Successful grant: KC returns a new access_token (always) and a
        # rotated refresh_token (when rotation enabled). Preserve any
        # auth_state keys we don't get back (e.g. oauth_user from
        # GenericOAuthenticator.authenticate's response).
        new_state = dict(auth_state)
        new_state["access_token"] = token_info["access_token"]
        if token_info.get("refresh_token"):
            new_state["refresh_token"] = token_info["refresh_token"]
        if token_info.get("id_token"):
            new_state["id_token"] = token_info["id_token"]
        new_state["token_response"] = token_info
        return {"auth_state": new_state}


def _kc_urls(issuer: str) -> dict:
    """Derive Keycloak OIDC endpoint URLs from the realm issuer URL."""
    base = f"{issuer}/protocol/openid-connect"
    return {
        "authorize_url": f"{base}/auth",
        "token_url": f"{base}/token",
        "userdata_url": f"{base}/userinfo",
        "end_session_url": f"{base}/logout",
    }


def configure(
    c,
    *,
    issuer: str,
    client_id: str,
    client_secret: str,
    callback_url: str,
    external_url: str,
    admin_groups=None,
):
    """Wire KeyCloakOAuthenticator onto JupyterHub's `c` config object."""
    urls = _kc_urls(issuer)
    c.JupyterHub.authenticator_class = KeyCloakOAuthenticator
    c.KeyCloakOAuthenticator.client_id = client_id
    c.KeyCloakOAuthenticator.client_secret = client_secret
    c.KeyCloakOAuthenticator.oauth_callback_url = callback_url
    c.KeyCloakOAuthenticator.authorize_url = urls["authorize_url"]
    c.KeyCloakOAuthenticator.token_url = urls["token_url"]
    c.KeyCloakOAuthenticator.userdata_url = urls["userdata_url"]
    c.KeyCloakOAuthenticator.username_claim = "preferred_username"
    # Explicit scopes — GenericOAuthenticator defaults to [] which omits the
    # scope param entirely; KC then issues a token without `openid` and
    # /userinfo returns 403 at token_to_user.
    c.KeyCloakOAuthenticator.scope = ["openid", "profile", "email", "groups"]
    c.KeyCloakOAuthenticator.claim_groups_key = "groups"
    c.KeyCloakOAuthenticator.admin_groups = set(admin_groups or ["admin"])
    # Persist tokens so refresh_user can use the stored refresh_token.
    c.KeyCloakOAuthenticator.enable_auth_state = True
    c.KeyCloakOAuthenticator.refresh_pre_spawn = True
    # Refresh ~1 min before KC's 5-min access-token TTL expires.
    c.KeyCloakOAuthenticator.auth_refresh_age = 240
    # Leave logout_redirect_url empty so LogoutHandler.get falls through
    # to render_logout_page (our subclass) instead of short-circuiting
    # to a static URL that can't include id_token_hint.
    c.KeyCloakOAuthenticator.logout_redirect_url = ""
    # Stash the pieces KeyCloakLogoutHandler.render_logout_page reads at
    # request time to build the per-user end-session URL. These are
    # plain class attributes (not traitlets), so set them directly on
    # the class instead of via `c.<Class>.<attr> = ...` — traitlets'
    # config-loader rejects unknown names with a warning and never
    # propagates the value.
    KeyCloakOAuthenticator._kc_end_session_url = urls["end_session_url"]
    KeyCloakOAuthenticator._kc_post_logout_redirect_uri = external_url
    # Skip hub's local /hub/login form — go straight to Keycloak's
    # authorize endpoint. One IdP, no point making the user click a
    # "Sign in with OAuth 2.0" button.
    c.Authenticator.auto_login = True
    # Any KC-authenticated user is admitted (matches prior EnvoyOIDC policy);
    # tighten via admin_groups / allowed_groups per-deploy if needed.
    c.Authenticator.allow_all = True


def _read_secret_file(secret_dir: Path, key: str) -> str:
    """Read a single value out of the operator-mounted KC client Secret."""
    return (secret_dir / key).read_text().strip()


# When loaded by JupyterHub, `c` is a magic global. On host imports (tests),
# `c` is undefined and the production wiring is skipped.
#
# Production wiring is gated TWICE:
#   1. `c` must exist (real JupyterHub run, not a host import).
#   2. `OAUTH_CALLBACK_URL` must be set (deployer opted into KC OAuth).
# Without (2), the chart's default authenticator (dummy) stays in place,
# so plain `kind` deploys come up without needing the operator Secret.
try:
    c  # type: ignore[used-before-def]
except NameError:
    pass
else:
    if os.environ.get("OAUTH_CALLBACK_URL"):
        _secret_dir = Path(os.environ.get("OAUTH_SECRET_DIR", "/etc/oauth"))
        configure(
            c,  # noqa: F821
            issuer=_read_secret_file(_secret_dir, "issuer-url"),
            client_id=_read_secret_file(_secret_dir, "client-id"),
            client_secret=_read_secret_file(_secret_dir, "client-secret"),
            callback_url=os.environ["OAUTH_CALLBACK_URL"],
            external_url=os.environ["OAUTH_EXTERNAL_URL"],
        )
