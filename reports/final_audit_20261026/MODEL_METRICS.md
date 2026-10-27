# Model Metrics - Global Backtest

Sumber: backtest/backtest_20261026_215202/metrics.json

1X2 (Multiclass)
LogLoss: 1.0143
Baseline Odds: 1.0025
Delta: +0.0114 (WORSE)
Brier: 0.6067
Accuracy: 0.5020
AUC: 0.6342

OU2.5 (Binary)
LogLoss: 0.6820
Baseline Odds: 0.6781
Delta: +0.0038 (WORSE)
Brier: 0.2445
Accuracy: 0.5593
AUC: 0.5788

Home O/U 0.5 (Binary)
LogLoss: 0.5129
Base Rate: 0.5332
Delta: -0.0204 (BETTER)
Brier: 0.1675
Accuracy: 0.7750

Home O/U 1.5 (Binary)
LogLoss: 0.6539
Base Rate: 0.6858
Delta: -0.0319 (BETTER)
Brier: 0.2309
Accuracy: 0.6203

Away O/U 0.5 (Binary)
LogLoss: 0.5893
Base Rate: 0.6074
Delta: -0.0181 (BETTER)

Away O/U 1.5 (Binary)
LogLoss: 0.6253
Base Rate: 0.6494
Delta: -0.0241 (BETTER)

Kesimpulan: Model kalah dari odds di 1X2/OU2.5. Model menang dari base rate di Home/Away O/U.
