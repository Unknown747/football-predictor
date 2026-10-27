# Backtest Report

Generated: 20261026_215202

Test: 9438 rows, 2025-07-25 .. 2026-10-21


## Global Metrics


### 1X2


**Model (all test rows, N=9438):**

- logloss: 1.0143
- brier: 0.6067
- accuracy: 0.5020
- auc: 0.6342

**Baseline odds (subset N=9426):**

- model logloss: 1.0140
- baseline logloss: 1.0025
- model acc: 0.5019
- baseline acc: 0.5066

**Baseline uniform:**

- logloss: 1.0986
- acc: 0.4311

**Bootstrap CI:** method=block_week, n_iter_valid=1000
- logloss_diff (model-baseline): +0.0114 [+0.0087, +0.0143]

### Over/Under 2.5


**Model (all test rows, N=9438):**

- logloss: 0.6820
- brier: 0.2445
- accuracy: 0.5593
- auc: 0.5788

**Baseline odds (subset N=9414):**

- model logloss: 0.6820
- baseline logloss: 0.6781
- model acc: 0.5593
- baseline acc: 0.5653

**Baseline base_rate (all test):**

- baseline logloss: 0.6925
- baseline acc: 0.5296

**Bootstrap CI:** method=block_week, n_iter_valid=1000
- logloss_diff (model-baseline): +0.0038 [+0.0021, +0.0056]

### Home Over 0.5


**Model (all test rows, N=9438):**

- logloss: 0.5129
- brier: 0.1675
- accuracy: 0.7750
- auc: 0.6348

**Baseline base_rate (all test):**

- baseline logloss: 0.5332
- baseline acc: 0.7752

**Bootstrap CI:** method=block_week, n_iter_valid=1000
- logloss_diff (model-baseline): -0.0204 [-0.0239, -0.0170]

### Home Over 1.5


**Model (all test rows, N=9438):**

- logloss: 0.6539
- brier: 0.2309
- accuracy: 0.6203
- auc: 0.6397

**Baseline base_rate (all test):**

- baseline logloss: 0.6858
- baseline acc: 0.5612

**Bootstrap CI:** method=block_week, n_iter_valid=1000
- logloss_diff (model-baseline): -0.0319 [-0.0366, -0.0271]

### Away Over 0.5


**Model (all test rows, N=9438):**

- logloss: 0.5893
- brier: 0.2013
- accuracy: 0.7034
- auc: 0.6166

**Baseline base_rate (all test):**

- baseline logloss: 0.6074
- baseline acc: 0.7050

**Bootstrap CI:** method=block_week, n_iter_valid=1000
- logloss_diff (model-baseline): -0.0181 [-0.0210, -0.0150]

### Away Over 1.5


**Model (all test rows, N=9438):**

- logloss: 0.6253
- brier: 0.2173
- accuracy: 0.6620
- auc: 0.6279

**Baseline base_rate (all test):**

- baseline logloss: 0.6494
- baseline acc: 0.6477

**Bootstrap CI:** method=block_week, n_iter_valid=1000
- logloss_diff (model-baseline): -0.0241 [-0.0278, -0.0204]

## Limitations

Lihat limitations.md untuk daftar lengkap.
