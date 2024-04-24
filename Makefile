all: lint test

lint:
	hatch fmt --linter --check
	hatch run types:check

test:
	hatch run test

test-slow:
	hatch run test-ci

test-all:
	hatch run all:test

coverage:
	hatch run cov

.PHONY: all lint test test-slow test-all coverage
