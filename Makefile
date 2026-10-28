WORK    := $(CURDIR)/recomp/work
GAME    := $(WORK)/game
ELF     := $(GAME)/SCES_533.12
RUNNER  := $(WORK)/PS2Recomp/out/build/ps2xRuntime/ps2EntryRunner

.PHONY: run build ghidra help

help:
	@echo "make build  - extract disc, build PS2Recomp, recompile the ELF, build the runner (ISO=<path> when the disc image is not the only .iso here)"
	@echo "make ghidra - import the ELF into Ghidra and export the function map used by make build"
	@echo "make run    - launch the recompiled game"

build:
	./recomp/build.sh "$(WORK)"

ghidra:
	./recomp/ghidra_export.sh "$(WORK)"

run:
	@test -x "$(RUNNER)" || { echo "Runner not built: run 'make build' first"; exit 1; }
	@test -f "$(ELF)" || { echo "Disc not extracted: run 'make build' first"; exit 1; }
	cd "$(GAME)" && "$(RUNNER)" "$(ELF)"
