"""KubeSpawner configuration."""
# ruff: noqa: F821 - `c` is a magic global provided by JupyterHub

from z2jh import get_config

# Home directory: Dynamic PVC per user via the cluster's default StorageClass.
# We configure volumes here instead of via singleuser.storage in values.yaml because
# jhub-apps' JHubSpawner expects volumes as a list, but the subchart's dynamic storage
# generates a dict, causing a TraitError on startup.
#
# Using fixed /home/jovyan mount path because {username} expands differently in
# KubeSpawner (escaped slug) vs base Spawner traits like notebook_dir (raw username),
# causing a path mismatch when usernames contain special characters (e.g. emails).
# Each user still gets an isolated PVC via claim-{username}.
c.KubeSpawner.storage_pvc_ensure = True
c.KubeSpawner.storage_capacity = "10Gi"
c.KubeSpawner.storage_access_modes = ["ReadWriteOnce"]
c.KubeSpawner.volumes = [
    {
        "name": "home",
        "persistentVolumeClaim": {
            "claimName": "claim-{username}",
        },
    },
]
c.KubeSpawner.volume_mounts = [
    {
        "name": "home",
        "mountPath": "/home/jovyan",
    },
]

c.KubeSpawner.notebook_dir = "/home/jovyan"
c.KubeSpawner.working_dir = "/home/jovyan"

# Nebi remote server URL — when set, JupyterLab pods auto-connect to the
# Nebi team server using the user's Keycloak IdToken cookie.
# Read from JupyterHub custom config (set via values.yaml jupyterhub.custom.nebi-remote-url).
nebi_remote_url = get_config("custom.nebi-remote-url", "")

env = {
    "HOME": "/home/jovyan",
}
if nebi_remote_url:
    env["NEBI_REMOTE_URL"] = nebi_remote_url

c.KubeSpawner.environment = env

# Nebi auto-authentication: exchange the user's Keycloak IdToken for a Nebi JWT
# at spawn time so JupyterLab pods are pre-authenticated with the remote Nebi server.
nebi_internal_url = get_config("custom.nebi-internal-url", "")

if nebi_remote_url and nebi_internal_url:
    from tornado.httpclient import AsyncHTTPClient, HTTPRequest
    import json as _json

    async def _nebi_pre_spawn_hook(spawner):
        """Exchange Keycloak IdToken for Nebi JWT at spawn time."""
        auth_state = await spawner.user.get_auth_state()
        if not auth_state or "id_token" not in auth_state:
            spawner.log.warning("No IdToken in auth_state, skipping Nebi auto-auth")
            return

        session_url = f"{nebi_internal_url.rstrip('/')}/api/v1/auth/session"
        try:
            request = HTTPRequest(
                session_url,
                method="GET",
                headers={"Cookie": f"IdToken={auth_state['id_token']}"},
                request_timeout=10,
            )
            response = await AsyncHTTPClient().fetch(request)
            data = _json.loads(response.body)
            token = data.get("token", "")
            if token:
                spawner.environment["NEBI_AUTH_TOKEN"] = token
                spawner.log.info("Nebi auto-auth succeeded for %s", spawner.user.name)
            else:
                spawner.log.warning("Nebi session response had no token")
        except Exception:
            # Non-fatal: pod still spawns, user just won't be auto-authenticated
            spawner.log.exception("Nebi auto-auth failed (pod will still spawn)")

    c.KubeSpawner.pre_spawn_hook = _nebi_pre_spawn_hook
