# League Baseline Audit — L10.4


Generated: 2026-10-26T22:02:43.305351


**Test**: 9438 rows, 22 leagues


**Base rates (train)**: {"ou25": 0.505688, "home_ou05": 0.765483, "home_ou15": 0.430638, "away_ou05": 0.686075, "away_ou15": 0.336631}


## 1X2


| League | N_model | N_common | Model LL | Baseline LL | Δ | CI 95% Δ | Verdict |
|---|---|---|---|---|---|---|---|
| Belgium-JPL | 383 | 0 | — | — | — | — | INSUFFICIENT N |
| England-Champ | 684 | 0 | — | — | — | — | INSUFFICIENT N |
| England-Conference | 707 | 0 | — | — | — | — | INSUFFICIENT N |
| England-L1 | 678 | 0 | — | — | — | — | INSUFFICIENT N |
| England-L2 | 690 | 0 | — | — | — | — | INSUFFICIENT N |
| England-PL | 450 | 0 | — | — | — | — | INSUFFICIENT N |
| France-L1 | 369 | 0 | — | — | — | — | INSUFFICIENT N |
| France-L2 | 386 | 0 | — | — | — | — | INSUFFICIENT N |
| Germany-BL1 | 360 | 0 | — | — | — | — | INSUFFICIENT N |
| Germany-BL2 | 378 | 0 | — | — | — | — | INSUFFICIENT N |
| Greece-SL | 284 | 0 | — | — | — | — | INSUFFICIENT N |
| Italy-SA | 450 | 0 | — | — | — | — | INSUFFICIENT N |
| Italy-SB | 450 | 0 | — | — | — | — | INSUFFICIENT N |
| Netherlands-ED | 387 | 0 | — | — | — | — | INSUFFICIENT N |
| Portugal-Liga1 | 378 | 0 | — | — | — | — | INSUFFICIENT N |
| Scotland-Champ | 234 | 0 | — | — | — | — | INSUFFICIENT N |
| Scotland-L1 | 234 | 0 | — | — | — | — | INSUFFICIENT N |
| Scotland-L2 | 235 | 0 | — | — | — | — | INSUFFICIENT N |
| Scotland-Prem | 282 | 0 | — | — | — | — | INSUFFICIENT N |
| Spain-LaLiga | 469 | 0 | — | — | — | — | INSUFFICIENT N |
| Spain-Segunda | 572 | 0 | — | — | — | — | INSUFFICIENT N |
| Turkey-SL | 378 | 0 | — | — | — | — | INSUFFICIENT N |

## OU 2.5


| League | N_model | N_common | Model LL | Baseline LL | Δ | CI 95% Δ | Verdict |
|---|---|---|---|---|---|---|---|
| Belgium-JPL | 383 | 0 | — | — | — | — | INSUFFICIENT N |
| England-Champ | 684 | 0 | — | — | — | — | INSUFFICIENT N |
| England-Conference | 707 | 0 | — | — | — | — | INSUFFICIENT N |
| England-L1 | 678 | 0 | — | — | — | — | INSUFFICIENT N |
| England-L2 | 690 | 0 | — | — | — | — | INSUFFICIENT N |
| England-PL | 450 | 0 | — | — | — | — | INSUFFICIENT N |
| France-L1 | 369 | 0 | — | — | — | — | INSUFFICIENT N |
| France-L2 | 386 | 0 | — | — | — | — | INSUFFICIENT N |
| Germany-BL1 | 360 | 0 | — | — | — | — | INSUFFICIENT N |
| Germany-BL2 | 378 | 0 | — | — | — | — | INSUFFICIENT N |
| Greece-SL | 284 | 0 | — | — | — | — | INSUFFICIENT N |
| Italy-SA | 450 | 0 | — | — | — | — | INSUFFICIENT N |
| Italy-SB | 450 | 0 | — | — | — | — | INSUFFICIENT N |
| Netherlands-ED | 387 | 0 | — | — | — | — | INSUFFICIENT N |
| Portugal-Liga1 | 378 | 0 | — | — | — | — | INSUFFICIENT N |
| Scotland-Champ | 234 | 0 | — | — | — | — | INSUFFICIENT N |
| Scotland-L1 | 234 | 0 | — | — | — | — | INSUFFICIENT N |
| Scotland-L2 | 235 | 0 | — | — | — | — | INSUFFICIENT N |
| Scotland-Prem | 282 | 0 | — | — | — | — | INSUFFICIENT N |
| Spain-LaLiga | 469 | 0 | — | — | — | — | INSUFFICIENT N |
| Spain-Segunda | 572 | 0 | — | — | — | — | INSUFFICIENT N |
| Turkey-SL | 378 | 0 | — | — | — | — | INSUFFICIENT N |

## Home O/U 0.5


| League | N_model | N_common | Model LL | Baseline LL | Δ | CI 95% Δ | Verdict |
|---|---|---|---|---|---|---|---|
| Portugal-Liga1 | 378 | 378 | 0.5296 | 0.5771 | -0.0475 | [-0.0701, -0.0287] | BETTER |
| Italy-SA | 450 | 450 | 0.5805 | 0.6195 | -0.0390 | [-0.0578, -0.0213] | BETTER |
| Netherlands-ED | 387 | 387 | 0.4209 | 0.4568 | -0.0358 | [-0.0498, -0.0220] | BETTER |
| Scotland-L1 | 234 | 234 | 0.5505 | 0.5857 | -0.0352 | [-0.0556, -0.0135] | BETTER |
| Turkey-SL | 378 | 378 | 0.5098 | 0.5427 | -0.0329 | [-0.0494, -0.0170] | BETTER |
| Greece-SL | 284 | 284 | 0.5513 | 0.5838 | -0.0325 | [-0.0557, -0.0080] | BETTER |
| Germany-BL1 | 360 | 360 | 0.4421 | 0.4743 | -0.0322 | [-0.0472, -0.0176] | BETTER |
| France-L1 | 369 | 369 | 0.5066 | 0.5333 | -0.0268 | [-0.0474, -0.0043] | BETTER |
| Spain-LaLiga | 469 | 469 | 0.4587 | 0.4842 | -0.0255 | [-0.0381, -0.0134] | BETTER |
| England-Conference | 707 | 707 | 0.4878 | 0.5115 | -0.0237 | [-0.0343, -0.0118] | BETTER |
| England-PL | 450 | 450 | 0.5236 | 0.5459 | -0.0223 | [-0.0365, -0.0079] | BETTER |
| Scotland-Prem | 282 | 282 | 0.5006 | 0.5189 | -0.0183 | [-0.0363, -0.0010] | BETTER |
| England-L2 | 690 | 690 | 0.5204 | 0.5364 | -0.0160 | [-0.0256, -0.0063] | BETTER |
| Scotland-Champ | 234 | 234 | 0.6104 | 0.6262 | -0.0158 | [-0.0356, +0.0031] | INCONCLUSIVE |
| Spain-Segunda | 572 | 572 | 0.5301 | 0.5444 | -0.0143 | [-0.0237, -0.0039] | BETTER |
| Belgium-JPL | 383 | 383 | 0.5354 | 0.5483 | -0.0129 | [-0.0247, -0.0004] | BETTER |
| Germany-BL2 | 378 | 378 | 0.4798 | 0.4926 | -0.0128 | [-0.0228, -0.0023] | BETTER |
| England-L1 | 678 | 678 | 0.5174 | 0.5272 | -0.0098 | [-0.0208, +0.0014] | INCONCLUSIVE |
| France-L2 | 386 | 386 | 0.5791 | 0.5860 | -0.0068 | [-0.0221, +0.0085] | INCONCLUSIVE |
| Italy-SB | 450 | 450 | 0.4903 | 0.4960 | -0.0056 | [-0.0194, +0.0071] | INCONCLUSIVE |
| Scotland-L2 | 235 | 235 | 0.4736 | 0.4787 | -0.0050 | [-0.0222, +0.0155] | INCONCLUSIVE |
| England-Champ | 684 | 684 | 0.5227 | 0.5249 | -0.0023 | [-0.0112, +0.0071] | INCONCLUSIVE |

## Home O/U 1.5


| League | N_model | N_common | Model LL | Baseline LL | Δ | CI 95% Δ | Verdict |
|---|---|---|---|---|---|---|---|
| Portugal-Liga1 | 378 | 378 | 0.6080 | 0.6844 | -0.0764 | [-0.1065, -0.0480] | BETTER |
| Netherlands-ED | 387 | 387 | 0.6521 | 0.7162 | -0.0641 | [-0.0952, -0.0322] | BETTER |
| Spain-LaLiga | 469 | 469 | 0.6358 | 0.6913 | -0.0554 | [-0.0808, -0.0279] | BETTER |
| Turkey-SL | 378 | 378 | 0.6324 | 0.6837 | -0.0512 | [-0.0744, -0.0269] | BETTER |
| Belgium-JPL | 383 | 383 | 0.6330 | 0.6835 | -0.0505 | [-0.0688, -0.0323] | BETTER |
| Italy-SA | 450 | 450 | 0.6223 | 0.6712 | -0.0489 | [-0.0774, -0.0182] | BETTER |
| Scotland-L1 | 234 | 234 | 0.6305 | 0.6790 | -0.0485 | [-0.0808, -0.0192] | BETTER |
| Greece-SL | 284 | 284 | 0.6308 | 0.6783 | -0.0475 | [-0.0804, -0.0140] | BETTER |
| Germany-BL1 | 360 | 360 | 0.6718 | 0.7114 | -0.0396 | [-0.0657, -0.0140] | BETTER |
| France-L2 | 386 | 386 | 0.6341 | 0.6652 | -0.0311 | [-0.0511, -0.0118] | BETTER |
| France-L1 | 369 | 369 | 0.6627 | 0.6934 | -0.0307 | [-0.0627, -0.0023] | BETTER |
| Italy-SB | 450 | 450 | 0.6523 | 0.6824 | -0.0300 | [-0.0467, -0.0139] | BETTER |
| England-Conference | 707 | 707 | 0.6642 | 0.6904 | -0.0262 | [-0.0424, -0.0107] | BETTER |
| Spain-Segunda | 572 | 572 | 0.6524 | 0.6780 | -0.0256 | [-0.0416, -0.0064] | BETTER |
| England-Champ | 684 | 684 | 0.6523 | 0.6771 | -0.0249 | [-0.0417, -0.0059] | BETTER |
| England-PL | 450 | 450 | 0.6801 | 0.6998 | -0.0196 | [-0.0440, +0.0056] | INCONCLUSIVE |
| England-L2 | 690 | 690 | 0.6591 | 0.6737 | -0.0146 | [-0.0303, +0.0031] | INCONCLUSIVE |
| England-L1 | 678 | 678 | 0.6701 | 0.6814 | -0.0113 | [-0.0296, +0.0070] | INCONCLUSIVE |
| Scotland-L2 | 235 | 235 | 0.6825 | 0.6928 | -0.0102 | [-0.0349, +0.0167] | INCONCLUSIVE |
| Scotland-Prem | 282 | 282 | 0.6824 | 0.6920 | -0.0096 | [-0.0448, +0.0228] | INCONCLUSIVE |
| Germany-BL2 | 378 | 378 | 0.6996 | 0.7058 | -0.0063 | [-0.0258, +0.0142] | INCONCLUSIVE |
| Scotland-Champ | 234 | 234 | 0.6724 | 0.6706 | +0.0017 | [-0.0303, +0.0346] | INCONCLUSIVE |

## Away O/U 0.5


| League | N_model | N_common | Model LL | Baseline LL | Δ | CI 95% Δ | Verdict |
|---|---|---|---|---|---|---|---|
| Greece-SL | 284 | 284 | 0.5856 | 0.6355 | -0.0499 | [-0.0752, -0.0215] | BETTER |
| Portugal-Liga1 | 378 | 378 | 0.5737 | 0.6229 | -0.0492 | [-0.0664, -0.0313] | BETTER |
| Scotland-Prem | 282 | 282 | 0.5866 | 0.6318 | -0.0452 | [-0.0632, -0.0243] | BETTER |
| Netherlands-ED | 387 | 387 | 0.5086 | 0.5505 | -0.0419 | [-0.0576, -0.0274] | BETTER |
| Italy-SA | 450 | 450 | 0.5944 | 0.6217 | -0.0273 | [-0.0488, -0.0072] | BETTER |
| Germany-BL1 | 360 | 360 | 0.5509 | 0.5766 | -0.0257 | [-0.0440, -0.0077] | BETTER |
| England-Conference | 707 | 707 | 0.5546 | 0.5791 | -0.0245 | [-0.0377, -0.0122] | BETTER |
| Turkey-SL | 378 | 378 | 0.6077 | 0.6312 | -0.0234 | [-0.0429, -0.0030] | BETTER |
| England-PL | 450 | 450 | 0.5745 | 0.5957 | -0.0212 | [-0.0390, -0.0047] | BETTER |
| Scotland-L1 | 234 | 234 | 0.5772 | 0.5973 | -0.0201 | [-0.0430, +0.0017] | INCONCLUSIVE |
| Italy-SB | 450 | 450 | 0.6066 | 0.6252 | -0.0186 | [-0.0303, -0.0073] | BETTER |
| Scotland-L2 | 235 | 235 | 0.5651 | 0.5830 | -0.0180 | [-0.0426, +0.0079] | INCONCLUSIVE |
| Scotland-Champ | 234 | 234 | 0.6395 | 0.6574 | -0.0179 | [-0.0402, +0.0041] | INCONCLUSIVE |
| France-L1 | 369 | 369 | 0.6144 | 0.6289 | -0.0145 | [-0.0351, +0.0089] | INCONCLUSIVE |
| Spain-LaLiga | 469 | 469 | 0.5950 | 0.6068 | -0.0119 | [-0.0306, +0.0071] | INCONCLUSIVE |
| England-L1 | 678 | 678 | 0.6089 | 0.6201 | -0.0112 | [-0.0222, -0.0009] | BETTER |
| Belgium-JPL | 383 | 383 | 0.6157 | 0.6238 | -0.0080 | [-0.0255, +0.0109] | INCONCLUSIVE |
| Spain-Segunda | 572 | 572 | 0.6050 | 0.6119 | -0.0069 | [-0.0211, +0.0068] | INCONCLUSIVE |
| Germany-BL2 | 378 | 378 | 0.5829 | 0.5877 | -0.0048 | [-0.0238, +0.0171] | INCONCLUSIVE |
| England-Champ | 684 | 684 | 0.5773 | 0.5814 | -0.0041 | [-0.0194, +0.0109] | INCONCLUSIVE |
| France-L2 | 386 | 386 | 0.6101 | 0.6137 | -0.0036 | [-0.0165, +0.0104] | INCONCLUSIVE |
| England-L2 | 690 | 690 | 0.6208 | 0.6192 | +0.0016 | [-0.0086, +0.0116] | INCONCLUSIVE |

## Away O/U 1.5


| League | N_model | N_common | Model LL | Baseline LL | Δ | CI 95% Δ | Verdict |
|---|---|---|---|---|---|---|---|
| Portugal-Liga1 | 378 | 378 | 0.5959 | 0.6617 | -0.0657 | [-0.0893, -0.0416] | BETTER |
| Netherlands-ED | 387 | 387 | 0.6615 | 0.7207 | -0.0592 | [-0.0881, -0.0282] | BETTER |
| Germany-BL1 | 360 | 360 | 0.6297 | 0.6836 | -0.0539 | [-0.0741, -0.0314] | BETTER |
| Greece-SL | 284 | 284 | 0.5800 | 0.6278 | -0.0477 | [-0.0763, -0.0207] | BETTER |
| Turkey-SL | 378 | 378 | 0.6112 | 0.6473 | -0.0361 | [-0.0585, -0.0153] | BETTER |
| Spain-LaLiga | 469 | 469 | 0.5913 | 0.6274 | -0.0360 | [-0.0579, -0.0143] | BETTER |
| Scotland-Prem | 282 | 282 | 0.6250 | 0.6606 | -0.0356 | [-0.0602, -0.0088] | BETTER |
| Italy-SA | 450 | 450 | 0.6250 | 0.6561 | -0.0311 | [-0.0499, -0.0126] | BETTER |
| England-Conference | 707 | 707 | 0.6509 | 0.6791 | -0.0282 | [-0.0491, -0.0087] | BETTER |
| Belgium-JPL | 383 | 383 | 0.6273 | 0.6548 | -0.0276 | [-0.0507, -0.0069] | BETTER |
| Italy-SB | 450 | 450 | 0.5984 | 0.6184 | -0.0201 | [-0.0338, -0.0061] | BETTER |
| England-Champ | 684 | 684 | 0.6172 | 0.6365 | -0.0194 | [-0.0353, -0.0037] | BETTER |
| France-L1 | 369 | 369 | 0.6356 | 0.6494 | -0.0138 | [-0.0387, +0.0093] | INCONCLUSIVE |
| Spain-Segunda | 572 | 572 | 0.6129 | 0.6263 | -0.0134 | [-0.0250, -0.0015] | BETTER |
| England-L2 | 690 | 690 | 0.6304 | 0.6405 | -0.0101 | [-0.0214, +0.0019] | INCONCLUSIVE |
| Germany-BL2 | 378 | 378 | 0.6543 | 0.6635 | -0.0091 | [-0.0324, +0.0143] | INCONCLUSIVE |
| Scotland-L2 | 235 | 235 | 0.6586 | 0.6673 | -0.0087 | [-0.0342, +0.0156] | INCONCLUSIVE |
| England-L1 | 678 | 678 | 0.6282 | 0.6365 | -0.0083 | [-0.0239, +0.0065] | INCONCLUSIVE |
| England-PL | 450 | 450 | 0.6380 | 0.6456 | -0.0076 | [-0.0320, +0.0183] | INCONCLUSIVE |
| France-L2 | 386 | 386 | 0.6486 | 0.6547 | -0.0061 | [-0.0225, +0.0112] | INCONCLUSIVE |
| Scotland-L1 | 234 | 234 | 0.6219 | 0.6278 | -0.0060 | [-0.0342, +0.0221] | INCONCLUSIVE |
| Scotland-Champ | 234 | 234 | 0.6001 | 0.6047 | -0.0046 | [-0.0287, +0.0219] | INCONCLUSIVE |

## Cross-League Ranking (1X2 & OU 2.5)


**Sort by ΔLogLoss** (ascending, negative = model better).


### 1X2


| Rank | League | N_common | ΔLogLoss | CI 95% Δ | Verdict |
|---|---|---|---|---|---|

### OU 2.5


| Rank | League | N_common | ΔLogLoss | CI 95% Δ | Verdict |
|---|---|---|---|---|---|