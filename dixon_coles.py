#!/usr/bin/env python3
"""Dixon-Coles model: koreksi skor rendah + matriks probabilitas."""
import numpy as np
from scipy import stats

def tau(x, y, lam, mu, rho):
    """Faktor koreksi Dixon-Coles untuk 0-0, 1-0, 0-1, 1-1."""
    if x == 0 and y == 0:
        return 1 - lam * mu * rho
    if x == 0 and y == 1:
        return 1 + lam * rho
    if x == 1 and y == 0:
        return 1 + mu * rho
    if x == 1 and y == 1:
        return 1 - rho
    return 1.0

def score_matrix(lam, mu, max_goals=10, rho=-0.05):
    """Bangun matriks probabilitas skor N x N, renormalisasi."""
    n = max_goals + 1
    m = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            p = stats.poisson.pmf(i, lam) * stats.poisson.pmf(j, mu)
            m[i, j] = p * tau(i, j, lam, mu, rho)
    m = np.clip(m, 0, None)
    s = m.sum()
    if s > 0:
        m = m / s
    return m

def markets(lam, mu, max_goals=10, rho=-0.05):
    """Hitung probabilitas pasar dari matriks."""
    m = score_matrix(lam, mu, max_goals, rho)
    n = m.shape[0]
    home = sum(m[i, j] for i in range(n) for j in range(n) if i > j)
    draw = sum(m[i, i] for i in range(n))
    away = sum(m[i, j] for i in range(n) for j in range(n) if i < j)
    under25 = sum(m[i, j] for i in range(n) for j in range(n) if i + j <= 2)
    btts = sum(m[i, j] for i in range(1, n) for j in range(1, n))
    return {
        "home": home, "draw": draw, "away": away,
        "over25": 1 - under25, "under25": under25, "btts": btts,
    }

def fit_rho_from_matches(df, lam_col="lam", mu_col="mu", max_iter=50):
    """Estimasi rho via grid search kasar (bisa diganti scipy.optimize)."""
    rhos = np.linspace(-0.15, 0.05, 41)
    best_rho, best_ll = -0.05, -np.inf
    for rho in rhos:
        ll = 0.0
        ok = True
        for _, row in df.iterrows():
            hg, ag = int(row["FTHG"]), int(row["FTAG"])
            t = tau(hg, ag, row[lam_col], row[mu_col], rho)
            if t <= 0:
                ok = False; break
            ll += np.log(t) + stats.poisson.logpmf(hg, row[lam_col]) + stats.poisson.logpmf(ag, row[mu_col])
        if ok and ll > best_ll:
            best_ll, best_rho = ll, rho
    return best_rho, best_ll

if __name__ == "__main__":
    # Quick self-test
    m = markets(1.6, 1.2, rho=-0.05)
    print("Self-test markets (lam=1.6, mu=1.2, rho=-0.05):")
    for k, v in m.items():
        print(f"  {k}: {v:.4f}")
    print(f"  sum 1x2: {m['home']+m['draw']+m['away']:.6f}")
