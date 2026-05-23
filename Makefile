PYTHON ?= /opt/homebrew/bin/python3.13
VENV   := .venv
BIN    := $(VENV)/bin
ANVIL  := $(BIN)/anvil

.PHONY: help venv install dev test test-live demo clean reinstall

help:
	@echo "Anvil dev targets:"
	@echo "  make venv        - create $(VENV) using $(PYTHON) -m venv --copies"
	@echo "  make install     - install anvil + runtime deps (editable)"
	@echo "  make dev         - install anvil + runtime + dev deps (pytest, ruff, mypy)"
	@echo "  make test        - run unit tests (skips live Flash tests)"
	@echo "  make test-live   - run live Flash tests (needs GOOGLE_API_KEY in .env)"
	@echo "  make demo        - run anvil init against a sample description"
	@echo "  make reinstall   - blow away $(VENV) and reinstall from scratch"
	@echo "  make clean       - remove $(VENV) and __pycache__"

$(VENV)/bin/python:
	$(PYTHON) -m venv --copies $(VENV)
	$(BIN)/python -m pip install --quiet --upgrade pip
	$(BIN)/pip install --quiet uv

venv: $(VENV)/bin/python

install: venv
	$(BIN)/uv pip install -e .

dev: venv
	$(BIN)/uv pip install -e ".[dev]"

test: dev
	$(BIN)/pytest -m "not live" -v; status=$$?; [ $$status -eq 0 ] || [ $$status -eq 5 ]

test-live: dev
	@test -f .env || (echo "Missing .env with GOOGLE_API_KEY" && exit 1)
	set -a && . ./.env && set +a && $(BIN)/pytest -m live -v

demo: dev
	@test -f .env || (echo "Missing .env with GOOGLE_API_KEY" && exit 1)
	rm -rf /tmp/anvil-demo && mkdir -p /tmp/anvil-demo
	set -a && . ./.env && set +a && $(ANVIL) init "Build a customer support agent: triage email, draft reply, escalate low-confidence cases to humans" --out /tmp/anvil-demo
	@echo
	@echo "Demo output at /tmp/anvil-demo/"
	@find /tmp/anvil-demo -type f -not -path "*/.git/*" | sort

reinstall: clean dev

clean:
	rm -rf $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
