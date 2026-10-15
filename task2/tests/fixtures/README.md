# Parser fixture

`valid_roi.txt` is deliberately small, synthetic text for parser tests, not an
assignment measurement. Its counts are chosen to make consistency checks exact:
100 instructions / 200 cycles = 0.5 IPC, and 4 misses / 100 instructions * 1000
= 40 MPKI. Tests corrupt fields in this fixture to check rejection. No historical
result files or machine-specific experiment directories are needed.
