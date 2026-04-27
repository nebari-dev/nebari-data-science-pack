"""HTTP client for JupyterHub against the test deployment.

The test harness needs to: log a user in, start their server, wait for
the pod, then stop the server cleanly. All four steps share cookie/XSRF
state, which is fiddly to manage with bare urllib.

`HubClient` owns one cookie session for the whole test and exposes a
small API. Internals (cookie jar, XSRF rotation, retry on 5xx, error
decoding) are hidden.
"""

import http.cookiejar
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest

log = logging.getLogger("e2e")


class HubClient:
    """One per test. Holds cookie state across login → spawn → stop."""

    def __init__(self, base_url):
        self.base = base_url.rstrip("/")
        self._jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._jar),
        )

    # ---- public API ----

    def login(self, username, password="x", retry_5xx_for=30):
        """POST /hub/login. Retries on 5xx (hub may be briefly unavailable
        right after a previous user pod is deleted)."""
        self._get("/hub/login")  # prime _xsrf cookie
        deadline = time.time() + retry_5xx_for
        while True:
            status, _, body = self._post(
                "/hub/login",
                data={"username": username, "password": password,
                      "_xsrf": self._xsrf()},
            )
            log.info("  login status=%d body[:120]=%r", status, body[:120])
            if status in (200, 302):
                return
            if status >= 500 and time.time() < deadline:
                log.info("  hub 5xx — retry in 2s")
                time.sleep(2)
                continue
            pytest.fail(f"login failed status={status}: {body}")

    def spawn(self, username):
        """POST /hub/api/users/<u>/server. Returns nothing — caller waits
        for the pod independently. 400 means already running (idempotent)."""
        status, _, body = self._post(
            f"/hub/api/users/{username}/server",
            headers={"X-XSRFToken": self._xsrf()},
        )
        log.info("  spawn status=%d body=%s", status, body)
        if status not in (201, 202, 400):
            pytest.fail(f"spawn failed status={status}: {body}")

    def stop(self, username):
        """DELETE /hub/api/users/<u>/server. Cleans up spawner state in the
        hub (a raw `kubectl delete pod` leaves the spawner pending and the
        next login returns 503)."""
        try:
            self._request(
                "DELETE", f"/hub/api/users/{username}/server",
                headers={"X-XSRFToken": self._xsrf()},
            )
        except urllib.error.HTTPError as e:
            log.warning("stop %s -> %d", username, e.code)

    # ---- internals ----

    def _xsrf(self):
        return next((c.value for c in self._jar if c.name == "_xsrf"), "")

    def _get(self, path):
        return self._request("GET", path)

    def _post(self, path, data=None, headers=None):
        return self._request("POST", path, data=data, headers=headers)

    def _request(self, method, path, data=None, headers=None):
        body = urllib.parse.urlencode(data).encode() if data else None
        req = urllib.request.Request(
            self.base + path, data=body, method=method,
            headers=headers or {},
        )
        try:
            r = self._opener.open(req, timeout=15)
            return r.status, dict(r.headers), r.read().decode(errors="replace")
        except urllib.error.HTTPError as e:
            payload = e.read().decode(errors="replace") if e.fp else ""
            return e.code, dict(e.headers or {}), payload
