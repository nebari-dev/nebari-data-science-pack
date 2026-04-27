"""kind + helm fixtures for end-to-end tests.

Reuses an existing cluster if `KIND_CLUSTER` is set (fast iteration),
otherwise creates a throwaway one named `nbtest-e2e`.
"""

import http.cookiejar
import json
import logging
import os
import pathlib
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
import urllib.error

import pytest

log = logging.getLogger(__name__)


def _step(n, total, msg):
    log.info("──── [%d/%d] %s ────", n, total, msg)

CLUSTER = os.environ.get("KIND_CLUSTER", "nbtest-e2e")
RELEASE = "ds"
NAMESPACE = "default"
HUB_LOCAL_PORT = 18000
TEST_VALUES = pathlib.Path(__file__).parent / "fixtures" / "test-values.yaml"


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
    cp = _run("kind", "get", "clusters", check=False, capture=True)
    return name in (cp.stdout or "").splitlines()


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


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Stash test outcome on the item so fixtures can detect failures."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(autouse=True)
def dump_diagnostics_on_failure(request):
    """If the test fails, dump hub logs + pods + events for debugging."""
    yield
    rep = getattr(request.node, "rep_call", None)
    if not (rep and rep.failed):
        return
    log.error("=" * 60)
    log.error("test failed: %s — dumping cluster diagnostics", request.node.name)
    log.error("=" * 60)
    _run("kubectl", "get", "pods", "-n", NAMESPACE,
         check=False, capture=True)
    _run("kubectl", "get", "events", "-n", NAMESPACE,
         "--sort-by=.lastTimestamp", check=False, capture=True)
    log.error("--- hub logs (tail 200) ---")
    _run("kubectl", "logs", "-n", NAMESPACE, "-l", "component=hub",
         "--tail=200", check=False, capture=True)
    log.error("--- singleuser pod logs (any user) ---")
    _run("kubectl", "logs", "-n", NAMESPACE,
         "-l", "component=singleuser-server", "--tail=100",
         "--all-containers=true", "--prefix=true",
         check=False, capture=True)


def _patch_nfs_pv_to_cluster_ip():
    """Add the NFS service FQDN to the kind node's /etc/hosts.

    kind nodes' host /etc/resolv.conf only knows Docker DNS, so `mount.nfs`
    (which runs in the host mount namespace) can't resolve cluster-internal
    FQDNs. Patching the PV's `nfs.server` to the IP would work but is
    rejected as immutable once the PV is Bound. Adding a hosts entry on
    each kind node bypasses DNS entirely and works post-bind.
    Production clusters don't need this — their kubelets have cluster DNS.
    """
    rc, pv_name, _ = _kctl(
        "get", "pv", "-l",
        f"app.kubernetes.io/instance={RELEASE}",
        "-o", "jsonpath={.items[?(@.spec.nfs)].metadata.name}",
    )
    pv_name = pv_name.strip()
    if not pv_name:
        log.info("no NFS-backed PV found — skipping hosts entry")
        return

    rc, fqdn, _ = _kctl(
        "get", "pv", pv_name,
        "-o", "jsonpath={.spec.nfs.server}",
    )
    fqdn = fqdn.strip()
    svc_name = fqdn.split(".", 1)[0]
    rc, svc_ip, err = _kctl(
        "get", "svc", svc_name,
        "-o", "jsonpath={.spec.clusterIP}",
    )
    svc_ip = svc_ip.strip()
    if not svc_ip:
        log.error("could not resolve NFS svc %s ClusterIP: %s", svc_name, err)
        return

    # Add to each kind node's /etc/hosts (idempotent: skip if already there).
    cp = subprocess.run(
        ["kind", "get", "nodes", "--name", CLUSTER],
        capture_output=True, text=True, check=True,
    )
    for node in cp.stdout.strip().splitlines():
        cmd = (f"grep -q '{fqdn}$' /etc/hosts || "
               f"echo '{svc_ip} {fqdn}' >> /etc/hosts")
        log.info("hosts entry on %s: %s -> %s", node, fqdn, svc_ip)
        subprocess.run(["docker", "exec", node, "sh", "-c", cmd], check=True)


@pytest.fixture(scope="session")
def cluster():
    TOTAL = 7
    _step(1, TOTAL, "verify required binaries on PATH")
    for b in ("kind", "helm", "kubectl"):
        _require(b)

    created_here = False
    if not _cluster_exists(CLUSTER):
        _step(2, TOTAL, f"create kind cluster '{CLUSTER}'")
        _run("kind", "create", "cluster", "--name", CLUSTER, "--wait", "60s")
        created_here = True
    else:
        _step(2, TOTAL, f"reuse existing kind cluster '{CLUSTER}'")
        # `kind delete` can wipe the kubeconfig entry while leaving the
        # container; re-export to make sure the context is wired up.
        _run("kind", "export", "kubeconfig", "--name", CLUSTER,
             check=True, capture=True)

    _step(3, TOTAL, "helm dependency update")
    _run("helm", "dependency", "update")

    _step(4, TOTAL, "helm install (chart + test overrides)")
    _t = time.time()
    _run("helm", "upgrade", "--install", RELEASE, ".",
         "--namespace", NAMESPACE,
         "--set", "nebariapp.enabled=false",
         "--values", str(TEST_VALUES))
    log.info("helm install completed in %ds", int(time.time() - _t))

    _step(5, TOTAL, "patch NFS PV server field to ClusterIP (kind workaround)")
    _patch_nfs_pv_to_cluster_ip()

    _step(6, TOTAL, "snapshot post-install resources")
    _run("kubectl", "get", "all,pvc,configmap", "-n", NAMESPACE,
         check=False, capture=True)

    _step(7, TOTAL, "wait for hub + proxy ready")
    _wait_for_hub(timeout_s=300, poll_s=5)

    yield CLUSTER

    if created_here and not os.environ.get("KIND_KEEP"):
        log.info("deleting cluster %s", CLUSTER)
        cp = _run("kind", "delete", "cluster", "--name", CLUSTER, check=False,
                  capture=True)
        if cp.returncode != 0:
            # Docker Desktop occasionally fails to kill a container with
            # active mounts. Force-remove orphan node containers so the next
            # run starts clean.
            log.warning("kind delete failed; force-removing node containers")
            cp2 = subprocess.run(
                ["docker", "ps", "-a", "--filter",
                 f"name={CLUSTER}-", "--format", "{{.Names}}"],
                capture_output=True, text=True,
            )
            for name in (cp2.stdout or "").strip().splitlines():
                # `docker stop` first with timeout=0 (SIGKILL immediately),
                # then rm -f. Avoids the "did not receive an exit event" hang.
                subprocess.run(
                    ["docker", "stop", "--time=0", name],
                    capture_output=True,
                )
                subprocess.run(
                    ["docker", "rm", "-f", "-v", name],
                    capture_output=True,
                )
            subprocess.run(
                ["docker", "network", "rm", f"kind"],
                capture_output=True,
            )


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


class SpawnedUser:
    """Handle to a logged-in JupyterHub user with a running singleuser pod."""

    def __init__(self, login_name, real_user, pod):
        self.login_name = login_name   # e.g. "alice-data" (sent to /hub/login)
        self.user = real_user          # e.g. "alice" (authenticator-resolved)
        self.pod = pod                 # k8s pod name

    def exec(self, *cmd, user=None):
        """Run a command inside the singleuser pod, return (rc, stdout)."""
        flags = ["-n", NAMESPACE, self.pod, "-c", "notebook", "--"]
        if user:
            return _kexec(*flags, "su", "-", user, "-c", " ".join(cmd))
        return _kexec(*flags, *cmd)


def _kexec(*args):
    cp = subprocess.run(
        ["kubectl", "exec", *args],
        capture_output=True, text=True,
    )
    # Concatenate stderr after stdout for diagnostics on failure but the
    # primary signal (return code, stdout) is what the test asserts on.
    out = (cp.stdout or "") + (cp.stderr or "")
    return cp.returncode, out


def _login_and_spawn(base, login_name, timeout_s=180):
    """POST /hub/login + start server + wait for pod ready. Returns SpawnedUser."""
    SPAWN_TOTAL = 4
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar),
    )

    def _xsrf():
        for c in jar:
            if c.name == "_xsrf":
                return c.value
        return ""

    def _request(method, path, data=None, headers=None):
        url = base + path
        body = urllib.parse.urlencode(data).encode() if data else None
        req = urllib.request.Request(url, data=body, method=method,
                                     headers=headers or {})
        try:
            r = opener.open(req, timeout=15)
            payload = r.read().decode(errors="replace")
            return r.status, dict(r.headers), payload
        except urllib.error.HTTPError as e:
            payload = e.read().decode(errors="replace") if e.fp else ""
            return e.code, dict(e.headers or {}), payload

    # 1. Prime _xsrf cookie
    _step(1, SPAWN_TOTAL, "GET /hub/login (prime _xsrf cookie)")
    status, _, _ = _request("GET", "/hub/login")
    log.info("  status=%d cookies=%s", status, [c.name for c in jar])

    # 2. Login (DummyAuthenticator accepts any password). Retry on 5xx — the
    #    hub briefly returns 503 right after a previous user pod is deleted
    #    while it cleans up the spawner state.
    _step(2, SPAWN_TOTAL, f"POST /hub/login (as {login_name})")
    deadline = time.time() + 30
    while True:
        status, _, body = _request(
            "POST", "/hub/login",
            data={"username": login_name, "password": "x", "_xsrf": _xsrf()},
        )
        log.info("  status=%d body[:200]=%r", status, body[:200])
        if status in (200, 302):
            break
        if status >= 500 and time.time() < deadline:
            log.info("  retrying after 5xx in 2s")
            time.sleep(2)
            continue
        pytest.fail(f"login failed status={status}: {body}")

    # 3. Start the server
    real_user = login_name.split("-")[0]
    _step(3, SPAWN_TOTAL, f"POST /hub/api/users/{real_user}/server")
    status, headers, body = _request(
        "POST", f"/hub/api/users/{real_user}/server",
        headers={"X-XSRFToken": _xsrf()},
    )
    log.info("  status=%d body=%s", status, body)
    if status not in (201, 202, 400):  # 400 = already running
        log.error("spawn POST returned %d", status)
        log.error("  response headers: %s", headers)
        log.error("  response body: %s", body)
        log.error("  request cookies: %s", [c.name for c in jar])
        pytest.fail(f"spawn POST returned {status}: {body}")

    # 4. Wait for pod ready
    pod_label = f"hub.jupyter.org/username={real_user}"
    _step(4, SPAWN_TOTAL, f"wait for pod with label {pod_label}")
    deadline = time.time() + timeout_s
    pod_name = None
    while time.time() < deadline:
        cp = _run("kubectl", "get", "pods", "-n", NAMESPACE,
                  "-l", pod_label, "-o", "jsonpath={.items[0].metadata.name}",
                  check=False, capture=True)
        if cp.returncode == 0 and cp.stdout.strip():
            pod_name = cp.stdout.strip()
            break
        time.sleep(2)
    if not pod_name:
        pytest.fail(f"pod for user {real_user} never appeared")

    _wait_for_pod_ready(pod_name, timeout_s=timeout_s, poll_s=5)
    return SpawnedUser(login_name, real_user, pod_name)


_INIT_CONTAINERS = ("block-cloud-metadata", "initialize-shared-mounts")


def _kctl(*args, timeout=10):
    """Quiet kubectl helper that returns trimmed stdout (no live logging)."""
    cp = subprocess.run(["kubectl", *args, "-n", NAMESPACE],
                        capture_output=True, text=True, timeout=timeout)
    return cp.returncode, (cp.stdout or "").strip(), (cp.stderr or "").strip()


def _wait_for_pod_ready(pod_name, timeout_s, poll_s):
    """Poll pod state until Ready, surfacing every observable kubelet signal.

    Each cycle logs:
      - one-line pod summary (phase, container/init readiness)
      - new events since the last poll (image pull, FailedMount, scheduling…)
      - nfs-client-installer DaemonSet phase (PR #30 prereq for NFS)
      - tail of any init/notebook container logs that have started
    """
    deadline = time.time() + timeout_s
    attempt = 0
    seen_events: set[str] = set()
    seen_log_lines: dict[str, set[str]] = {c: set() for c in _INIT_CONTAINERS}
    while time.time() < deadline:
        attempt += 1
        elapsed = int(timeout_s - (deadline - time.time()))
        log.info("=== pod-wait %s attempt=%d elapsed=%ds ===",
                 pod_name, attempt, elapsed)

        # 1. Pod summary
        rc, out, _ = _kctl("get", "pod", pod_name, "--no-headers")
        if rc == 0:
            log.info("    pod: %s", out)
        else:
            log.warning("    pod not found yet")

        # 2. Per-container state (more readable than jsonpath blob)
        rc, out, _ = _kctl(
            "get", "pod", pod_name, "-o",
            "jsonpath={range .status.initContainerStatuses[*]}"
            "init/{.name} ready={.ready} state={.state}{'\\n'}{end}"
            "{range .status.containerStatuses[*]}"
            "main/{.name} ready={.ready} state={.state}{'\\n'}{end}",
        )
        for line in out.splitlines():
            log.info("    %s", line)

        # 3. Pod events from kubectl describe (canonical, with aggregation).
        #    Dedup on (Type, Reason, Message) — drop the Age column which
        #    keeps changing and breaks naive string-equality dedup.
        rc, out, _ = _kctl("describe", "pod", pod_name, timeout=10)
        in_events = False
        for raw in out.splitlines():
            stripped = raw.strip()
            if raw.startswith("Events:"):
                in_events = True; continue
            if raw and not raw.startswith(" "):
                in_events = False
            if not (in_events and stripped):
                continue
            if stripped.startswith("Type") or stripped.startswith("----"):
                continue
            # describe-pod event row: "Type   Reason   Age   From   Message"
            # Drop column index 2 (Age) for stable dedup.
            cols = stripped.split(None, 4)
            key = (cols[0], cols[1], cols[3] if len(cols) > 3 else "",
                   cols[4] if len(cols) > 4 else "")
            if key in seen_events:
                continue
            seen_events.add(key)
            log.info("    event: %s", stripped)

        # 4. Node-level kubelet logs (the deepest signal: NFS mount attempts,
        #    image pull progress, container exec). kind nodes are docker
        #    containers; journalctl is available inside.
        rc, out, _ = _kctl(
            "get", "pod", pod_name, "-o", "jsonpath={.spec.nodeName}",
        )
        if out:
            node = out.strip()
            cp = subprocess.run(
                ["docker", "exec", node, "journalctl", "-u", "kubelet",
                 "--since", "8 seconds ago", "--no-pager", "-q",
                 "-o", "cat"],
                capture_output=True, text=True, timeout=5,
            )
            for line in (cp.stdout or "").splitlines():
                # Filter to lines that mention this pod's name or its uid.
                if pod_name in line or "FailedMount" in line or "MountVolume" in line:
                    if line in seen_events:
                        continue
                    seen_events.add(line)
                    log.info("    kubelet: %s", line)

        # 4. NFS client installer DaemonSet status + init-container logs.
        #    The "1/1 Running" we see is the pause container — the actual
        #    apt-install runs in an init container; failures hide unless
        #    we tail its logs.
        rc, out, _ = _kctl(
            "get", "pods", "-l",
            "app.kubernetes.io/component=nfs-client-installer",
            "--no-headers",
        )
        if out:
            log.info("    nfs-installer: %s", out)
            for installer_pod in (line.split()[0] for line in out.splitlines()):
                rc2, init_log, _ = _kctl(
                    "logs", installer_pod, "-c", "install-nfs-common",
                    "--tail=20", timeout=5,
                )
                if rc2 == 0:
                    for line in (init_log or "").splitlines():
                        key = ("installer-log", line)
                        if key in seen_events:
                            continue
                        seen_events.add(key)
                        log.info("    installer: %s", line)

        # 5. Init + main container logs as they start producing output.
        for c in _INIT_CONTAINERS + ("notebook",):
            rc, out, _ = _kctl(
                "logs", pod_name, "-c", c, "--tail=20", timeout=5,
            )
            if rc != 0:
                continue
            for line in out.splitlines():
                if line in seen_log_lines.setdefault(c, set()):
                    continue
                seen_log_lines[c].add(line)
                log.info("    %s: %s", c, line)

        # Ready?
        ready = subprocess.run(
            ["kubectl", "wait", "--for=condition=ready", "pod", pod_name,
             "-n", NAMESPACE, "--timeout=2s"],
            capture_output=True, text=True,
        )
        if ready.returncode == 0:
            log.info("pod %s ready after %ds", pod_name, elapsed)
            return
        time.sleep(poll_s)
    pytest.fail(f"pod {pod_name} not ready within {timeout_s}s")


@pytest.fixture
def spawn_user(hub_url):
    """Factory: login and start a singleuser pod for a username convention.

    Username 'alice-data-ml' -> User(name='alice', groups=['data','ml']).
    Pods are stopped and deleted in teardown.
    """
    spawned: list[SpawnedUser] = []

    def _spawn(login_name):
        u = _login_and_spawn(hub_url, login_name)
        spawned.append(u)
        return u

    yield _spawn

    # Stop via the JupyterHub API so the spawner state is cleaned up (a
    # raw pod delete leaves the hub thinking the server is still pending,
    # causing 503s on the next login).
    for u in spawned:
        log.info("stopping server for %s via /hub/api", u.user)
        _stop_server(hub_url, u.login_name, u.user)


def _stop_server(base, login_name, real_user):
    """DELETE /hub/api/users/<user>/server (login first to get auth cookie)."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar))
    try:
        opener.open(base + "/hub/login", timeout=10).read()
        xsrf = next((c.value for c in jar if c.name == "_xsrf"), "")
        opener.open(urllib.request.Request(
            base + "/hub/login", method="POST",
            data=urllib.parse.urlencode(
                {"username": login_name, "password": "x", "_xsrf": xsrf}
            ).encode(),
        ), timeout=10).read()
        xsrf = next((c.value for c in jar if c.name == "_xsrf"), "")
        opener.open(urllib.request.Request(
            base + f"/hub/api/users/{real_user}/server",
            method="DELETE",
            headers={"X-XSRFToken": xsrf},
        ), timeout=15).read()
    except urllib.error.HTTPError as e:
        log.warning("stop_server: %s -> %d", real_user, e.code)
    except Exception as e:
        log.warning("stop_server failed: %s", e)
