KGEN_HOME := ../..
KGEN := ${KGEN_HOME}/bin/kgen

SRC_DIR := ${PWD}/src
SRC := ${SRC_DIR}/update_mod.F90
CALLSITE := update_mod:update:calc
FC := gfortran

test:
	${KGEN} \
		-D ROW=4,COL=4 \
		-I ${SRC_DIR} \
		--timing repeat=10 \
		--invocation 0:0:1,0:0:2,0:0:3 \
		--kernel-compile FC='${FC}' \
		--state-build cmds="cd ${SRC_DIR}; make build FC='${FC}'" \
		--state-run cmds="cd ${SRC_DIR}; make run FC='${FC}'" \
		--check tolerance=1.0D-14 \
		${SRC}:${CALLSITE}

clean:
	${MAKE} clean -C src
	rm -rf kernel state kgen.log
