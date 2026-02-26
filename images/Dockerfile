ARG BASE_IMAGE=ubuntu:24.04
FROM ${BASE_IMAGE} AS builder
LABEL MAINTAINER="Nebari development team"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    wget \
    bzip2 \
    ca-certificates \
    curl \
    git

COPY scripts /opt/scripts

RUN curl -fsSL https://pixi.sh/install.sh | bash

ENV PATH=/root/.pixi/bin:/opt/scripts:${PATH}

ENV DEFAULT_ENV=default


# ========== jupyterhub install ===========
FROM builder AS jupyterhub

COPY --from=builder /root/.pixi /root/.pixi
COPY jupyterhub/pixi.toml /opt/jupyterhub/pixi.toml
COPY jupyterhub/pixi.lock /opt/jupyterhub/pixi.lock
RUN --mount=type=cache,target=/root/.cache/rattler/cache,sharing=locked \
    pixi install --manifest-path /opt/jupyterhub/ -e ${DEFAULT_ENV} --locked

COPY jupyterhub /opt/jupyterhub
RUN /opt/jupyterhub/postBuild

WORKDIR /srv/jupyterhub

# So we can actually write a db file here
RUN fix-permissions /srv/jupyterhub

ENV PATH=/opt/jupyterhub/.pixi/envs/${DEFAULT_ENV}/bin:${PATH}

CMD ["jupyterhub", "--config", "/usr/local/etc/jupyterhub/jupyterhub_config.py"]


# ========== jupyterlab base ===========
FROM builder AS intermediate
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
RUN chmod -R a-w ~
ENV TZ=UTC
# Set timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    locales \
    libnss-wrapper \
    xvfb


# ========== jupyterlab install ===========
FROM intermediate AS jupyterlab

ARG GPU

ENV CONDA_DIR=/opt/conda \
    DEFAULT_ENV=default \
    LD_LIBRARY_PATH=${GPU:+/usr/local/nvidia/lib64} \
    NVIDIA_PATH=${GPU:+/usr/local/nvidia/bin}

ENV PATH=${GPU:+/usr/local/nvidia/bin:}${PATH}

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglx-mesa0 \
    libxrandr2 \
    libxss1 \
    libxcursor1 \
    libxcomposite1 \
    libasound2t64 \
    libxi6 \
    libxtst6 \
    libfontconfig1 \
    libxrender1 \
    libosmesa6

COPY --from=builder /root/.pixi /root/.pixi
COPY jupyterlab/pixi.toml /opt/jupyterlab/pixi.toml
COPY jupyterlab/pixi.lock /opt/jupyterlab/pixi.lock
RUN --mount=type=cache,target=/root/.cache/rattler/cache,sharing=locked \
    pixi install --manifest-path /opt/jupyterlab/ -e ${DEFAULT_ENV} --locked

# ========== code-server install ============
ENV PATH=/opt/jupyterlab/.pixi/envs/${DEFAULT_ENV}/share/code-server/bin:${PATH}

COPY jupyterlab /opt/jupyterlab
RUN /opt/jupyterlab/postBuild

ENV LD_LIBRARY_PATH=/usr/local/nvidia/lib64
ENV NVIDIA_PATH=/usr/local/nvidia/bin
ENV PATH=/opt/jupyterlab/.pixi/envs/${DEFAULT_ENV}/bin:${NVIDIA_PATH}:$PATH


# ========== jupyterlab + nebi ===========
FROM jupyterlab AS jupyterlab-nebi

# TEMPORARY: using nebi from main branch (sha-6a19116) for NEBI_SERVER_BASE_PATH support.
# When the next nebi release (>0.7) is out, replace the COPY below with the commented-out
# ARG/RUN block, updating NEBI_VERSION to the new release version.
#
# ARG NEBI_VERSION=<new-version>
# ARG TARGETARCH
# RUN curl -fsSL \
#     "https://github.com/nebari-dev/nebi/releases/download/v${NEBI_VERSION}/nebi_${NEBI_VERSION}_linux_$([ "${TARGETARCH}" = "amd64" ] && echo "x86_64" || echo "arm64").tar.gz" \
#     | tar -xz -C /usr/local/bin nebi
COPY --from=quay.io/nebari/nebi:sha-6a19116 /app/nebi /usr/local/bin/nebi

COPY nebi/jupyter_server_config.py /usr/local/etc/jupyter/jupyter_server_config.py
COPY nebi/icons /usr/local/etc/jupyter/icons
# WORKAROUND for https://github.com/nebari-dev/jupyterlab-launchpad/issues/73
# Remove this line (and images/nebi/custom/) when the bug is fixed.
COPY nebi/custom/custom.css /root/.jupyter/custom/custom.css
