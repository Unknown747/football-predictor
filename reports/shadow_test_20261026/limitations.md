# Limitations - Shadow Test Helper (L13.2B)

1. HELPER IMPLEMENTED: shadow_capture.py berfungsi sesuai API predict.py.
2. TECHNICAL TESTS: 11 kasus PASS (lihat run.log).
3. PROSPECTIVE SHADOW TEST: **NOT STARTED**. Helper belum dipakai untuk fixture mendatang.
4. Label SYNTHETIC_TEST_ONLY / HISTORICAL_FIXTURE wajib. Tidak untuk live.
5. Tidak ada fetch fixture otomatis. Tidak ada download odds.
6. Predictions tidak untuk taruhan. Tidak ada klaim profitabilitas.
7. Model hash diverifikasi sebelum predict. Mismatch = exit.
8. Immutable: shadow_predictions.csv tidak boleh diedit manual setelah capture.
