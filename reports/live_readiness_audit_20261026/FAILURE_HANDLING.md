# Audit Failure Handling

## Coverage Error States (dari predict.py)

1. INVALID_DATE
   - Trigger: date parse gagal
   - Output: NaN semua probabilities, status = INVALID_DATE
   - Test: T7 PASS

2. UNKNOWN_LEAGUE
   - Trigger: league tidak ada di master_canon
   - Output: NaN, status = UNKNOWN_LEAGUE
   - Test: T15 PASS

3. UNKNOWN_TEAM
   - Trigger: home/away tidak match canonical + fuzzy
   - Output: NaN, status = UNKNOWN_TEAM
   - Test: T2 PASS

4. INVALID_MATCH
   - Trigger: home == away
   - Output: NaN, status = INVALID_MATCH
   - Test: T8 PASS

5. DATE_NOT_IN_FUTURE
   - Trigger: date <= max(master_canon.Date)
   - Output: NaN, status = DATE_NOT_IN_FUTURE
   - Test: T9 PASS

6. INSUFFICIENT_HISTORY (warning, bukan fail)
   - Trigger: n_played < 5 atau < 10
   - Output: probabilities + warning_insufficient_history=True
   - Test: T3 PASS

## Determinisme
Run 2x dengan input sama -> output identik (test T12 PASS).

## Duplikasi Input
predict.py dedupe (date, home, away, league), simpan yang pertama.
Test: T6 PASS.

## Kesimpulan
- 6 error state terdefinisi
- Fail-closed pada invalid input
- Determinism: PASS
- Dedupe: PASS
