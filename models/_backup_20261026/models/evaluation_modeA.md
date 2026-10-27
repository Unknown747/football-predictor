# Model Evaluation -- Mode A

Generated: 2026-10-26T20:15:13.677029


Train range: <= 2024-06-30
Val range: 2024-06-30 .. 2025-06-30
Test range: > 2025-06-30

N train: 22945, N val: 7681, N test: 9438

Features: 74


## 1X2

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.4764 | 0.5061 | -0.0297 (worse) |
| val | logloss | 1.0343 | 1.0005 | +0.0337 (worse) |
| val | brier | 0.6211 | 0.5982 | +0.0229 (worse) |
| test | acc | 0.4663 | 0.5067 | -0.0404 (worse) |
| test | logloss | 1.0401 | 1.0026 | +0.0375 (worse) |
| test | brier | 0.6250 | 0.5997 | +0.0253 (worse) |

## OU25

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.5350 | 0.5684 | -0.0335 (worse) |
| val | logloss | 0.6895 | 0.6783 | +0.0113 (worse) |
| val | brier | 0.2482 | 0.2427 | +0.0055 (worse) |
| val | auc | 0.5500 | 0.5957 | -0.0456 (worse) |
| test | acc | 0.5386 | 0.5654 | -0.0268 (worse) |
| test | logloss | 0.6877 | 0.6782 | +0.0095 (worse) |
| test | brier | 0.2473 | 0.2427 | +0.0046 (worse) |
| test | auc | 0.5459 | 0.5921 | -0.0463 (worse) |

## HOME_OU05

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.7641 | 0.7646 | -0.0005 (worse) |
| val | logloss | 0.5317 | 0.5457 | -0.0140 (BETTER) |
| val | brier | 0.1752 | 0.1800 | -0.0048 (BETTER) |
| val | auc | 0.6095 | 0.5000 | +0.1095 (BETTER) |
| test | acc | 0.7748 | 0.7752 | -0.0003 (worse) |
| test | logloss | 0.5207 | 0.5332 | -0.0125 (BETTER) |
| test | brier | 0.1702 | 0.1744 | -0.0042 (BETTER) |
| test | auc | 0.6025 | 0.5000 | +0.1025 (BETTER) |

## HOME_OU15

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.6064 | 0.5687 | +0.0378 (BETTER) |
| val | logloss | 0.6598 | 0.6837 | -0.0239 (BETTER) |
| val | brier | 0.2337 | 0.2453 | -0.0116 (BETTER) |
| val | auc | 0.6194 | 0.5000 | +0.1194 (BETTER) |
| test | acc | 0.5940 | 0.5612 | +0.0327 (BETTER) |
| test | logloss | 0.6676 | 0.6858 | -0.0182 (BETTER) |
| test | brier | 0.2375 | 0.2463 | -0.0089 (BETTER) |
| test | auc | 0.6043 | 0.5000 | +0.1043 (BETTER) |

## AWAY_OU05

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.6895 | 0.6901 | -0.0007 (worse) |
| val | logloss | 0.6096 | 0.6190 | -0.0094 (BETTER) |
| val | brier | 0.2101 | 0.2139 | -0.0038 (BETTER) |
| val | auc | 0.5787 | 0.5000 | +0.0787 (BETTER) |
| test | acc | 0.7049 | 0.7050 | -0.0001 (worse) |
| test | logloss | 0.5979 | 0.6074 | -0.0095 (BETTER) |
| test | brier | 0.2045 | 0.2083 | -0.0038 (BETTER) |
| test | auc | 0.5831 | 0.5000 | +0.0831 (BETTER) |

## AWAY_OU15

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.6697 | 0.6637 | +0.0060 (BETTER) |
| val | logloss | 0.6256 | 0.6385 | -0.0129 (BETTER) |
| val | brier | 0.2173 | 0.2232 | -0.0059 (BETTER) |
| val | auc | 0.5961 | 0.5000 | +0.0961 (BETTER) |
| test | acc | 0.6499 | 0.6477 | +0.0022 (BETTER) |
| test | logloss | 0.6377 | 0.6494 | -0.0117 (BETTER) |
| test | brier | 0.2230 | 0.2284 | -0.0054 (BETTER) |
| test | auc | 0.5886 | 0.5000 | +0.0886 (BETTER) |