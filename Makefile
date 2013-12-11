VENV_DIR=$(HOME)/venv
SUPERVISORD_PIDFILE=tmp/supervisord.pid

setup:
	mkdir -p tmp
	mkdir -p uitests/captures

test-ui: setup clean start nap run-ui-tests stop

nap:
	@echo Waiting for start-up to complete
	bin/backoff.sh curl -I http://localhost:9765/include.js

run-ui-tests:
	@/bin/bash -c 'pushd uitests > /dev/null; \
	casperjs test tests ; \
	popd > /dev/null || \
	$(MAKE) stop'

clean:
	find uitests/captures -type f -exec rm {} \;

start:
	@if [ ! -f "$(SUPERVISORD_PIDFILE)" ]; then \
		VENV_DIR=$(VENV_DIR) supervisord -c ./supervisord.conf && echo supervisord started; \
	else echo supervisord already started; fi

stop:
	@if [ -f "$(SUPERVISORD_PIDFILE)" ]; then \
		kill `cat $(SUPERVISORD_PIDFILE)` && echo supervisord stopped; \
	else echo supervisord pidfile not found; fi

.PHONY: setup test-ui nap run-ui-tests clean start stop
