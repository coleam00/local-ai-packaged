PROFILE ?= gpu-nvidia
ENVIRONMENT ?= private
PROJECT ?= localai

CONTAINER_RUNTIME := $(shell \
	if command -v podman >/dev/null 2>&1 && podman compose version >/dev/null 2>&1; then \
		echo podman; \
	elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then \
		echo docker; \
	fi)

ifeq ($(CONTAINER_RUNTIME),)
$(error Neither 'podman compose' nor 'docker compose' is available)
endif

COMPOSE := $(CONTAINER_RUNTIME) compose

.PHONY: start stop

start:
	python start_services.py --profile $(PROFILE) --environment $(ENVIRONMENT)

stop:
	$(COMPOSE) -p $(PROJECT) -f docker-compose.yml down || true
	@if [ -f supabase/docker/docker-compose.yml ]; then \
		$(COMPOSE) -p $(PROJECT) -f supabase/docker/docker-compose.yml down || true; \
	fi
