# -*- mode: Python -*-
# Tiltfile for nebari-data-science-pack local development
#
# References:
# - Tilt helm integration: https://docs.tilt.dev/helm.html
# - allow_k8s_contexts: https://docs.tilt.dev/api.html#api.allow_k8s_contexts

# Increase apply timeout for slow operations like image pulls
# Reference: https://docs.tilt.dev/api.html#api.update_settings
update_settings(k8s_upsert_timeout_secs=600)

# Safety: Only allow deployment to local k3d cluster
# Reference: https://github.com/tilt-dev/tilt/blob/main/internal/tiltfile/k8scontext/k8scontext.go
# k3d clusters use context name format: k3d-<cluster-name>
allow_k8s_contexts('k3d-nebari-dev')

# Deploy the Helm chart using helm() for templating
# Reference: https://docs.tilt.dev/helm.html
# Using helm() instead of helm_resource() because:
# - Better integration with Tilt's resource tracking
# - Automatic port-forward support via k8s_resource
# - Individual pod logs in Tilt UI
# Note: helm() skips chart hooks (like image-puller), which is fine for local dev
k8s_yaml(helm(
    '.',
    name='nebari',
    namespace='default',
))

# Configure the proxy resource for port forwarding
# Reference: https://docs.tilt.dev/api.html#api.k8s_resource
k8s_resource(
    workload='proxy',
    port_forwards=['8000:8000'],
    labels=['jupyterhub'],
)

# Configure the hub resource
k8s_resource(
    workload='hub',
    labels=['jupyterhub'],
)
