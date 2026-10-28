---
name: Model research isolation
description: User's scope and usage facts for improving the football prediction models.
---

The user says the existing model is built from team statistics in the database and its predictions have never been used for live betting. All model-refinement experiments, code, configurations, and outputs must stay under `new/`. Do not change the main training, feature, prediction, data, or model artifacts while searching for the best model. The requested markets are 1X2, match Over/Under 2.5, and home/away team-goal Over/Under 0.5 and 1.5.

**Why:** the user explicitly required isolation and described the model's current use.

**How to apply:** read main assets as reference only; run experiments and save results under `new/`; use historical walk-forward validation and, if needed, no-stakes paper tracking. Never imply live-bet validation or promote a candidate without explicit approval.
