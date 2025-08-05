# Makefile for agent-schedule-system Project

# --- Variables ---
# Default environment is 'local' if not specified.
# Usage: make serve ENV="test"
ENV ?= local

# Default migration message if not specified.
# Usage: make db-generate M="your message"
M ?= "new migration"

# --- Phony Targets ---
# .PHONY declares targets that are not files.
.PHONY: all help serve db-generate db-upgrade

all: help

help:
	@echo "Usage: make <command> [OPTIONS]"
	@echo ""
	@echo "Commands:"
	@echo "  serve          Start the application server on 0.0.0.0:9091 (default ENV=local)."
	@echo "  db-generate    Generate a new database migration file."
	@echo "  db-upgrade     Upgrade the database to the latest version."
	@echo ""
	@echo "Options:"
	@echo "  ENV=<env>      Specify the environment (e.g., local, test, production). Default: local."
	@echo "  M=<message>    Specify the migration message for db-generate."
	@echo ""
	@echo "Examples:"
	@echo "  make serve"
	@echo "  make serve ENV=test"
	@echo "  make db-generate M=\"create user table\""
	@echo "  make db-upgrade ENV=prod"


# --- Application Commands ---
serve:
	@echo "Starting server in [$(ENV)]..."
	@ENV=$(ENV) uvicorn --host 0.0.0.0 --port 9091 main:app

# --- Database Migration Commands ---
db-generate:
	@echo "Generating DB migration for [$(ENV)]..."
	@ENV=$(ENV) alembic revision --autogenerate -m "$(M)"

db-upgrade:
	@echo "Upgrading DB for [$(ENV)] to head..."
	@ENV=$(ENV) alembic upgrade head
