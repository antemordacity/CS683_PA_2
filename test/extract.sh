#!/usr/bin/env bash
# Usage: ./extract.sh results.txt
f="$1"

echo "IPC: $(grep -m1 '^CPU 0 cumulative IPC' "$f" | awk '{print $5}')"
echo "Branch accuracy: $(grep -m1 'Branch Prediction Accuracy' "$f" | awk '{print $6, "MPKI:", $8}')"
echo
printf "%-5s %10s %9s %8s %7s\n" Level Access Miss "Miss%" MPKI
grep -E '^(ITLB|DTLB|STLB|L1D|L1I|BTB|L2C|LLC) TOTAL' "$f" |
  awk '{printf "%-5s %10d %9d %8.2f %7.2f\n", $1, $4, $8, $14, $16}'
echo
echo "Average miss latency (cycles):"
grep -E '^[A-Z0-9]+ AVERAGE MISS LATENCY' "$f" | awk '{print " ", $1, $5}'