# Limitations - shadow_capture.py

1. Helper ini hanya VALIDASI TEKNIS. Label SYNTHETIC_TEST_ONLY atau HISTORICAL_FIXTURE
   berarti TIDAK untuk prediksi live.
2. Tidak ada fetch fixture otomatis. User harus supply CSV manual.
3. Tidak ada download odds otomatis. User supply odds manual (jika ada).
4. Predictions dari helper ini TIDAK untuk taruhan. Tidak ada klaim profitabilitas.
5. Timestamp capture di UTC. Tanggal kickoff mengikuti konvensi CSV input (YYYY-MM-DD).
6. Model hash diverifikasi sebelum predict. Jika mismatch, helper exit.
7. Probabilities NaN (fail-closed) jika input invalid. Tidak menebak.
8. Output immutable setelah capture: JANGAN edit shadow_predictions.csv manual.
