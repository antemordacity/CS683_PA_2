#!/bin/bash
# usage: ./run_all.sh <binary-name>   (the name you passed to build_champsim.sh)
NAME=$1
BIN=$(ls bin/*-1core-$NAME)
mkdir -p results/$NAME
for t in ../traces/*.champsimtrace.xz; do
  echo "$BIN -warmup_instructions 25000000 -simulation_instructions 25000000 -traces $t > results/$NAME/$(basename $t .champsimtrace.xz).txt 2>&1"
done | xargs -P 4 -I{} sh -c "{}"
