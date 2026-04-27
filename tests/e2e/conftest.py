"""k3d + helm fixtures for end-to-end tests.

Reuses an existing cluster if `K3D_CLUSTER` is set (fast iteration),
otherwise creates a throwaway one named `nbtest-e2e`.
"""

import logging
import os
import shutil
import subprocess
import time

import pytest
import urllib.request
import urllib.error

log = logging.getLogger(__name__)

CLUSTER = os.environ.get("K3D_CLUSTER", "nbtest-e2e")
RELEASE = "ds"
NAMESPACE = "default"
HUB_LOCAL_PORT = 18000


def _run(*args, check=True, capture=False):
    """Run a subprocess. Streams stdout/stderr live via logging."""
    log.info("$ %s", " ".join(args))
    if capture:
        cp = subprocess.run(args, check=check, capture_output=True, text=True)
        for line in (cp.stdout or "").splitlines():
            log.info("    %s", line)
        for line in (cp.stderr or "").splitlines():
            log.warning("    %s", line)
        return cp
    proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in proc.stdout:
        log.info("    %s", line.rstrip())
    rc = proc.wait()
    if check and rc != 0:
        raise subprocess.CalledProcessError(rc, args)
    return subprocess.CompletedProcess(args, rc)


def _require(binary):
    if not shutil.which(binary):
        pytest.exit(f"{binary} not found on PATH", returncode=2)


def _cluster_exists(name):
    cp = _run("k3d", "cluster", "list", "-o", "json",
              check=False, capture=True)
    return f'"name":"{name}"' in cp.stdout


def _wait_for_hub(timeout_s, poll_s):
    """Poll until hub + proxy pods are Ready."""
    deadline = time.time() + timeout_s
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        elapsed = int(timeout_s - (deadline - time.time()))
        log.info("hub-wait attempt=%d elapsed=%ds", attempt, elapsed)
        _run("kubectl", "get", "pods", "-n", NAMESPACE,
             check=False, capture=True)
        _run("kubectl", "logs", "-n", NAMESPACE, "-l", "component=hub",
             "--tail=5", check=False, capture=True)
        hub = _run("kubectl", "wait", "--for=condition=ready", "pod",
                   "-l", "component=hub", "-n", NAMESPACE,
                   "--timeout=2s", check=False, capture=True)
        proxy = _run("kubectl", "wait", "--for=condition=ready", "pod",
                     "-l", "component=proxy", "-n", NAMESPACE,
                     "--timeout=2s", check=False, capture=True)
        if hub.returncode == 0 and proxy.returncode == 0:
            log.info("hub+proxy ready after %ds", elapsed)
            return
        time.sleep(poll_s)
    log.error("timeout after %ds; dumping last 200 hub log lines", timeout_s)
    _run("kubectl", "logs", "-n", NAMESPACE, "-l", "component=hub",
         "--tail=200", check=False, capture=True)
    pytest.fail(f"hub/proxy not ready within {timeout_s}s")


@pytest.fixture(scope="session")
def cluster():
    for b in ("k3d", "helm", "kubectl"):
        _require(b)

    created_here = False
    if not _cluster_exists(CLUSTER):
        log.info("creating k3d cluster %s", CLUSTER)
        _run("k3d", "cluster", "create", CLUSTER, "--wait")
        created_here = True
    else:
        log.info("reusing existing cluster %s", CLUSTER)

    _run("helm", "dependency", "update")
    _run("helm", "upgrade", "--install", RELEASE, ".",
         "--namespace", NAMESPACE,
         "--set", "nebariapp.enabled=false")

    _wait_for_hub(timeout_s=300, poll_s=5)

    yield CLUSTER

    if created_here and not os.environ.get("K3D_KEEP"):
        log.info("deleting cluster %s", CLUSTER)
        _run("k3d", "cluster", "delete", CLUSTER, check=False)


@pytest.fixture
def hub_url(cluster):
    """Port-forward proxy-public, yield base URL, tear down."""
    log.info("port-forward svc/proxy-public -> :%d", HUB_LOCAL_PORT)
    pf = subprocess.Popen(
        ["kubectl", "port-forward", "svc/proxy-public",
         f"{HUB_LOCAL_PORT}:80", "-n", NAMESPACE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://localhost:{HUB_LOCAL_PORT}"
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"{base}/hub/login", timeout=2) as r:
                    if r.status == 200:
                        break
            except (urllib.error.URLError, ConnectionResetError):
                time.sleep(0.5)
        else:
            pytest.fail("port-forward never became reachable")
        log.info("port-forward ready at %s", base)
        yield base
    finally:
        log.info("closing port-forward")
        pf.terminate()
        pf.wait(timeout=5)
