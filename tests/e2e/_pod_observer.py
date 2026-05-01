"""Live observability for a kubelet-managed pod.

`wait_for_pod_ready(name)` polls until the pod is Ready, surfacing every
observable signal as it changes:
  - one-line pod state (phase, container/init readiness)
  - kubectl-describe events (deduped by Type/Reason/Source/Message)
  - node-level kubelet journal lines that mention the pod
  - nfs-client-installer DaemonSet status + apt-install init logs
  - init/main container logs as soon as they produce output

Dedup means new info appears each cycle; a stuck pod produces a quiet
loop with the most recent state visible at a glance.
"""

import logging
import subprocess
import time

import pytest

from _process import kctl_out

log = logging.getLogger("e2e")


# Init containers we expect: block-cloud-metadata is z2jh's, the rest
# come from PR #30. Names are stable across runs.
_INIT_CONTAINERS = ("block-cloud-metadata", "initialize-shared-mounts")
_LOG_CONTAINERS = _INIT_CONTAINERS + ("notebook",)


def wait_for_pod_ready(pod_name, timeout_s=180, poll_s=5):
    """Poll until pod is Ready, with deep observability each cycle."""
    obs = _PodObserver(pod_name)
    deadline = time.time() + timeout_s
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        elapsed = int(timeout_s - (deadline - time.time()))
        log.info("=== pod-wait %s attempt=%d elapsed=%ds ===",
                 pod_name, attempt, elapsed)
        obs.snapshot()
        if obs.is_ready():
            log.info("pod %s ready after %ds", pod_name, elapsed)
            return
        time.sleep(poll_s)
    pytest.fail(f"pod {pod_name} not ready within {timeout_s}s")


class _PodObserver:
    """Per-cycle pod snapshot with cross-cycle dedup of events + log lines."""

    def __init__(self, pod_name):
        self.pod = pod_name
        self._seen = set()  # dedup key for events, kubelet lines, installer logs
        self._seen_logs = {c: set() for c in _LOG_CONTAINERS}

    def snapshot(self):
        self._log_pod_summary()
        self._log_container_states()
        self._log_pod_events()
        self._log_kubelet_journal()
        self._log_nfs_installer()
        self._log_container_outputs()

    def is_ready(self):
        cp = subprocess.run(
            ["kubectl", "wait", "--for=condition=ready", "pod", self.pod,
             "-n", "default", "--timeout=2s"],
            capture_output=True, text=True,
        )
        return cp.returncode == 0

    # ---- per-section collectors ----

    def _log_pod_summary(self):
        rc, out, _ = kctl_out("get", "pod", self.pod, "--no-headers")
        if rc == 0:
            log.info("    pod: %s", out)
        else:
            log.warning("    pod not found yet")

    def _log_container_states(self):
        _, out, _ = kctl_out(
            "get", "pod", self.pod, "-o",
            "jsonpath="
            "{range .status.initContainerStatuses[*]}"
            "init/{.name} ready={.ready} state={.state}{'\\n'}{end}"
            "{range .status.containerStatuses[*]}"
            "main/{.name} ready={.ready} state={.state}{'\\n'}{end}",
        )
        for line in out.splitlines():
            log.info("    %s", line)

    def _log_pod_events(self):
        """Parse the Events section of `kubectl describe pod`. Dedup on
        (Type, Reason, Source, Message) — drop the Age column which keeps
        ticking and breaks naive string-equality dedup."""
        _, out, _ = kctl_out("describe", "pod", self.pod)
        in_events = False
        for raw in out.splitlines():
            line = raw.strip()
            if raw.startswith("Events:"):
                in_events = True
                continue
            if raw and not raw.startswith(" "):
                in_events = False
            if not (in_events and line):
                continue
            if line.startswith(("Type", "----")):
                continue
            cols = line.split(None, 4)  # Type Reason Age From Message
            key = ("evt", cols[0], cols[1],
                   cols[3] if len(cols) > 3 else "",
                   cols[4] if len(cols) > 4 else "")
            if key not in self._seen:
                self._seen.add(key)
                log.info("    event: %s", line)

    def _log_kubelet_journal(self):
        """Tail kubelet's systemd journal on the pod's node, filtered to
        lines that mention this pod (the deepest observable signal — shows
        actual mount.nfs / image-pull / runtime-exec activity)."""
        _, node, _ = kctl_out(
            "get", "pod", self.pod, "-o", "jsonpath={.spec.nodeName}",
        )
        if not node:
            return
        cp = subprocess.run(
            ["docker", "exec", node, "journalctl", "-u", "kubelet",
             "--since", "8 seconds ago", "--no-pager", "-q", "-o", "cat"],
            capture_output=True, text=True, timeout=5,
        )
        for line in (cp.stdout or "").splitlines():
            if not (self.pod in line
                    or "FailedMount" in line
                    or "MountVolume" in line):
                continue
            key = ("kubelet", line)
            if key not in self._seen:
                self._seen.add(key)
                log.info("    kubelet: %s", line)

    def _log_nfs_installer(self):
        """The chart's nfs-client-installer DaemonSet apt-installs nfs-common
        in a privileged init container. Failures here block all NFS mounts —
        but the pause container shows `1/1 Running` regardless, so we have
        to tail the init container's logs separately."""
        _, out, _ = kctl_out(
            "get", "pods",
            "-l", "app.kubernetes.io/component=nfs-client-installer",
            "--no-headers",
        )
        if not out:
            return
        log.info("    nfs-installer: %s", out)
        for line in out.splitlines():
            installer_pod = line.split()[0]
            _, init_log, _ = kctl_out(
                "logs", installer_pod, "-c", "install-nfs-common",
                "--tail=20", timeout=5,
            )
            for log_line in init_log.splitlines():
                key = ("installer", log_line)
                if key not in self._seen:
                    self._seen.add(key)
                    log.info("    installer: %s", log_line)

    def _log_container_outputs(self):
        for container in _LOG_CONTAINERS:
            rc, out, _ = kctl_out(
                "logs", self.pod, "-c", container, "--tail=20", timeout=5,
            )
            if rc != 0:
                continue
            for line in out.splitlines():
                if line in self._seen_logs[container]:
                    continue
                self._seen_logs[container].add(line)
                log.info("    %s: %s", container, line)
