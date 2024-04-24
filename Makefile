all: lint test

lint:
	hatch fmt --check
	hatch run types:check

format:
	hatch fmt --formatter

test:
	hatch run test

test-slow:
	hatch run test-ci

test-all:
	hatch run all:test

coverage:
	hatch run cov

.PHONY: all lint format test test-slow test-all coverage
