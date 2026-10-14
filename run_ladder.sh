#!/bin/bash
# usage: ./run_ladder.sh <1|2|3>
V=$1
sed -i "s/^#define IRRIP_VERSION .*/#define IRRIP_VERSION $V/" replacement/irrip.l2c_repl
CXX=g++-9 ./build_champsim.sh irrip > results/build_v$V.log 2>&1
cp bin/hashed_perceptron-no-no-no-no-no-no-no-lru-lru-lru-irrip-lru-lru-lru-lru-1core-irrip bin/irrip_v$V
for t in Trace1 Trace2 Trace3; do
  ./bin/irrip_v$V -warmup_instructions 25000000 -simulation_instructions 25000000 -traces ~/traces/$t.gz > results/irrip_v${V}_$t.txt &
done
wait