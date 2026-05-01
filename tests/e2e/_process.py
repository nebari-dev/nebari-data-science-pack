"""Subprocess execution helpers with structured logging.

Two modes:
  - run(...)         : streams stdout live to logging (for slow commands
                       where you want to see progress).
  - run(..., quiet=True): captures and logs after completion (for fast
                          queries where mid-stream output is just noise).

`kctl()` is a thin wrapper that always injects `-n <NAMESPACE>`.
"""

import logging
import subprocess

log = logging.getLogger("e2e")

NAMESPACE = "default"


def run(*args, quiet=False, check=True, timeout=None):
    """Run a subprocess. Returns CompletedProcess.

    quiet=False : live-stream stdout via log.info; stderr merged in.
    quiet=True  : capture, log all lines after completion (stdout=info,
                  stderr=warning).
    """
    log.info("$ %s", " ".join(args))
    if quiet:
        cp = subprocess.run(args, check=check, capture_output=True,
                            text=True, timeout=timeout)
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


def kctl(*args, quiet=True, **kw):
    """kubectl wrapper that auto-namespaces. Defaults to quiet=True."""
    return run("kubectl", *args, "-n", NAMESPACE, quiet=quiet, **kw)


def kctl_out(*args, timeout=10):
    """kubectl call returning (rc, stdout, stderr) without logging.

    Used by hot-loop pollers (PodObserver) where we'd otherwise spam the
    log with one `$ kubectl ...` line every poll cycle.
    """
    cp = subprocess.run(["kubectl", *args, "-n", NAMESPACE],
                        capture_output=True, text=True, timeout=timeout)
    return cp.returncode, (cp.stdout or "").strip(), (cp.stderr or "").strip()


def step(n, total, msg):
    """Log a progress banner: ──── [n/total] msg ────"""
    log.info("──── [%d/%d] %s ────", n, total, msg)
