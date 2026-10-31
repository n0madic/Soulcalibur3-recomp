WORK ?= $(CURDIR)/recomp/work
EXPLORE ?= 1
export ISO EXPLORE PS2_JOBS

.PHONY: help build run test test-runtime
help:
	@echo 'make build         - build SC3 with ps2-native-recomp (ISO=<path>, EXPLORE=0 skips exploration)'
	@echo 'make run           - launch SC3 (ARGS="--fullscreen" passes runner options)'
	@echo 'make test          - test build/launch tooling without a disc'
	@echo 'make test-runtime  - run synthetic audio, VU0 and window-watchdog tests'
build:
	python3 recomp/port.py build --work "$(WORK)"
run:
	python3 recomp/port.py run --work "$(WORK)" -- $(ARGS)
test:
	python3 -m unittest discover -s recomp/tests -v
test-runtime:
	python3 recomp/port.py test-runtime --work "$(WORK)"
