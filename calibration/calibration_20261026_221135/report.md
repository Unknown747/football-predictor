# Calibration Experiment — L10.6


Generated: 2026-10-26T22:12:04.844514


**Splits:** Train 22945, Val 7681, Test 9438


**Val internal split:** fit=4070, check=3611 (cutoff: 2025-01-15)


## Method Selection (on val_late)


| Market | Selected | Raw LL | Platt LL | Isotonic LL |
|---|---|---|---|---|
| Home O/U 0.5 | platt | 0.524052 | 0.523212 | 0.523789 |
| Home O/U 1.5 | platt | 0.644748 | 0.644294 | 0.650136 |
| Away O/U 0.5 | platt | 0.589783 | 0.594929 | 0.594680 |
| Away O/U 1.5 | platt | 0.611324 | 0.609812 | 0.610534 |

## Test Evaluation (after calibration)


| Market | Method | N | LogLoss raw | LogLoss cal | Δ | CI 95% Δ | Brier raw | Brier cal | Acc raw | Acc cal |
|---|---|---|---|---|---|---|---|---|---|---|
| Home O/U 0.5 | platt | 9438 | 0.5129 | 0.5121 | -0.0008 | [-0.0015, -0.0001] | 0.1675 | 0.1674 | 0.7750 | 0.7739 |
| Home O/U 1.5 | platt | 9438 | 0.6539 | 0.6531 | -0.0009 | [-0.0014, -0.0003] | 0.2309 | 0.2305 | 0.6203 | 0.6206 |
| Away O/U 0.5 | platt | 9438 | 0.5893 | 0.5894 | +0.0002 | [-0.0003, +0.0006] | 0.2013 | 0.2013 | 0.7034 | 0.7047 |
| Away O/U 1.5 | platt | 9438 | 0.6253 | 0.6246 | -0.0007 | [-0.0017, +0.0004] | 0.2173 | 0.2170 | 0.6620 | 0.6613 |

## Verification


| Market | Method | Prob range OK | Monotonic OK | Class changed at 0.5 |
|---|---|---|---|---|
| Home O/U 0.5 | platt | True | True | 58/9438 |
| Home O/U 1.5 | platt | True | True | 233/9438 |
| Away O/U 0.5 | platt | True | True | 64/9438 |
| Away O/U 1.5 | platt | True | True | 23/9438 |

## Notes


- 'Class changed at 0.5' = number of predictions where calibrated class differs from raw class at threshold 0.5. This is NOT necessarily a bug (calibration may shift effective threshold), but documented for transparency.


- Method selected based on **val_late** logloss (temporal internal val). Test set untouched during selection.


- ΔLogLoss CI 95% from paired bootstrap (N=1000).
