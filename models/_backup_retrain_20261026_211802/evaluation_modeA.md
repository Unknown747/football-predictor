# Model Evaluation -- Mode A

Generated: 2026-10-26T21:16:34.182251


Train range: <= 2024-06-30
Val range: 2024-06-30 .. 2025-06-30
Test range: > 2025-06-30

N train: 22945, N val: 7681, N test: 9438

Features: 74


## 1X2

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.4796 | 0.5061 | -0.0264 (worse) |
| val | logloss | 1.0346 | 1.0005 | +0.0341 (worse) |
| val | brier | 0.6209 | 0.5982 | +0.0227 (worse) |
| test | acc | 0.4705 | 0.5067 | -0.0361 (worse) |
| test | logloss | 1.0384 | 1.0026 | +0.0357 (worse) |
| test | brier | 0.6235 | 0.5997 | +0.0238 (worse) |

## OU25

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.5348 | 0.5684 | -0.0336 (worse) |
| val | logloss | 0.6896 | 0.6783 | +0.0114 (worse) |
| val | brier | 0.2483 | 0.2427 | +0.0055 (worse) |
| val | auc | 0.5487 | 0.5957 | -0.0469 (worse) |
| test | acc | 0.5356 | 0.5654 | -0.0298 (worse) |
| test | logloss | 0.6876 | 0.6782 | +0.0094 (worse) |
| test | brier | 0.2472 | 0.2427 | +0.0046 (worse) |
| test | auc | 0.5464 | 0.5921 | -0.0458 (worse) |

## HOME_OU05

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.7640 | 0.7646 | -0.0007 (worse) |
| val | logloss | 0.5308 | 0.5457 | -0.0149 (BETTER) |
| val | brier | 0.1749 | 0.1800 | -0.0051 (BETTER) |
| val | auc | 0.6127 | 0.5000 | +0.1127 (BETTER) |
| test | acc | 0.7757 | 0.7752 | +0.0005 (BETTER) |
| test | logloss | 0.5201 | 0.5332 | -0.0131 (BETTER) |
| test | brier | 0.1700 | 0.1744 | -0.0044 (BETTER) |
| test | auc | 0.6057 | 0.5000 | +0.1057 (BETTER) |

## HOME_OU15

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.6081 | 0.5687 | +0.0394 (BETTER) |
| val | logloss | 0.6599 | 0.6837 | -0.0238 (BETTER) |
| val | brier | 0.2338 | 0.2453 | -0.0115 (BETTER) |
| val | auc | 0.6193 | 0.5000 | +0.1193 (BETTER) |
| test | acc | 0.5976 | 0.5612 | +0.0363 (BETTER) |
| test | logloss | 0.6672 | 0.6858 | -0.0186 (BETTER) |
| test | brier | 0.2373 | 0.2463 | -0.0090 (BETTER) |
| test | auc | 0.6032 | 0.5000 | +0.1032 (BETTER) |

## AWAY_OU05

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.6898 | 0.6901 | -0.0004 (worse) |
| val | logloss | 0.6089 | 0.6190 | -0.0101 (BETTER) |
| val | brier | 0.2098 | 0.2139 | -0.0041 (BETTER) |
| val | auc | 0.5815 | 0.5000 | +0.0815 (BETTER) |
| test | acc | 0.7048 | 0.7050 | -0.0002 (worse) |
| test | logloss | 0.5975 | 0.6074 | -0.0099 (BETTER) |
| test | brier | 0.2044 | 0.2083 | -0.0039 (BETTER) |
| test | auc | 0.5824 | 0.5000 | +0.0824 (BETTER) |

## AWAY_OU15

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.6720 | 0.6637 | +0.0083 (BETTER) |
| val | logloss | 0.6251 | 0.6385 | -0.0134 (BETTER) |
| val | brier | 0.2170 | 0.2232 | -0.0062 (BETTER) |
| val | auc | 0.5967 | 0.5000 | +0.0967 (BETTER) |
| test | acc | 0.6505 | 0.6477 | +0.0028 (BETTER) |
| test | logloss | 0.6375 | 0.6494 | -0.0119 (BETTER) |
| test | brier | 0.2229 | 0.2284 | -0.0055 (BETTER) |
| test | auc | 0.5888 | 0.5000 | +0.0888 (BETTER) |