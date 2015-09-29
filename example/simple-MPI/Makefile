KGEN_HOME := ../../kgen
KGEN := ${KGEN_HOME}/kgen.py

SRC_DIR := ${PWD}/src
SRC := ${SRC_DIR}/update_mod.F90
CALLSITE := update_mod:update:calc
FC := ifort
FC_FLAGS := -O3
MPI_INC := /ncar/opt/intel/12.1.0.233/impi/4.0.3.008/intel64/include

test:
	python ${KGEN} \
		-D ROW=4,COL=4 \
		-I ${SRC_DIR}:${MPI_INC} \
		-e exclude.ini \
		--mpi ranks=0:1 \
		--invocation 1,3 \
		--kernel-compile FC='${FC}',FC_FLAGS='${FC_FLAGS}' \
		--timing repeat=1000 \
		--state-build cmds="cd ${SRC_DIR}; make build" \
		--state-run cmds="cd ${SRC_DIR}; make run" \
		${SRC}:${CALLSITE}

clean:
	${MAKE} clean -C src
	rm -rf kernel state kgen.log