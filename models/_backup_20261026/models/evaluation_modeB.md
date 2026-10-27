# Model Evaluation -- Mode B

Generated: 2026-10-26T20:22:00.242735


Train range: <= 2024-06-30
Val range: 2024-06-30 .. 2025-06-30
Test range: > 2025-06-30

N train: 22945, N val: 7681, N test: 9438

Features: 78


## 1X2

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.5045 | 0.5061 | -0.0016 (worse) |
| val | logloss | 1.0081 | 1.0005 | +0.0076 (worse) |
| val | brier | 0.6030 | 0.5982 | +0.0048 (worse) |
| test | acc | 0.4996 | 0.5067 | -0.0071 (worse) |
| test | logloss | 1.0142 | 1.0026 | +0.0116 (worse) |
| test | brier | 0.6068 | 0.5997 | +0.0071 (worse) |

## OU25

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.5637 | 0.5684 | -0.0047 (worse) |
| val | logloss | 0.6803 | 0.6783 | +0.0020 (worse) |
| val | brier | 0.2437 | 0.2427 | +0.0010 (worse) |
| val | auc | 0.5904 | 0.5957 | -0.0053 (worse) |
| test | acc | 0.5584 | 0.5654 | -0.0070 (worse) |
| test | logloss | 0.6819 | 0.6782 | +0.0037 (worse) |
| test | brier | 0.2444 | 0.2427 | +0.0018 (worse) |
| test | auc | 0.5801 | 0.5921 | -0.0120 (worse) |

## HOME_OU05

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.7647 | 0.7646 | +0.0001 (BETTER) |
| val | logloss | 0.5235 | 0.5457 | -0.0222 (BETTER) |
| val | brier | 0.1722 | 0.1800 | -0.0078 (BETTER) |
| val | auc | 0.6362 | 0.5000 | +0.1362 (BETTER) |
| test | acc | 0.7745 | 0.7752 | -0.0006 (worse) |
| test | logloss | 0.5128 | 0.5332 | -0.0204 (BETTER) |
| test | brier | 0.1675 | 0.1744 | -0.0069 (BETTER) |
| test | auc | 0.6342 | 0.5000 | +0.1342 (BETTER) |

## HOME_OU15

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.6278 | 0.5687 | +0.0591 (BETTER) |
| val | logloss | 0.6486 | 0.6837 | -0.0351 (BETTER) |
| val | brier | 0.2284 | 0.2453 | -0.0168 (BETTER) |
| val | auc | 0.6444 | 0.5000 | +0.1444 (BETTER) |
| test | acc | 0.6170 | 0.5612 | +0.0557 (BETTER) |
| test | logloss | 0.6547 | 0.6858 | -0.0311 (BETTER) |
| test | brier | 0.2312 | 0.2463 | -0.0151 (BETTER) |
| test | auc | 0.6373 | 0.5000 | +0.1373 (BETTER) |

## AWAY_OU05

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.6872 | 0.6901 | -0.0030 (worse) |
| val | logloss | 0.6016 | 0.6190 | -0.0174 (BETTER) |
| val | brier | 0.2070 | 0.2139 | -0.0069 (BETTER) |
| val | auc | 0.6151 | 0.5000 | +0.1151 (BETTER) |
| test | acc | 0.7030 | 0.7050 | -0.0020 (worse) |
| test | logloss | 0.5880 | 0.6074 | -0.0194 (BETTER) |
| test | brier | 0.2007 | 0.2083 | -0.0076 (BETTER) |
| test | auc | 0.6197 | 0.5000 | +0.1197 (BETTER) |

## AWAY_OU15

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.6812 | 0.6637 | +0.0174 (BETTER) |
| val | logloss | 0.6117 | 0.6385 | -0.0269 (BETTER) |
| val | brier | 0.2110 | 0.2232 | -0.0122 (BETTER) |
| val | auc | 0.6379 | 0.5000 | +0.1379 (BETTER) |
| test | acc | 0.6627 | 0.6477 | +0.0150 (BETTER) |
| test | logloss | 0.6244 | 0.6494 | -0.0250 (BETTER) |
| test | brier | 0.2169 | 0.2284 | -0.0115 (BETTER) |
| test | auc | 0.6295 | 0.5000 | +0.1295 (BETTER) |