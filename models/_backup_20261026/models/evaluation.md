# Model Evaluation

Generated: 2026-10-26T20:04:05.463347


Train range: <= 2024-06-30
Val range: 2024-06-30 .. 2025-06-30
Test range: > 2025-06-30

N train: 22945, N val: 7681, N test: 9438

Features: 140


## 1X2

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.5939 | 0.5061 | +0.0879 (BETTER) |
| val | logloss | 0.8693 | 1.0005 | -0.1312 (BETTER) |
| val | brier | 0.5134 | 0.5982 | -0.0848 (BETTER) |
| test | acc | 0.5989 | 0.5067 | +0.0922 (BETTER) |
| test | logloss | 0.8647 | 1.0026 | -0.1379 (BETTER) |
| test | brier | 0.5107 | 0.5997 | -0.0890 (BETTER) |

## OU25

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.6809 | 0.5684 | +0.1125 (BETTER) |
| val | logloss | 0.5834 | 0.6783 | -0.0949 (BETTER) |
| val | brier | 0.2005 | 0.2427 | -0.0422 (BETTER) |
| val | auc | 0.7544 | 0.5957 | +0.1588 (BETTER) |
| test | acc | 0.6903 | 0.5654 | +0.1249 (BETTER) |
| test | logloss | 0.5842 | 0.6782 | -0.0940 (BETTER) |
| test | brier | 0.2006 | 0.2427 | -0.0421 (BETTER) |
| test | auc | 0.7547 | 0.5921 | +0.1625 (BETTER) |

## HOME_OU05

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.8017 | 0.7646 | +0.0371 (BETTER) |
| val | logloss | 0.4384 | 0.5457 | -0.1073 (BETTER) |
| val | brier | 0.1415 | 0.1800 | -0.0385 (BETTER) |
| val | auc | 0.7897 | 0.5000 | +0.2897 (BETTER) |
| test | acc | 0.8089 | 0.7752 | +0.0337 (BETTER) |
| test | logloss | 0.4271 | 0.5332 | -0.1061 (BETTER) |
| test | brier | 0.1368 | 0.1744 | -0.0376 (BETTER) |
| test | auc | 0.7923 | 0.5000 | +0.2923 (BETTER) |

## HOME_OU15

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.7197 | 0.5687 | +0.1510 (BETTER) |
| val | logloss | 0.5372 | 0.6837 | -0.1465 (BETTER) |
| val | brier | 0.1826 | 0.2453 | -0.0627 (BETTER) |
| val | auc | 0.7934 | 0.5000 | +0.2934 (BETTER) |
| test | acc | 0.7228 | 0.5612 | +0.1616 (BETTER) |
| test | logloss | 0.5348 | 0.6858 | -0.1510 (BETTER) |
| test | brier | 0.1813 | 0.2463 | -0.0650 (BETTER) |
| test | auc | 0.7981 | 0.5000 | +0.2981 (BETTER) |

## AWAY_OU05

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.7607 | 0.6901 | +0.0706 (BETTER) |
| val | logloss | 0.4962 | 0.6190 | -0.1228 (BETTER) |
| val | brier | 0.1640 | 0.2139 | -0.0498 (BETTER) |
| val | auc | 0.7816 | 0.5000 | +0.2816 (BETTER) |
| test | acc | 0.7710 | 0.7050 | +0.0660 (BETTER) |
| test | logloss | 0.4836 | 0.6074 | -0.1238 (BETTER) |
| test | brier | 0.1588 | 0.2083 | -0.0495 (BETTER) |
| test | auc | 0.7862 | 0.5000 | +0.2862 (BETTER) |

## AWAY_OU15

| Set | Metric | Model | Baseline | Δ (Model - Baseline) |
|---|---|---|---|---|
| val | acc | 0.7414 | 0.6637 | +0.0777 (BETTER) |
| val | logloss | 0.5009 | 0.6385 | -0.1376 (BETTER) |
| val | brier | 0.1692 | 0.2232 | -0.0540 (BETTER) |
| val | auc | 0.7949 | 0.5000 | +0.2949 (BETTER) |
| test | acc | 0.7219 | 0.6477 | +0.0742 (BETTER) |
| test | logloss | 0.5171 | 0.6494 | -0.1323 (BETTER) |
| test | brier | 0.1766 | 0.2284 | -0.0518 (BETTER) |
| test | auc | 0.7945 | 0.5000 | +0.2945 (BETTER) |