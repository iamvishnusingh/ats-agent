# Local dev targets (aligned with patterns in template-agent: venv, .env, run module).
# https://github.com/redhat-data-and-ai/template-agent uses `make local` similarly.

.PHONY: install local clean test

ROOT := $(abspath .)
PKG_DIR := ats_agent
PYTHON ?= python3
VENV := $(ROOT)/.venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

# Create venv and install the service package (editable).
install:
	@test -d "$(VENV)" || "$(PYTHON)" -m venv "$(VENV)"
	"$(PIP)" install -U pip
	"$(PIP)" install -e "$(ROOT)/$(PKG_DIR)[dev]" || "$(PIP)" install -e "$(ROOT)/$(PKG_DIR)"
	@echo "Done. Activate: source $(VENV)/bin/activate"

# Run FastAPI + LangGraph on AGENT_PORT (default 8082). Ensures .env exists under $(PKG_DIR)/.
# No Postgres required when USE_INMEMORY_SAVER=true (default in .env.example).
local:
	@test -f "$(ROOT)/$(PKG_DIR)/.env" || ( \
		echo "Creating $(PKG_DIR)/.env from .env.example..." && \
		cp "$(ROOT)/$(PKG_DIR)/.env.example" "$(ROOT)/$(PKG_DIR)/.env" )
	@test -x "$(PY)" || ( echo "Run 'make install' first." && exit 1 )
	@echo "Starting ATS agent (cwd=$(PKG_DIR) for .env loading)..."
	@echo "  Health: http://localhost:$${AGENT_PORT:-8082}/health"
	@echo "  Report: POST http://localhost:$${AGENT_PORT:-8082}/v1/report"
	@echo "  Docs (development): http://localhost:$${AGENT_PORT:-8082}/docs"
	@echo "Press Ctrl+C to stop."
	@cd "$(ROOT)/$(PKG_DIR)" && \
		PYTHONPATH="$(ROOT)" USE_INMEMORY_SAVER=true "$(PY)" -m ats_agent.src.main

clean:
	rm -rf "$(VENV)"
	rm -rf "$(ROOT)/$(PKG_DIR)/.pytest_cache" "$(ROOT)/$(PKG_DIR)/.ruff_cache" "$(ROOT)/$(PKG_DIR)/.mypy_cache"
	find "$(ROOT)/$(PKG_DIR)" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find "$(ROOT)" -maxdepth 2 -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "clean: removed venv and common caches"

# Smoke check: bytecode compile of package sources.
test:
	@test -x "$(PY)" || ( echo "Run 'make install' first." && exit 1 )
	"$(PY)" -m compileall -q "$(ROOT)/$(PKG_DIR)/src"
	@echo "compileall OK (add pytest under $(PKG_DIR)/tests to extend this target)"
