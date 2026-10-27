# Model Evaluation -- Mode B

Generated: 2026-10-26T21:16:57.877422


Train range: <= 2024-06-30
Val range: 2024-06-30 .. 2025-06-30
Test range: > 2025-06-30

N train: 22945, N val: 7681, N test: 9438

Features: 78


## 1X2

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.5035 | 0.5061 | -0.0026 (worse) |
| val | logloss | 1.0078 | 1.0005 | +0.0073 (worse) |
| val | brier | 0.6029 | 0.5982 | +0.0047 (worse) |
| test | acc | 0.5020 | 0.5067 | -0.0047 (worse) |
| test | logloss | 1.0143 | 1.0026 | +0.0116 (worse) |
| test | brier | 0.6067 | 0.5997 | +0.0069 (worse) |

## OU25

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.5635 | 0.5684 | -0.0049 (worse) |
| val | logloss | 0.6805 | 0.6783 | +0.0022 (worse) |
| val | brier | 0.2438 | 0.2427 | +0.0011 (worse) |
| val | auc | 0.5892 | 0.5957 | -0.0065 (worse) |
| test | acc | 0.5593 | 0.5654 | -0.0060 (worse) |
| test | logloss | 0.6820 | 0.6782 | +0.0039 (worse) |
| test | brier | 0.2445 | 0.2427 | +0.0018 (worse) |
| test | auc | 0.5788 | 0.5921 | -0.0133 (worse) |

## HOME_OU05

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.7647 | 0.7646 | +0.0001 (BETTER) |
| val | logloss | 0.5231 | 0.5457 | -0.0226 (BETTER) |
| val | brier | 0.1721 | 0.1800 | -0.0079 (BETTER) |
| val | auc | 0.6390 | 0.5000 | +0.1390 (BETTER) |
| test | acc | 0.7750 | 0.7752 | -0.0002 (worse) |
| test | logloss | 0.5129 | 0.5332 | -0.0203 (BETTER) |
| test | brier | 0.1675 | 0.1744 | -0.0069 (BETTER) |
| test | auc | 0.6348 | 0.5000 | +0.1348 (BETTER) |

## HOME_OU15

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.6278 | 0.5687 | +0.0591 (BETTER) |
| val | logloss | 0.6479 | 0.6837 | -0.0358 (BETTER) |
| val | brier | 0.2281 | 0.2453 | -0.0172 (BETTER) |
| val | auc | 0.6475 | 0.5000 | +0.1475 (BETTER) |
| test | acc | 0.6203 | 0.5612 | +0.0590 (BETTER) |
| test | logloss | 0.6539 | 0.6858 | -0.0318 (BETTER) |
| test | brier | 0.2309 | 0.2463 | -0.0154 (BETTER) |
| test | auc | 0.6397 | 0.5000 | +0.1397 (BETTER) |

## AWAY_OU05

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.6873 | 0.6901 | -0.0029 (worse) |
| val | logloss | 0.6019 | 0.6190 | -0.0171 (BETTER) |
| val | brier | 0.2070 | 0.2139 | -0.0068 (BETTER) |
| val | auc | 0.6143 | 0.5000 | +0.1143 (BETTER) |
| test | acc | 0.7034 | 0.7050 | -0.0016 (worse) |
| test | logloss | 0.5893 | 0.6074 | -0.0181 (BETTER) |
| test | brier | 0.2013 | 0.2083 | -0.0070 (BETTER) |
| test | auc | 0.6166 | 0.5000 | +0.1166 (BETTER) |

## AWAY_OU15

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.6821 | 0.6637 | +0.0184 (BETTER) |
| val | logloss | 0.6109 | 0.6385 | -0.0276 (BETTER) |
| val | brier | 0.2106 | 0.2232 | -0.0126 (BETTER) |
| val | auc | 0.6391 | 0.5000 | +0.1391 (BETTER) |
| test | acc | 0.6620 | 0.6477 | +0.0143 (BETTER) |
| test | logloss | 0.6253 | 0.6494 | -0.0241 (BETTER) |
| test | brier | 0.2173 | 0.2284 | -0.0111 (BETTER) |
| test | auc | 0.6279 | 0.5000 | +0.1279 (BETTER) |