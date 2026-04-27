"""End-to-end test fixtures.

Composes the helpers from `_cluster`, `_hub`, and `_pod_observer` into
pytest fixtures. The deep modules hide everything fiddly (cookie jars,
kubelet polling, force-cleanup); this file should stay short.

Cluster reuse via env vars:
  KIND_CLUSTER=<name>  use an existing cluster (skip create + delete)
  KIND_KEEP=1          keep the cluster after a session that created it
"""

import logging
import os
import pathlib
import subprocess
import time
import urllib.error
import urllib.request

import pytest

from _cluster import (
    ensure_cluster,
    helm_install,
    patch_nfs_hosts_entry,
    require_binaries,
    teardown_cluster,
    wait_for_hub,
)
from _hub import HubClient
from _pod_observer import wait_for_pod_ready
from _process import NAMESPACE, kctl, kctl_out, step

log = logging.getLogger("e2e")

CLUSTER = os.environ.get("KIND_CLUSTER", "nbtest-e2e")
RELEASE = "ds"
HUB_LOCAL_PORT = 18000
TEST_VALUES = pathlib.Path(__file__).parent / "fixtures" / "test-values.yaml"


# ---------------------------------------------------------------------------
# Failure diagnostics
# ---------------------------------------------------------------------------


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Stash test outcome on the item so the diagnostics fixture can see
    whether the test failed."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(autouse=True)
def dump_diagnostics_on_failure(request):
    yield
    rep = getattr(request.node, "rep_call", None)
    if not (rep and rep.failed):
        return
    log.error("=" * 60)
    log.error("test failed: %s — dumping cluster diagnostics", request.node.name)
    log.error("=" * 60)
    kctl("get", "pods")
    kctl("get", "events", "--sort-by=.lastTimestamp")
    log.error("--- hub logs (tail 200) ---")
    kctl("logs", "-l", "component=hub", "--tail=200", check=False)
    log.error("--- singleuser pod logs ---")
    kctl("logs", "-l", "component=singleuser-server", "--tail=100",
         "--all-containers=true", "--prefix=true", check=False)


# ---------------------------------------------------------------------------
# Cluster + chart (session-scoped)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def cluster():
    TOTAL = 6
    step(1, TOTAL, "verify required binaries on PATH")
    require_binaries("kind", "helm", "kubectl")

    step(2, TOTAL, f"ensure kind cluster '{CLUSTER}'")
    created_here = ensure_cluster(CLUSTER)
    log.info("created_here=%s", created_here)

    step(3, TOTAL, "helm install (chart + test overrides)")
    helm_install(RELEASE, ".", TEST_VALUES)

    step(4, TOTAL, "kind workaround: NFS svc FQDN -> /etc/hosts")
    patch_nfs_hosts_entry(RELEASE, CLUSTER)

    step(5, TOTAL, "snapshot post-install resources")
    kctl("get", "all,pvc,configmap")

    step(6, TOTAL, "wait for hub + proxy ready")
    wait_for_hub()

    yield CLUSTER

    if created_here and not os.environ.get("KIND_KEEP"):
        log.info("deleting cluster %s", CLUSTER)
        teardown_cluster(CLUSTER)


# ---------------------------------------------------------------------------
# Per-test: port-forward + hub session
# ---------------------------------------------------------------------------


@pytest.fixture
def hub_url(cluster):
    """Port-forward proxy-public; yield base URL; tear down."""
    log.info("port-forward svc/proxy-public -> :%d", HUB_LOCAL_PORT)
    pf = subprocess.Popen(
        ["kubectl", "port-forward", "svc/proxy-public",
         f"{HUB_LOCAL_PORT}:80", "-n", NAMESPACE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://localhost:{HUB_LOCAL_PORT}"
    try:
        _wait_for_url(f"{base}/hub/login", timeout_s=30)
        log.info("port-forward ready at %s", base)
        yield base
    finally:
        log.info("closing port-forward")
        pf.terminate()
        pf.wait(timeout=5)


def _wait_for_url(url, timeout_s):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except (urllib.error.URLError, ConnectionResetError):
            time.sleep(0.5)
    pytest.fail(f"{url} never became reachable")


# ---------------------------------------------------------------------------
# Per-test: spawn a singleuser pod
# ---------------------------------------------------------------------------


class SpawnedUser:
    """Handle to a logged-in JupyterHub user with a running singleuser pod."""

    def __init__(self, login_name, real_user, pod):
        self.login_name = login_name   # e.g. "alice-data" (form input)
        self.user = real_user          # e.g. "alice"      (auth-resolved)
        self.pod = pod                 # k8s pod name

    def exec(self, *cmd, user=None):
        """Run a command inside the notebook container. Returns (rc, out)."""
        flags = ["-n", NAMESPACE, self.pod, "-c", "notebook", "--"]
        if user:
            return _kubectl_exec(*flags, "su", "-", user, "-c", " ".join(cmd))
        return _kubectl_exec(*flags, *cmd)


def _kubectl_exec(*args):
    cp = subprocess.run(["kubectl", "exec", *args],
                        capture_output=True, text=True)
    return cp.returncode, (cp.stdout or "") + (cp.stderr or "")


@pytest.fixture
def spawn_user(hub_url):
    """Factory: log in + start a singleuser pod for a username convention.

    Username 'alice-data-ml' → User(name='alice', groups=['data','ml']).
    Pods are stopped via the JupyterHub API in teardown.
    """
    client = HubClient(hub_url)
    spawned: list[SpawnedUser] = []

    def _spawn(login_name):
        SPAWN_STEPS = 3
        step(1, SPAWN_STEPS, f"login as {login_name}")
        client.login(login_name)

        real_user = login_name.split("-")[0]
        step(2, SPAWN_STEPS, f"spawn server for {real_user}")
        client.spawn(real_user)

        step(3, SPAWN_STEPS, f"wait for pod ready (user={real_user})")
        pod = _wait_for_pod_to_appear(real_user)
        wait_for_pod_ready(pod)

        u = SpawnedUser(login_name, real_user, pod)
        spawned.append(u)
        return u

    yield _spawn

    for u in spawned:
        log.info("stopping server for %s via /hub/api", u.user)
        client.stop(u.user)


def _wait_for_pod_to_appear(real_user, timeout_s=60):
    """Wait for the singleuser pod object to be created (named by hub)."""
    label = f"hub.jupyter.org/username={real_user}"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        rc, name, _ = kctl_out(
            "get", "pods", "-l", label,
            "-o", "jsonpath={.items[0].metadata.name}",
        )
        if rc == 0 and name:
            return name
        time.sleep(2)
    pytest.fail(f"pod for user {real_user} never appeared")
