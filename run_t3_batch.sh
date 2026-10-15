#!/bin/bash
set -u
mkdir -p results/task3_full bin
run_cfg () {   # $1 = build name, $2 = tag
  ./build_champsim.sh "$1" || { echo "BUILD FAILED $1"; return; }
  BIN=$(ls -t bin/hashed* | head -1); cp "$BIN" "bin/t3_$2"
  for T in 1 2 3; do
    ./bin/t3_$2 -warmup_instructions 25000000 -simulation_instructions 25000000 \
      -traces ~/traces/Trace$T.gz > results/task3_full/$2_Trace$T.txt 2>&1 &
  done; wait
  echo "DONE $2"
}
run_cfg baseline lru
run_cfg dyn_irrip dyn
run_cfg spp spp
run_cfg spp+dyn_irrip spp_dyn
