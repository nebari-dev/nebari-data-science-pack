# Minimal Makefile for local development
# Only two commands needed - Tilt handles everything else via its UI

.PHONY: up down

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
