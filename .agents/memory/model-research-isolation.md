---
name: Model research isolation
description: User's scope and usage facts for improving the football prediction models.
---

The user says the existing model is built from team statistics in the database and its predictions have never been used for live betting. The goal is to find a history-based model that could eventually be considered for real betting. All model-refinement experiments, code, configurations, and outputs must stay under `new/model_lab/`; do not change the main training, feature, prediction, data, or model artifacts during research. The requested markets are 1X2, match Over/Under 2.5, and home/away team-goal Over/Under 0.5 and 1.5. Compare every experiment against the main-script model and every lab candidate, include home/away H2H statistics, and report possible model bias/ambiguity rather than selecting by one headline score.

Untuk riset lanjutan, bandingkan setiap kandidat dengan model di script utama dan semua kandidat lab. Simulasikan skenario pertandingan dengan odds, termasuk heavy favorite/huge underdog, odds yang terpaut ekstrem (istilah lokal: odds banting/odds ketinggian), dan mismatched odds. Odds sintetis boleh dipakai, tetapi harus diberi label simulasi dan tidak disamakan dengan odds bookmaker atau bukti profitabilitas. Libatkan statistik H2H home/away. Buat laporan untuk setiap simulasi, analisis bias/ketidakpastian, dan catat kandidat terbaik per pasar beserta alasan dan batasannya agar agen berikutnya dapat melanjutkan tanpa menebak. Kandidat yang tercatat tetap di lab; pemindahan ke script utama adalah langkah terpisah dengan persetujuan eksplisit pengguna.

**Why:** the user explicitly required isolation, described the model's current use, and clarified that eventual real-betting use is the goal. The user also explicitly emphasized rerunning tests across all models with odds scenarios, H2H, per-simulation reports, and a durable per-market winner record for future agents.

**Why:** the user explicitly asked for comparisons against the main-script model and every lab candidate, synthetic odds scenarios, H2H home/away features, and per-market reports for future handoff.

**How to apply:** read main assets as reference only; run experiments and save results under `new/model_lab/`; compare the main-script model and all lab candidates per market on chronological data; label synthetic odds and scenario assumptions, including heavy-favorite/huge-underdog, extreme disparity, and mismatched-odds cases; include H2H home/away; report bias/uncertainty and limitations for each simulation; record protocol, metrics, and the per-market leader for handoff. Use prospective no-stakes tracking before readiness claims. Promote a candidate outside the lab only with explicit approval.
