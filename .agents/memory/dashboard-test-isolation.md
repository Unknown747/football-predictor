---
name: Dashboard test isolation
description: User's rule for testing dashboard HTML changes separately from the main page.
---

Test dashboard HTML changes in `new/index.html` first. Do not apply them to the main `index.html` before testing, so the production page is not damaged by an unverified change.

**Why:** the user explicitly asked to investigate dashboard bugs in a separate test page before touching the main file.

**How to apply:** for dashboard display or prediction-table issues, make and verify changes in `new/index.html` first; only move a proven fix to the main page after the test is complete.
