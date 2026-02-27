# Minimal Makefile for local development
# Only two commands needed - Tilt handles everything else via its UI

.PHONY: up down jupyterlab

# Start local development environment
# - ctlptl apply is idempotent (creates cluster only if not exists)
# - tilt up starts the dev loop with UI at http://localhost:10350
up:
	ctlptl apply -f ctlptl-config.yaml
	@pgrep -f "tilt up" >/dev/null && echo "Tilt already running at http://localhost:10350" || tilt up

# Tear down local development environment
down:
	-tilt down
	-pkill -f "tilt up" 2>/dev/null || true
	ctlptl delete -f ctlptl-config.yaml

JUPYTERLAB_CONTAINER = jupyterlab-test
JUPYTERLAB_IMAGE = jupyterlab:test
JUPYTERLAB_PORT = 8888

# Build and run the jupyterlab image for local testing
# Stops and removes any existing container first
jupyterlab:
	@if docker ps -a --format '{{.Names}}' | grep -q '^$(JUPYTERLAB_CONTAINER)$$'; then \
		echo "Stopping and removing existing container..."; \
		docker stop $(JUPYTERLAB_CONTAINER) >/dev/null 2>&1 || true; \
		docker rm $(JUPYTERLAB_CONTAINER) >/dev/null 2>&1 || true; \
	fi
	docker build --target jupyterlab -t $(JUPYTERLAB_IMAGE) images/
	docker run -d --name $(JUPYTERLAB_CONTAINER) -p $(JUPYTERLAB_PORT):8888 \
		$(JUPYTERLAB_IMAGE) \
		jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root \
		--ServerApp.token='' --ServerApp.password=''
	@echo "JupyterLab running at http://localhost:$(JUPYTERLAB_PORT)"
