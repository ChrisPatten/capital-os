HOST ?= 127.0.0.1
PORT ?= 8000
BASE_URL ?= http://$(HOST):$(PORT)
CAPITAL_OS_DB_URL ?= sqlite:///./data/capital_os.db
CAPITAL_OS_IDLE_SECONDS ?= 300
COA_PATH ?= config/coa.yaml
RUN_DIR ?= .run
HEALTH_RETRIES ?= 20
HEALTH_RETRY_DELAY ?= 0.2

PID_FILE := $(RUN_DIR)/capital-os.pid
URL_FILE := $(RUN_DIR)/capital-os.url
LAST_REQUEST_FILE := $(RUN_DIR)/last_request.ts
UVICORN_LOG := $(RUN_DIR)/uvicorn.log

.PHONY: init migrate coa-validate coa-seed health run stop serve-idle

init: migrate coa-seed

migrate:
	CAPITAL_OS_DB_URL='$(CAPITAL_OS_DB_URL)' python3 scripts/apply_migrations.py

coa-validate:
	python3 scripts/import_coa.py '$(COA_PATH)' --validate-only

coa-seed:
	CAPITAL_OS_DB_URL='$(CAPITAL_OS_DB_URL)' python3 scripts/import_coa.py '$(COA_PATH)'

health:
	curl -fsS '$(BASE_URL)/health' >/dev/null

run:
	@mkdir -p '$(RUN_DIR)'
	@healthy=0; \
	for _ in $$(seq 1 $(HEALTH_RETRIES)); do \
		if curl -fsS '$(BASE_URL)/health' >/dev/null 2>&1; then \
			healthy=1; \
			break; \
		fi; \
		sleep $(HEALTH_RETRY_DELAY); \
	done; \
	if [ "$$healthy" -eq 1 ]; then \
		echo "capital-os already healthy at $(BASE_URL)"; \
		exit 0; \
	fi
	@if [ -f '$(PID_FILE)' ]; then \
		pid=$$(cat '$(PID_FILE)' 2>/dev/null || true); \
		if [ -n "$$pid" ] && kill -0 $$pid >/dev/null 2>&1; then \
			kill $$pid >/dev/null 2>&1 || true; \
			for _ in 1 2 3 4 5; do \
				kill -0 $$pid >/dev/null 2>&1 || break; \
				sleep 0.2; \
			done; \
		fi; \
		rm -f '$(PID_FILE)'; \
	fi
	@nohup env \
		CAPITAL_OS_DB_URL='$(CAPITAL_OS_DB_URL)' \
		python3 scripts/serve_with_idle_shutdown.py \
		--host '$(HOST)' \
		--port '$(PORT)' \
		--pid-file '$(PID_FILE)' \
		--url-file '$(URL_FILE)' \
		--last-request-file '$(LAST_REQUEST_FILE)' \
		--idle-seconds 0 \
		>> '$(UVICORN_LOG)' 2>&1 &
	@for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do \
		curl -fsS '$(BASE_URL)/health' >/dev/null 2>&1 && exit 0; \
		sleep 0.2; \
	done; \
	echo "failed to start capital-os runtime at $(BASE_URL)" >&2; \
	exit 1

stop:
	@if [ -f '$(PID_FILE)' ]; then \
		pid=$$(cat '$(PID_FILE)' 2>/dev/null || true); \
		if [ -n "$$pid" ] && kill -0 $$pid >/dev/null 2>&1; then \
			kill $$pid >/dev/null 2>&1 || true; \
			for _ in 1 2 3 4 5 6 7 8 9 10; do \
				kill -0 $$pid >/dev/null 2>&1 || break; \
				sleep 0.2; \
			done; \
			kill -9 $$pid >/dev/null 2>&1 || true; \
		fi; \
	fi
	@rm -f '$(PID_FILE)' '$(URL_FILE)' '$(LAST_REQUEST_FILE)' '$(UVICORN_LOG)'

serve-idle:
	@mkdir -p '$(RUN_DIR)'
	@healthy=0; \
	for _ in $$(seq 1 $(HEALTH_RETRIES)); do \
		if curl -fsS '$(BASE_URL)/health' >/dev/null 2>&1; then \
			healthy=1; \
			break; \
		fi; \
		sleep $(HEALTH_RETRY_DELAY); \
	done; \
	if [ "$$healthy" -eq 1 ]; then \
		echo "capital-os already healthy at $(BASE_URL)"; \
		exit 0; \
	fi
	@if [ -f '$(PID_FILE)' ]; then \
		pid=$$(cat '$(PID_FILE)' 2>/dev/null || true); \
		if [ -z "$$pid" ] || ! kill -0 $$pid >/dev/null 2>&1; then \
			rm -f '$(PID_FILE)'; \
		fi; \
	fi
	@nohup env \
		CAPITAL_OS_DB_URL='$(CAPITAL_OS_DB_URL)' \
		python3 scripts/serve_with_idle_shutdown.py \
		--host '$(HOST)' \
		--port '$(PORT)' \
		--pid-file '$(PID_FILE)' \
		--url-file '$(URL_FILE)' \
		--last-request-file '$(LAST_REQUEST_FILE)' \
		--idle-seconds '$(CAPITAL_OS_IDLE_SECONDS)' \
		>> '$(UVICORN_LOG)' 2>&1 &
	@for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do \
		curl -fsS '$(BASE_URL)/health' >/dev/null 2>&1 && exit 0; \
		sleep 0.2; \
	done; \
	echo "failed to start capital-os runtime at $(BASE_URL)" >&2; \
	exit 1
