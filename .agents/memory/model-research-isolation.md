---
name: Model research isolation
description: User's scope and usage facts for improving the football prediction models.
---

The user says the existing model is built from team statistics in the database and its predictions have never been used for live betting. The goal is to find a history-based model that could eventually be considered for real betting. All model-refinement experiments, code, configurations, and outputs must stay under `new/`; do not change the main training, feature, prediction, data, or model artifacts during research. The requested markets are 1X2, match Over/Under 2.5, and home/away team-goal Over/Under 0.5 and 1.5.

Untuk riset lanjutan, bandingkan setiap kandidat dengan model di script utama dan semua kandidat lab. Simulasikan skenario pertandingan dengan odds, termasuk heavy favorite/huge underdog, odds yang terpaut ekstrem, dan mismatched odds. Odds sintetis boleh dipakai, tetapi harus diberi label simulasi dan tidak disamakan dengan odds bookmaker atau bukti profitabilitas. Libatkan statistik H2H home/away. Buat laporan untuk setiap simulasi dan catat kandidat terbaik per pasar agar agen berikutnya dapat melanjutkan tanpa menebak.

**Why:** the user explicitly required isolation, described the model's current use, and clarified that eventual real-betting use is the goal.

**Why:** the user explicitly asked for comparisons against the main-script model and every lab candidate, synthetic odds scenarios, H2H home/away features, and per-market reports for future handoff.

**How to apply:** read main assets as reference only; run experiments and save results under `new/model_lab/`; compare all candidates per market on chronological data; label synthetic odds and scenario assumptions; include H2H home/away; record protocol, metrics, limitations, and the per-market leader. Use prospective no-stakes tracking before readiness claims. Promote a candidate outside the lab only with explicit approval.
