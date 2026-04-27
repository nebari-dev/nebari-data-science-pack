"""Smoke test: chart installs, hub serves /hub/login."""

import urllib.request


def test_hub_login_page(hub_url):
    with urllib.request.urlopen(f"{hub_url}/hub/login", timeout=5) as r:
        body = r.read().decode()
    assert r.status == 200
    assert "JupyterHub" in body
