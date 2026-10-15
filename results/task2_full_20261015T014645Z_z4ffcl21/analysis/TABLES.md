# New runs (25,000,000 ROI instructions)

| Trace | Policy | IPC | Speedup / LRU | L2C load MPKI | Instruction MPKI | Data MPKI |
|---|---|---:|---:|---:|---:|---:|
| Trace1 | lru | 0.232288 | 1.000000 | 17.75090 | 10.40300 | 7.34788 |
| Trace1 | rrip | 0.232320 | 1.000138 | 17.68140 | 10.61290 | 7.06844 |
| Trace1 | irrip_v1 | 0.232270 | 0.999923 | 17.73080 | 10.16210 | 7.56868 |
| Trace1 | irrip_v2 | 0.232230 | 0.999750 | 17.72410 | 9.99920 | 7.72488 |
| Trace1 | irrip_v3 | 0.232193 | 0.999591 | 17.77160 | 9.86920 | 7.90240 |
| Trace1 | dyn_0.10 | 0.231939 | 0.998498 | 17.78490 | 9.90596 | 7.87892 |
| Trace1 | dyn_0.20 | 0.232118 | 0.999268 | 17.76930 | 9.89300 | 7.87632 |
| Trace1 | dyn_0.25 | 0.231952 | 0.998554 | 17.77420 | 9.89988 | 7.87436 |
| Trace1 | dyn_0.35 | 0.231955 | 0.998566 | 17.77780 | 9.90104 | 7.87680 |
| Trace1 | dyn_0.50 | 0.232319 | 1.000133 | 17.68190 | 10.61290 | 7.06896 |
| Trace2 | lru | 0.250638 | 1.000000 | 28.22860 | 19.52980 | 8.69880 |
| Trace2 | rrip | 0.251296 | 1.002625 | 26.60660 | 18.54560 | 8.06100 |
| Trace2 | irrip_v1 | 0.253368 | 1.010892 | 25.76270 | 16.90470 | 8.85804 |
| Trace2 | irrip_v2 | 0.254714 | 1.016262 | 24.65310 | 15.36290 | 9.29020 |
| Trace2 | irrip_v3 | 0.256319 | 1.022666 | 23.23560 | 13.74250 | 9.49312 |
| Trace2 | dyn_0.10 | 0.256134 | 1.021928 | 23.35300 | 13.89980 | 9.45324 |
| Trace2 | dyn_0.20 | 0.256133 | 1.021924 | 23.35330 | 13.89980 | 9.45356 |
| Trace2 | dyn_0.25 | 0.256134 | 1.021928 | 23.35300 | 13.89950 | 9.45348 |
| Trace2 | dyn_0.35 | 0.255727 | 1.020304 | 23.68770 | 14.26350 | 9.42420 |
| Trace2 | dyn_0.50 | 0.251382 | 1.002968 | 26.60280 | 18.54750 | 8.05528 |
| Trace3 | lru | 0.382008 | 1.000000 | 3.95916 | 1.12316 | 2.83600 |
| Trace3 | rrip | 0.381631 | 0.999013 | 4.04428 | 1.19760 | 2.84668 |
| Trace3 | irrip_v1 | 0.381966 | 0.999890 | 3.95572 | 1.07572 | 2.88000 |
| Trace3 | irrip_v2 | 0.382039 | 1.000081 | 3.91012 | 1.03000 | 2.88012 |
| Trace3 | irrip_v3 | 0.382057 | 1.000128 | 3.89472 | 1.00004 | 2.89468 |
| Trace3 | dyn_0.10 | 0.381999 | 0.999976 | 3.90000 | 1.00712 | 2.89288 |
| Trace3 | dyn_0.20 | 0.382010 | 1.000005 | 3.90040 | 1.00656 | 2.89384 |
| Trace3 | dyn_0.25 | 0.382001 | 0.999982 | 3.90052 | 1.00616 | 2.89436 |
| Trace3 | dyn_0.35 | 0.381775 | 0.999390 | 3.98284 | 1.09720 | 2.88564 |
| Trace3 | dyn_0.50 | 0.381631 | 0.999013 | 4.04428 | 1.19760 | 2.84668 |

Speedup uses the reported IPC. Counts independently validate IPC and MPKI within simulator printing precision.

## Dynamic diagnostics

| Trace | Threshold | Metric | Switches | Follower RRIP updates | Follower I-RRIP updates |
|---|---:|---:|---:|---:|---:|
| Trace1 | 0.1 | 0.384516170638 | 5 | 14584 | 1800979 |
| Trace1 | 0.2 | 0.384197679545 | 23 | 57663 | 1757924 |
| Trace1 | 0.25 | 0.384371439014 | 3 | 78088 | 1737488 |
| Trace1 | 0.35 | 0.384593894721 | 5 | 494633 | 1320940 |
| Trace1 | 0.5 | 0.384155777166 | 2 | 1815349 | 277 |
| Trace2 | 0.1 | 0.48002944424 | 3 | 193 | 2834595 |
| Trace2 | 0.2 | 0.48002944424 | 5 | 630 | 2834158 |
| Trace2 | 0.25 | 0.480038274695 | 3 | 738 | 2834051 |
| Trace2 | 0.35 | 0.480047717583 | 11 | 158335 | 2676448 |
| Trace2 | 0.5 | 0.479485591246 | 40 | 2438575 | 396257 |
| Trace3 | 0.1 | 0.31920754717 | 7 | 63044 | 951817 |
| Trace3 | 0.2 | 0.318977551405 | 9 | 104552 | 910313 |
| Trace3 | 0.25 | 0.318979176098 | 5 | 130061 | 884793 |
| Trace3 | 0.35 | 0.319168207722 | 18 | 579110 | 435745 |
| Trace3 | 0.5 | 0.319259720414 | 2 | 1014842 | 13 |

## Threshold sensitivity

Each comparison uses the same trace and instruction budget. These observations do not establish a universal best threshold.

- Trace1: dynamic IPC spans 0.231939 to 0.232319; highest reported IPC at threshold(s) 0.50. Best dynamic IPC / RRIP = 0.999996; best dynamic IPC / static V3 = 1.000543.

- Trace2: dynamic IPC spans 0.251382 to 0.256134; highest reported IPC at threshold(s) 0.10, 0.25. Best dynamic IPC / RRIP = 1.019252; best dynamic IPC / static V3 = 0.999278.

- Trace3: dynamic IPC spans 0.381631 to 0.382010; highest reported IPC at threshold(s) 0.20. Best dynamic IPC / RRIP = 1.000993; best dynamic IPC / static V3 = 0.999877.

A tie at printed precision does not prove all internal behavior is identical. Read the switch counts and follower update counts above.
