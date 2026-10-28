---
name: Model research isolation
description: User's scope and usage facts for improving the football prediction models.
---

The user says the existing model is built from team statistics in the database and its predictions have never been used for live betting. The goal is to find a history-based model that could eventually be considered for real betting. All model-refinement experiments, code, configurations, and outputs must stay under `new/`; do not change the main training, feature, prediction, data, or model artifacts during research. The requested markets are 1X2, match Over/Under 2.5, and home/away team-goal Over/Under 0.5 and 1.5.

**Why:** the user explicitly required isolation, described the model's current use, and clarified that eventual real-betting use is the goal.

**How to apply:** read main assets as reference only; run experiments and save results under `new/`; use chronological historical evaluation and prospective no-stakes tracking. Historical results alone do not establish live readiness or profitability. Promote a candidate outside the lab only with explicit approval.
