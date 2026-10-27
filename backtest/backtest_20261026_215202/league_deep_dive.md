# ⚠️ SUPERSEDED — Lihat Audit v2

> **File ini adalah audit lama dan DIANGGAP USANG untuk klaim per-liga di pasar 1X2 dan OU 2.5.**
>
> **Alasan:** Laporan ini menghitung `ΔLogLoss = model_logloss_per_liga − global_baseline_logloss` (baseline odds GLOBAL, dicampur dari 22 liga), bukan baseline odds PER LIGA. Ini menyebabkan bias optimis untuk liga dengan odds efisien (misal Portugal-Liga1, Spain-LaLiga, England-PL) — mereka tampak "BETTER" padahal tidak signifikan setelah baseline disesuaikan.
>
> **Klaim yang TIDAK VALID di file ini:**
> - Ranking 1X2 dan OU 2.5 vs baseline (Δ di tabel 2.1 dan 2.2)
> - Verdict BETTER/WORSE di Section 3 (Cross-Market League Ranking) untuk 1X2 dan OU 2.5
>
> **Klaim yang MASIH VALID di file ini:**
> - Model logloss / Brier / Acc / AUC per liga (kolom `Model LL`, `Acc`, `AUC` di Section 2) — metrik model itu sendiri tidak berubah, hanya perbandingan terhadap baseline yang bermasalah
> - Home/Away O/U (Section 2.3–2.6): baseline = `base_rate_train` (global, konsisten untuk semua liga) — **hasil ini valid**
> - Distribusi per season (Section 4) — tidak terkait baseline
>
> **Gunakan audit yang benar:**
> - `backtest/backtest_20261026_215202/league_baseline_audit_20261026_220351_v2/league_metrics.md`
> - `backtest/backtest_20261026_215202/league_baseline_audit_20261026_220351_v2/league_metrics.csv`
> - `backtest/backtest_20261026_215202/league_baseline_audit_20261026_220351_v2/config.json`
>
> **Dokumentasi lengkap metode fix:** lihat `limitations.md` di direktori audit v2.
>
> ---
>
> _File di bawah ini adalah isi ASLI dari `league_deep_dive.md` (diproduksi sebelum audit v2). Tidak ada bagian yang dihapus atau diubah. Hanya ditambahkan header peringatan ini._

---

# Per-League & Per-Season Deep Dive


Generated from: `backtest_20261026_215202/metrics.json`


**Read-only audit.** Tidak ada tuning, retraining, atau prediksi live.


**Ambang:** N ≥ 100 untuk komparatif. N < 100 ditandai INSUFFICIENT N.


## 1. Per-League Summary — Semua Pasar


Total leagues dalam test: 22


### League list

- Belgium-JPL (N in 1x2: 383)
- England-Champ (N in 1x2: 684)
- England-Conference (N in 1x2: 707)
- England-L1 (N in 1x2: 678)
- England-L2 (N in 1x2: 690)
- England-PL (N in 1x2: 450)
- France-L1 (N in 1x2: 369)
- France-L2 (N in 1x2: 386)
- Germany-BL1 (N in 1x2: 360)
- Germany-BL2 (N in 1x2: 378)
- Greece-SL (N in 1x2: 284)
- Italy-SA (N in 1x2: 450)
- Italy-SB (N in 1x2: 450)
- Netherlands-ED (N in 1x2: 387)
- Portugal-Liga1 (N in 1x2: 378)
- Scotland-Champ (N in 1x2: 234)
- Scotland-L1 (N in 1x2: 234)
- Scotland-L2 (N in 1x2: 235)
- Scotland-Prem (N in 1x2: 282)
- Spain-LaLiga (N in 1x2: 469)
- Spain-Segunda (N in 1x2: 572)
- Turkey-SL (N in 1x2: 378)

## 2. Detail per Pasar × Liga


### 2.1. 1X2


| League | N | LogLoss | Acc | AUC | Baseline | ΔLogLoss | Status |
|---|---|---|---|---|---|---|---|
| Portugal-Liga1 | 378 | 0.9216 | 0.5450 | 0.7204 | odds:1.0025 | -0.0809 | BETTER |
| Greece-SL | 284 | 0.9501 | 0.5317 | 0.7035 | odds:1.0025 | -0.0524 | BETTER |
| Spain-LaLiga | 469 | 0.9672 | 0.5203 | 0.6795 | odds:1.0025 | -0.0353 | BETTER |
| France-L1 | 369 | 0.9777 | 0.5312 | 0.6784 | odds:1.0025 | -0.0249 | BETTER |
| Italy-SA | 450 | 0.9783 | 0.5511 | 0.6792 | odds:1.0025 | -0.0242 | BETTER |
| Scotland-Prem | 282 | 0.9824 | 0.5213 | 0.6594 | odds:1.0025 | -0.0201 | BETTER |
| Turkey-SL | 378 | 0.9866 | 0.5265 | 0.6670 | odds:1.0025 | -0.0160 | BETTER |
| Germany-BL1 | 360 | 0.9874 | 0.5444 | 0.6543 | odds:1.0025 | -0.0152 | BETTER |
| Netherlands-ED | 387 | 0.9921 | 0.5375 | 0.6584 | odds:1.0025 | -0.0104 | BETTER |
| England-Conference | 707 | 0.9989 | 0.5375 | 0.6323 | odds:1.0025 | -0.0036 | INCONCLUSIVE |
| Scotland-L1 | 234 | 0.9995 | 0.5214 | 0.6535 | odds:1.0025 | -0.0030 | INCONCLUSIVE |
| Belgium-JPL | 383 | 1.0112 | 0.5091 | 0.6266 | odds:1.0025 | +0.0087 | WORSE |
| England-PL | 450 | 1.0257 | 0.5044 | 0.6203 | odds:1.0025 | +0.0232 | WORSE |
| Italy-SB | 450 | 1.0359 | 0.4778 | 0.6256 | odds:1.0025 | +0.0333 | WORSE |
| England-L1 | 678 | 1.0399 | 0.4764 | 0.6072 | odds:1.0025 | +0.0374 | WORSE |
| Spain-Segunda | 572 | 1.0416 | 0.4930 | 0.5873 | odds:1.0025 | +0.0391 | WORSE |
| England-L2 | 690 | 1.0498 | 0.4768 | 0.5940 | odds:1.0025 | +0.0473 | WORSE |
| Germany-BL2 | 378 | 1.0507 | 0.4709 | 0.5775 | odds:1.0025 | +0.0482 | WORSE |
| England-Champ | 684 | 1.0511 | 0.4839 | 0.5887 | odds:1.0025 | +0.0485 | WORSE |
| Scotland-Champ | 234 | 1.0678 | 0.4231 | 0.6029 | odds:1.0025 | +0.0653 | WORSE |
| France-L2 | 386 | 1.0682 | 0.4326 | 0.5942 | odds:1.0025 | +0.0657 | WORSE |
| Scotland-L2 | 235 | 1.0713 | 0.4043 | 0.5554 | odds:1.0025 | +0.0688 | WORSE |

### 2.2. OU 2.5


| League | N | LogLoss | Acc | AUC | Baseline | ΔLogLoss | Status |
|---|---|---|---|---|---|---|---|
| Germany-BL1 | 360 | 0.6438 | 0.6333 | 0.5817 | odds:0.6781 | -0.0343 | BETTER |
| Netherlands-ED | 387 | 0.6544 | 0.6305 | 0.5349 | odds:0.6781 | -0.0237 | BETTER |
| Turkey-SL | 378 | 0.6626 | 0.5847 | 0.6429 | odds:0.6781 | -0.0155 | BETTER |
| France-L1 | 369 | 0.6660 | 0.6098 | 0.6296 | odds:0.6781 | -0.0122 | BETTER |
| Spain-LaLiga | 469 | 0.6723 | 0.5821 | 0.6154 | odds:0.6781 | -0.0058 | BETTER |
| Portugal-Liga1 | 378 | 0.6739 | 0.5926 | 0.6053 | odds:0.6781 | -0.0043 | INCONCLUSIVE |
| England-Conference | 707 | 0.6739 | 0.5997 | 0.5819 | odds:0.6781 | -0.0043 | INCONCLUSIVE |
| Scotland-L2 | 235 | 0.6790 | 0.5745 | 0.5280 | odds:0.6781 | +0.0009 | INCONCLUSIVE |
| France-L2 | 386 | 0.6791 | 0.5570 | 0.5878 | odds:0.6781 | +0.0009 | INCONCLUSIVE |
| Spain-Segunda | 572 | 0.6830 | 0.5629 | 0.5964 | odds:0.6781 | +0.0049 | INCONCLUSIVE |
| Germany-BL2 | 378 | 0.6843 | 0.5503 | 0.5024 | odds:0.6781 | +0.0061 | WORSE |
| England-L1 | 678 | 0.6862 | 0.5280 | 0.5637 | odds:0.6781 | +0.0080 | WORSE |
| Italy-SB | 450 | 0.6872 | 0.5356 | 0.5681 | odds:0.6781 | +0.0090 | WORSE |
| Greece-SL | 284 | 0.6887 | 0.5563 | 0.5636 | odds:0.6781 | +0.0105 | WORSE |
| Scotland-L1 | 234 | 0.6914 | 0.5427 | 0.5465 | odds:0.6781 | +0.0133 | WORSE |
| England-PL | 450 | 0.6915 | 0.5444 | 0.5356 | odds:0.6781 | +0.0133 | WORSE |
| England-Champ | 684 | 0.6919 | 0.5322 | 0.5476 | odds:0.6781 | +0.0137 | WORSE |
| Scotland-Prem | 282 | 0.6945 | 0.5426 | 0.5388 | odds:0.6781 | +0.0164 | WORSE |
| England-L2 | 690 | 0.6952 | 0.5116 | 0.5245 | odds:0.6781 | +0.0170 | WORSE |
| Belgium-JPL | 383 | 0.6952 | 0.5248 | 0.5356 | odds:0.6781 | +0.0171 | WORSE |
| Italy-SA | 450 | 0.6967 | 0.5467 | 0.5318 | odds:0.6781 | +0.0185 | WORSE |
| Scotland-Champ | 234 | 0.7125 | 0.4872 | 0.4664 | odds:0.6781 | +0.0344 | WORSE |

### 2.3. Home O/U 0.5


| League | N | LogLoss | Acc | AUC | Baseline | ΔLogLoss | Status |
|---|---|---|---|---|---|---|---|
| Netherlands-ED | 387 | 0.4209 | 0.8398 | 0.6861 | base:0.5332 | -0.1123 | BETTER |
| Germany-BL1 | 360 | 0.4421 | 0.8222 | 0.6870 | base:0.5332 | -0.0911 | BETTER |
| Spain-LaLiga | 469 | 0.4587 | 0.8166 | 0.6581 | base:0.5332 | -0.0746 | BETTER |
| Scotland-L2 | 235 | 0.4736 | 0.8213 | 0.5136 | base:0.5332 | -0.0596 | BETTER |
| Germany-BL2 | 378 | 0.4798 | 0.8095 | 0.5924 | base:0.5332 | -0.0535 | BETTER |
| England-Conference | 707 | 0.4878 | 0.7935 | 0.6515 | base:0.5332 | -0.0454 | BETTER |
| Italy-SB | 450 | 0.4903 | 0.8067 | 0.5888 | base:0.5332 | -0.0429 | BETTER |
| Scotland-Prem | 282 | 0.5006 | 0.7837 | 0.6258 | base:0.5332 | -0.0326 | BETTER |
| France-L1 | 369 | 0.5066 | 0.7778 | 0.6626 | base:0.5332 | -0.0266 | BETTER |
| Turkey-SL | 378 | 0.5098 | 0.7672 | 0.6728 | base:0.5332 | -0.0235 | BETTER |
| England-L1 | 678 | 0.5174 | 0.7802 | 0.5885 | base:0.5332 | -0.0158 | BETTER |
| England-L2 | 690 | 0.5204 | 0.7725 | 0.6232 | base:0.5332 | -0.0128 | BETTER |
| England-Champ | 684 | 0.5227 | 0.7822 | 0.5520 | base:0.5332 | -0.0106 | BETTER |
| England-PL | 450 | 0.5236 | 0.7600 | 0.6455 | base:0.5332 | -0.0096 | BETTER |
| Portugal-Liga1 | 378 | 0.5296 | 0.7407 | 0.6899 | base:0.5332 | -0.0036 | INCONCLUSIVE |
| Spain-Segunda | 572 | 0.5301 | 0.7657 | 0.6223 | base:0.5332 | -0.0032 | INCONCLUSIVE |
| Belgium-JPL | 383 | 0.5354 | 0.7624 | 0.6111 | base:0.5332 | +0.0022 | INCONCLUSIVE |
| Scotland-L1 | 234 | 0.5505 | 0.7308 | 0.6746 | base:0.5332 | +0.0173 | WORSE |
| Greece-SL | 284 | 0.5513 | 0.7324 | 0.6688 | base:0.5332 | +0.0181 | WORSE |
| France-L2 | 386 | 0.5791 | 0.7306 | 0.5633 | base:0.5332 | +0.0459 | WORSE |
| Italy-SA | 450 | 0.5805 | 0.7022 | 0.6723 | base:0.5332 | +0.0473 | WORSE |
| Scotland-Champ | 234 | 0.6104 | 0.6966 | 0.5970 | base:0.5332 | +0.0771 | WORSE |

### 2.4. Home O/U 1.5


| League | N | LogLoss | Acc | AUC | Baseline | ΔLogLoss | Status |
|---|---|---|---|---|---|---|---|
| Portugal-Liga1 | 378 | 0.6080 | 0.6772 | 0.7210 | base:0.6858 | -0.0778 | BETTER |
| Italy-SA | 450 | 0.6223 | 0.6689 | 0.6719 | base:0.6858 | -0.0635 | BETTER |
| Scotland-L1 | 234 | 0.6305 | 0.6453 | 0.6855 | base:0.6858 | -0.0553 | BETTER |
| Greece-SL | 284 | 0.6308 | 0.6514 | 0.6865 | base:0.6858 | -0.0550 | BETTER |
| Turkey-SL | 378 | 0.6324 | 0.6429 | 0.6759 | base:0.6858 | -0.0533 | BETTER |
| Belgium-JPL | 383 | 0.6330 | 0.6292 | 0.6800 | base:0.6858 | -0.0527 | BETTER |
| France-L2 | 386 | 0.6341 | 0.6632 | 0.6109 | base:0.6858 | -0.0517 | BETTER |
| Spain-LaLiga | 469 | 0.6358 | 0.6674 | 0.6812 | base:0.6858 | -0.0499 | BETTER |
| Netherlands-ED | 387 | 0.6521 | 0.6253 | 0.6669 | base:0.6858 | -0.0336 | BETTER |
| England-Champ | 684 | 0.6523 | 0.6243 | 0.6201 | base:0.6858 | -0.0335 | BETTER |
| Italy-SB | 450 | 0.6523 | 0.6422 | 0.6301 | base:0.6858 | -0.0334 | BETTER |
| Spain-Segunda | 572 | 0.6524 | 0.6364 | 0.6350 | base:0.6858 | -0.0334 | BETTER |
| England-L2 | 690 | 0.6591 | 0.5913 | 0.6020 | base:0.6858 | -0.0267 | BETTER |
| France-L1 | 369 | 0.6627 | 0.6125 | 0.6415 | base:0.6858 | -0.0231 | BETTER |
| England-Conference | 707 | 0.6642 | 0.5955 | 0.6223 | base:0.6858 | -0.0216 | BETTER |
| England-L1 | 678 | 0.6701 | 0.6003 | 0.5945 | base:0.6858 | -0.0156 | BETTER |
| Germany-BL1 | 360 | 0.6718 | 0.6000 | 0.6287 | base:0.6858 | -0.0140 | BETTER |
| Scotland-Champ | 234 | 0.6724 | 0.6068 | 0.5314 | base:0.6858 | -0.0134 | BETTER |
| England-PL | 450 | 0.6801 | 0.5911 | 0.6097 | base:0.6858 | -0.0056 | BETTER |
| Scotland-Prem | 282 | 0.6824 | 0.6099 | 0.5990 | base:0.6858 | -0.0034 | INCONCLUSIVE |
| Scotland-L2 | 235 | 0.6825 | 0.5787 | 0.5781 | base:0.6858 | -0.0032 | INCONCLUSIVE |
| Germany-BL2 | 378 | 0.6996 | 0.5079 | 0.5359 | base:0.6858 | +0.0138 | WORSE |

### 2.5. Away O/U 0.5


| League | N | LogLoss | Acc | AUC | Baseline | ΔLogLoss | Status |
|---|---|---|---|---|---|---|---|
| Netherlands-ED | 387 | 0.5086 | 0.7829 | 0.6447 | base:0.6074 | -0.0988 | BETTER |
| Germany-BL1 | 360 | 0.5509 | 0.7444 | 0.6353 | base:0.6074 | -0.0565 | BETTER |
| England-Conference | 707 | 0.5546 | 0.7397 | 0.6295 | base:0.6074 | -0.0528 | BETTER |
| Scotland-L2 | 235 | 0.5651 | 0.7447 | 0.5841 | base:0.6074 | -0.0423 | BETTER |
| Portugal-Liga1 | 378 | 0.5737 | 0.6878 | 0.6878 | base:0.6074 | -0.0337 | BETTER |
| England-PL | 450 | 0.5745 | 0.7178 | 0.6259 | base:0.6074 | -0.0329 | BETTER |
| Scotland-L1 | 234 | 0.5772 | 0.7094 | 0.6356 | base:0.6074 | -0.0302 | BETTER |
| England-Champ | 684 | 0.5773 | 0.7251 | 0.5961 | base:0.6074 | -0.0301 | BETTER |
| Germany-BL2 | 378 | 0.5829 | 0.7302 | 0.5522 | base:0.6074 | -0.0245 | BETTER |
| Greece-SL | 284 | 0.5856 | 0.6514 | 0.6985 | base:0.6074 | -0.0218 | BETTER |
| Scotland-Prem | 282 | 0.5866 | 0.6702 | 0.7021 | base:0.6074 | -0.0208 | BETTER |
| Italy-SA | 450 | 0.5944 | 0.6889 | 0.6427 | base:0.6074 | -0.0130 | BETTER |
| Spain-LaLiga | 469 | 0.5950 | 0.6994 | 0.5982 | base:0.6074 | -0.0124 | BETTER |
| Spain-Segunda | 572 | 0.6050 | 0.6941 | 0.5885 | base:0.6074 | -0.0024 | INCONCLUSIVE |
| Italy-SB | 450 | 0.6066 | 0.6844 | 0.6071 | base:0.6074 | -0.0008 | INCONCLUSIVE |
| Turkey-SL | 378 | 0.6077 | 0.6667 | 0.6418 | base:0.6074 | +0.0003 | INCONCLUSIVE |
| England-L1 | 678 | 0.6089 | 0.6962 | 0.5929 | base:0.6074 | +0.0015 | INCONCLUSIVE |
| France-L2 | 386 | 0.6101 | 0.6969 | 0.5640 | base:0.6074 | +0.0027 | INCONCLUSIVE |
| France-L1 | 369 | 0.6144 | 0.6829 | 0.6114 | base:0.6074 | +0.0070 | WORSE |
| Belgium-JPL | 383 | 0.6157 | 0.6893 | 0.5894 | base:0.6074 | +0.0083 | WORSE |
| England-L2 | 690 | 0.6208 | 0.6884 | 0.5488 | base:0.6074 | +0.0134 | WORSE |
| Scotland-Champ | 234 | 0.6395 | 0.6325 | 0.6160 | base:0.6074 | +0.0321 | WORSE |

### 2.6. Away O/U 1.5


| League | N | LogLoss | Acc | AUC | Baseline | ΔLogLoss | Status |
|---|---|---|---|---|---|---|---|
| Greece-SL | 284 | 0.5800 | 0.7148 | 0.6851 | base:0.6494 | -0.0694 | BETTER |
| Spain-LaLiga | 469 | 0.5913 | 0.7058 | 0.6562 | base:0.6494 | -0.0581 | BETTER |
| Portugal-Liga1 | 378 | 0.5959 | 0.7011 | 0.7109 | base:0.6494 | -0.0535 | BETTER |
| Italy-SB | 450 | 0.5984 | 0.6933 | 0.6196 | base:0.6494 | -0.0511 | BETTER |
| Scotland-Champ | 234 | 0.6001 | 0.7094 | 0.5929 | base:0.6494 | -0.0493 | BETTER |
| Turkey-SL | 378 | 0.6112 | 0.6693 | 0.6621 | base:0.6494 | -0.0382 | BETTER |
| Spain-Segunda | 572 | 0.6129 | 0.6818 | 0.5847 | base:0.6494 | -0.0365 | BETTER |
| England-Champ | 684 | 0.6172 | 0.6754 | 0.6177 | base:0.6494 | -0.0322 | BETTER |
| Scotland-L1 | 234 | 0.6219 | 0.6923 | 0.5978 | base:0.6494 | -0.0275 | BETTER |
| Italy-SA | 450 | 0.6250 | 0.6689 | 0.6453 | base:0.6494 | -0.0244 | BETTER |
| Scotland-Prem | 282 | 0.6250 | 0.6348 | 0.6605 | base:0.6494 | -0.0244 | BETTER |
| Belgium-JPL | 383 | 0.6273 | 0.6371 | 0.6462 | base:0.6494 | -0.0221 | BETTER |
| England-L1 | 678 | 0.6282 | 0.6652 | 0.5905 | base:0.6494 | -0.0212 | BETTER |
| Germany-BL1 | 360 | 0.6297 | 0.6694 | 0.6832 | base:0.6494 | -0.0197 | BETTER |
| England-L2 | 690 | 0.6304 | 0.6391 | 0.5969 | base:0.6494 | -0.0190 | BETTER |
| France-L1 | 369 | 0.6356 | 0.6531 | 0.6021 | base:0.6494 | -0.0138 | BETTER |
| England-PL | 450 | 0.6380 | 0.6244 | 0.5925 | base:0.6494 | -0.0114 | BETTER |
| France-L2 | 386 | 0.6486 | 0.6244 | 0.5715 | base:0.6494 | -0.0008 | INCONCLUSIVE |
| England-Conference | 707 | 0.6509 | 0.6379 | 0.6161 | base:0.6494 | +0.0015 | INCONCLUSIVE |
| Germany-BL2 | 378 | 0.6543 | 0.6376 | 0.5761 | base:0.6494 | +0.0049 | INCONCLUSIVE |
| Scotland-L2 | 235 | 0.6586 | 0.6383 | 0.5730 | base:0.6494 | +0.0092 | WORSE |
| Netherlands-ED | 387 | 0.6615 | 0.6253 | 0.6519 | base:0.6494 | +0.0121 | WORSE |

## 3. Cross-Market League Ranking


**Ranking berdasarkan Δlogloss** (model - baseline), diurutkan dari peningkatan terbesar (paling negatif = model lebih baik).


**Hanya untuk pasar dengan baseline odds.** Untuk Home/Away O/U (tanpa odds), lihat Section 2.


### 1X2


Baseline odds logloss (global): 1.0025


| Rank | League | N | LogLoss | ΔLogLoss | Verdict |
|---|---|---|---|---|---|
| 1 | Portugal-Liga1 | 378 | 0.9216 | -0.0809 | BETTER |
| 2 | Greece-SL | 284 | 0.9501 | -0.0524 | BETTER |
| 3 | Spain-LaLiga | 469 | 0.9672 | -0.0353 | BETTER |
| 4 | France-L1 | 369 | 0.9777 | -0.0249 | BETTER |
| 5 | Italy-SA | 450 | 0.9783 | -0.0242 | BETTER |
| 6 | Scotland-Prem | 282 | 0.9824 | -0.0201 | BETTER |
| 7 | Turkey-SL | 378 | 0.9866 | -0.0160 | BETTER |
| 8 | Germany-BL1 | 360 | 0.9874 | -0.0152 | BETTER |
| 9 | Netherlands-ED | 387 | 0.9921 | -0.0104 | BETTER |
| 10 | England-Conference | 707 | 0.9989 | -0.0036 | INCONCLUSIVE |
| 11 | Scotland-L1 | 234 | 0.9995 | -0.0030 | INCONCLUSIVE |
| 12 | Belgium-JPL | 383 | 1.0112 | +0.0087 | WORSE |
| 13 | England-PL | 450 | 1.0257 | +0.0232 | WORSE |
| 14 | Italy-SB | 450 | 1.0359 | +0.0333 | WORSE |
| 15 | England-L1 | 678 | 1.0399 | +0.0374 | WORSE |
| 16 | Spain-Segunda | 572 | 1.0416 | +0.0391 | WORSE |
| 17 | England-L2 | 690 | 1.0498 | +0.0473 | WORSE |
| 18 | Germany-BL2 | 378 | 1.0507 | +0.0482 | WORSE |
| 19 | England-Champ | 684 | 1.0511 | +0.0485 | WORSE |
| 20 | Scotland-Champ | 234 | 1.0678 | +0.0653 | WORSE |
| 21 | France-L2 | 386 | 1.0682 | +0.0657 | WORSE |
| 22 | Scotland-L2 | 235 | 1.0713 | +0.0688 | WORSE |

### OU 2.5


Baseline odds logloss (global): 0.6781


| Rank | League | N | LogLoss | ΔLogLoss | Verdict |
|---|---|---|---|---|---|
| 1 | Germany-BL1 | 360 | 0.6438 | -0.0343 | BETTER |
| 2 | Netherlands-ED | 387 | 0.6544 | -0.0237 | BETTER |
| 3 | Turkey-SL | 378 | 0.6626 | -0.0155 | BETTER |
| 4 | France-L1 | 369 | 0.6660 | -0.0122 | BETTER |
| 5 | Spain-LaLiga | 469 | 0.6723 | -0.0058 | BETTER |
| 6 | Portugal-Liga1 | 378 | 0.6739 | -0.0043 | INCONCLUSIVE |
| 7 | England-Conference | 707 | 0.6739 | -0.0043 | INCONCLUSIVE |
| 8 | Scotland-L2 | 235 | 0.6790 | +0.0009 | INCONCLUSIVE |
| 9 | France-L2 | 386 | 0.6791 | +0.0009 | INCONCLUSIVE |
| 10 | Spain-Segunda | 572 | 0.6830 | +0.0049 | INCONCLUSIVE |
| 11 | Germany-BL2 | 378 | 0.6843 | +0.0061 | WORSE |
| 12 | England-L1 | 678 | 0.6862 | +0.0080 | WORSE |
| 13 | Italy-SB | 450 | 0.6872 | +0.0090 | WORSE |
| 14 | Greece-SL | 284 | 0.6887 | +0.0105 | WORSE |
| 15 | Scotland-L1 | 234 | 0.6914 | +0.0133 | WORSE |
| 16 | England-PL | 450 | 0.6915 | +0.0133 | WORSE |
| 17 | England-Champ | 684 | 0.6919 | +0.0137 | WORSE |
| 18 | Scotland-Prem | 282 | 0.6945 | +0.0164 | WORSE |
| 19 | England-L2 | 690 | 0.6952 | +0.0170 | WORSE |
| 20 | Belgium-JPL | 383 | 0.6952 | +0.0171 | WORSE |
| 21 | Italy-SA | 450 | 0.6967 | +0.0185 | WORSE |
| 22 | Scotland-Champ | 234 | 0.7125 | +0.0344 | WORSE |

## 4. Per-Season Summary


**Catatan:** Season di sini adalah **tahun kalender** (dari `Date.dt.year`), bukan season code (`2122`, `2223`, dll.). Ini karena implementasi `backtest.py` menggunakan `Date.dt.year`. Perhatikan keterbatasan ini saat interpretasi.


### 4.1. 1X2


| Year | N | LogLoss | Acc | ΔLogLoss | Status |
|---|---|---|---|---|---|
| 2025 | 3729 | 1.0200 | 0.4961 | +0.0175 | WORSE |
| 2026 | 5709 | 1.0105 | 0.5059 | +0.0080 | WORSE |

### 4.2. OU 2.5


| Year | N | LogLoss | Acc | ΔLogLoss | Status |
|---|---|---|---|---|---|
| 2025 | 3729 | 0.6859 | 0.5564 | +0.0078 | WORSE |
| 2026 | 5709 | 0.6795 | 0.5612 | +0.0014 | INCONCLUSIVE |

### 4.3. Home O/U 0.5


| Year | N | LogLoss | Acc | ΔLogLoss | Status |
|---|---|---|---|---|---|
| 2025 | 3729 | 0.5237 | 0.7675 | -0.0095 | BETTER |
| 2026 | 5709 | 0.5058 | 0.7798 | -0.0274 | BETTER |

### 4.4. Home O/U 1.5


| Year | N | LogLoss | Acc | ΔLogLoss | Status |
|---|---|---|---|---|---|
| 2025 | 3729 | 0.6496 | 0.6254 | -0.0361 | BETTER |
| 2026 | 5709 | 0.6568 | 0.6169 | -0.0290 | BETTER |

### 4.5. Away O/U 0.5


| Year | N | LogLoss | Acc | ΔLogLoss | Status |
|---|---|---|---|---|---|
| 2025 | 3729 | 0.5948 | 0.6988 | -0.0126 | BETTER |
| 2026 | 5709 | 0.5857 | 0.7064 | -0.0217 | BETTER |

### 4.6. Away O/U 1.5


| Year | N | LogLoss | Acc | ΔLogLoss | Status |
|---|---|---|---|---|---|
| 2025 | 3729 | 0.6182 | 0.6726 | -0.0312 | BETTER |
| 2026 | 5709 | 0.6300 | 0.6551 | -0.0194 | BETTER |

## 5. Coverage & Limitations


### Coverage: Markets with N ≥ 100


| Market | Total Leagues | Leagues N≥100 | Leagues N<100 |
|---|---|---|---|
| 1X2 | 22 | 22 | 0 |
| OU 2.5 | 22 | 22 | 0 |
| Home O/U 0.5 | 22 | 22 | 0 |
| Home O/U 1.5 | 22 | 22 | 0 |
| Away O/U 0.5 | 22 | 22 | 0 |
| Away O/U 1.5 | 22 | 22 | 0 |

### Limitations


1. **Per-league baseline = global baseline**: Baseline odds (untuk 1x2, ou25) dihitung global, bukan per-league. Ini karena `backtest.py` menyimpan baseline di level global, bukan per-league. Delta di tabel adalah `model_league_logloss - global_baseline_logloss` — ini mengasumsikan baseline odds konstan antar liga, yang mungkin tidak benar (liga dengan odds lebih efisien seharusnya punya baseline logloss lebih rendah).

2. **Threshold verdict 0.005 logloss**: Konservatif tapi tidak tervalidasi. Bisa beda kalau Anda mau threshold 0.01 atau 0.003.

3. **Per-season menggunakan tahun kalender**: Season code 2122, 2223, dst. tidak diekstrak. Ini karena `backtest.py` grouping by `Date.dt.year`. Kalender 2025 = split antara 2425 dan 2526 musim.

4. **Tidak ada bootstrap CI per-league**: CI 95% hanya di global. Per-league CI tidak dihitung. Delta di tabel adalah point estimate tanpa interval kepercayaan. Untuk liga dengan N kecil (100-500), ini tidak reliable.

5. **Tidak ada profitabilitas / bankroll simulation**: Laporan ini hanya logloss/brier/acc. Tidak ada ROI, tidak ada stake sizing.

6. **Closing odds bias (R2)**: Semua evaluasi odds-based (1x2, ou25) kena bias optimis karena closing odds tidak sama dengan opening odds live.

7. **League with N<100 in some markets but N>=100 in others**: Contoh E0 (Premier League) punya 380 match/musim → di test (14 bulan) mungkin punya N>500 di 1x2 tapi split ke beberapa liga? Tidak — test period mencakup partial season. Cek detail di Section 2.


## 6. Recommendations


### Liga/Pasar Layak Dipantau Lanjut

- **Germany-BL1**: Δ1x2=-0.0152, Δou25=-0.0343 — model > baseline di dua pasar dengan odds
- **Spain-LaLiga**: Δ1x2=-0.0353, Δou25=-0.0058 — model > baseline di dua pasar dengan odds
- **France-L1**: Δ1x2=-0.0249, Δou25=-0.0122 — model > baseline di dua pasar dengan odds
- **Netherlands-ED**: Δ1x2=-0.0104, Δou25=-0.0237 — model > baseline di dua pasar dengan odds
- **Turkey-SL**: Δ1x2=-0.0160, Δou25=-0.0155 — model > baseline di dua pasar dengan odds

### Liga/Pasar yang Lemah (Model Kalah dari Baseline)


| Market | League | N | ΔLogLoss |
|---|---|---|---|
| 1X2 | Scotland-L2 | 235 | +0.0688 |
| 1X2 | France-L2 | 386 | +0.0657 |
| 1X2 | Scotland-Champ | 234 | +0.0653 |
| 1X2 | England-Champ | 684 | +0.0485 |
| 1X2 | Germany-BL2 | 378 | +0.0482 |
| 1X2 | England-L2 | 690 | +0.0473 |
| 1X2 | Spain-Segunda | 572 | +0.0391 |
| 1X2 | England-L1 | 678 | +0.0374 |
| OU 2.5 | Scotland-Champ | 234 | +0.0344 |
| 1X2 | Italy-SB | 450 | +0.0333 |
| 1X2 | England-PL | 450 | +0.0232 |

### Kalibrasi Lanjutan


**Rekomendasi saya: lakukan kalibrasi per-pasar (bukan global).**

Alasan:
- Model **kalah tipis** dari odds di 1x2 (Δlogloss +0.0114) dan ou25 (+0.0038) — probabilitas belum tentu calibrated.
- Model **menang signifikan** di Home/Away O/U (Δlogloss -0.018 s/d -0.032) — signal kuat tapi kalibrasi belum diverifikasi.
- Kalibrasi per-market (Isotonic/Platt) bisa memperbaiki kedua kasus tanpa retrain.
- **Kalibrasi global** (satu kalibrasi untuk semua market) berisiko karena target berbeda.

**Jangan** interpretasikan hasil backtest ini sebagai "model layak untuk taruhan". Belum ada:
- Simulasi bankroll
- Pengujian odds opening vs closing
- Analisis ROI
