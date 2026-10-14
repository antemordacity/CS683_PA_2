#!/bin/bash
# usage: ./run3.sh <binary path> <tag>
for t in Trace1 Trace2 Trace3; do
  $1 -warmup_instructions 25000000 -simulation_instructions 25000000 -traces ~/traces/$t.gz > results/$2_$t.txt &
done
wait