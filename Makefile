# Local dev gate — mirrors the GitHub workflows (.github/workflows/ci.yml +
# linter.yml) so you can run lint / semgrep / tests before pushing.
#
#   make setup    # one-time: install + wire pre-commit and semgrep
#   make check    # everything CI runs (lint + semgrep + backend tests)
#
# Override the site or bench location as needed:  make test SITE=mysite

SITE          ?= bs.local
APP           := buildsuite_core
BENCH         := $(abspath $(CURDIR)/../..)
SEMGREP_RULES := $(CURDIR)/.frappe-semgrep-rules

.PHONY: help setup lint format semgrep test e2e check

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: ## one-time: install pre-commit + semgrep (isolated) and wire the git hook
	@command -v pipx >/dev/null || { \
		echo "ERROR: pipx not found. Install it first (do NOT 'pip install pre-commit'"; \
		echo "       inside the bench venv — it pulls virtualenv, which conflicts with"; \
		echo "       Frappe's filelock pin). Run:"; \
		echo "         python3 -m pip install --user pipx && python3 -m pipx ensurepath"; \
		exit 1; }
	pipx install pre-commit
	pipx install semgrep
	pre-commit install
	@echo "pre-commit hook installed — ruff/prettier/eslint now run on every commit."

lint: ## run all pre-commit hooks (ruff lint+format, prettier, eslint) over the repo
	pre-commit run --all-files

format: ## auto-format Python (ruff) and JS/Vue/SCSS (prettier)
	pre-commit run ruff-format --all-files
	pre-commit run prettier --all-files

semgrep: ## run the Frappe semgrep rules + python correctness rules
	@test -d $(SEMGREP_RULES) \
		|| git clone --depth 1 https://github.com/frappe/semgrep-rules.git $(SEMGREP_RULES)
	semgrep scan --error \
		--config $(SEMGREP_RULES)/rules \
		--config r/python.lang.correctness .

test: ## run the backend test suite (bench run-tests)
	cd $(BENCH) && bench --site $(SITE) set-config allow_tests true >/dev/null
	cd $(BENCH) && bench --site $(SITE) run-tests --app $(APP)

e2e: ## build the frontend + run Cypress (needs `bench start` running in another shell)
	cd $(BENCH) && bench --site $(SITE) execute $(APP).api.cypress_setup.ensure_cypress_users
	cd frontend && yarn build && yarn cypress run

check: lint semgrep test ## the full local gate — lint + semgrep + backend tests
