"""Engine test suite -- headless, no display required.

28 checks over CalibrationEngine: the numerically stable quadratic inversion,
input-file validation, a full 10 000-iteration calibration, Monte Carlo
reproducibility, the empty-MC guard, and the vectorised confidence bands.

    python verify/verify_v4.py        # expect 28 PASS, "ALL CHECKS PASSED"

Count the PASS lines, not the verdict: fewer than 28 means an incomplete
environment, not a healthy project.  Exits non-zero on any failure.

If your console is not UTF-8, run with PYTHONIOENCODING=utf-8 PYTHONUTF8=1 --
this prints non-ASCII and dies partway through on cp1252, which looks exactly
like a broken project.
"""
import sys, os, io, time
from pathlib import Path
import numpy as np

# Derive the repo root from this script's own location: verify/ lives inside
# the repo, so the parent of this file's directory IS the root.  Previously
# both paths were hardcoded absolutes, which meant every machine that received
# this project had to edit two lines in each script before the baseline could
# run at all -- and forgetting to was indistinguishable from a broken install.
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import matplotlib
matplotlib.use("Agg")            # no GUI needed for engine tests
import ra226_gui as G

DATA = str(REPO / "226Ra_En_Area.txt")
fails = []
def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {extra}")
    if not cond: fails.append(name)

# ── 1. Quadratic inverter: stability as c → 0 ────────────────────────────
# ch = 10 + 2E + cE²  at E=500 → ch = 10+1000+c*250000
for c in (1e-7, 1e-12, 1e-20, 0.0, -1e-12):
    ch = 10 + 2*500 + c*500**2
    ref = (ch - 10) / 2.0
    E = float(G._invert_quadratic(10.0, 2.0, c, ch, ref))
    check(f"inv_quad c={c:g}", np.isfinite(E) and abs(E - 500) < 1e-3,
          f"E={E!r} (want 500)")

# Vectorised, with c straddling zero — the case that produced inf before
cs  = np.linspace(-1e-9, 1e-9, 2001)
chs = 10 + 2*500 + cs*500**2
refs = (chs - 10)/2.0
Ev = G._invert_quadratic(np.full_like(cs,10.0), np.full_like(cs,2.0), cs, chs, refs)
check("inv_quad vector straddling c=0",
      np.all(np.isfinite(Ev)) and np.allclose(Ev, 500, atol=1e-3),
      f"finite={np.isfinite(Ev).sum()}/{len(Ev)}, max|E-500|={np.nanmax(np.abs(Ev-500)):.2e}")

# Negative discriminant → NaN, not a crash
check("inv_quad neg discriminant is NaN",
      np.isnan(float(G._invert_quadratic(0.0, 0.0, 1.0, -5.0, 0.0))))

# ── 2. Validation rejects malformed files ────────────────────────────────
good = np.loadtxt(DATA)
def try_load(arr, label):
    p = os.path.join(os.environ["TEMP"], f"_v4_{label}.txt")
    np.savetxt(p, arr)
    eng = G.CalibrationEngine()
    try:
        eng.load(p); return None
    except ValueError as e:
        return str(e).splitlines()[0]
    finally:
        os.remove(p)

check("valid file loads", try_load(good, "good") is None)
bad = good.copy(); bad[3,1] = 0.0
check("rejects dch=0",  try_load(bad, "dch") is not None, try_load(bad,"dch") or "")
bad = good.copy(); bad[2,4] = -5.0
check("rejects E<=0",   try_load(bad, "E") is not None,   try_load(bad,"E") or "")
bad = good.copy(); bad[1,5] = 0.0
check("rejects I<=0",   try_load(bad, "I") is not None,   try_load(bad,"I") or "")
bad = good.copy(); bad[0,2] = -1.0
check("rejects N<=0",   try_load(bad, "N") is not None,   try_load(bad,"N") or "")
bad = good.copy(); bad[4,3] = 0.0; bad[4,6] = 0.0
check("rejects dN=dI=0",try_load(bad,"dz") is not None,   try_load(bad,"dz") or "")
check("rejects too few rows", try_load(good[:3], "few") is not None,
      try_load(good[:3],"few") or "")

# ── 3. Full calibration on the real file ─────────────────────────────────
eng = G.CalibrationEngine()
eng.load(DATA)
print(f"\n  loaded n={eng.n}  E={eng.E.min():.1f}-{eng.E.max():.1f} keV")
t0 = time.time(); eng.calibrate(); t_en = time.time()-t0
check("energy calibrate", eng.cal_ready, f"{t_en:.2f}s  B1={eng.birge1:.3f} B2={eng.birge2:.3f}")
t0 = time.time(); eng.calibrate_efficiency(); t_ef = time.time()-t0
check("efficiency calibrate", eng.eff_ready,
      f"{t_ef:.1f}s  KRF ok={eng.mc_krf_ok} RW ok={eng.mc_rw_ok} bad={eng.mc_bad}")
check("params_eff is 2-D", eng.params_eff.ndim == 2, str(eng.params_eff.shape))

# ── 4. predict() reproducibility (issue #1) ──────────────────────────────
r1 = eng.predict(2000.0, 0.5)
r2 = eng.predict(2000.0, 0.5)
check("predict is reproducible", r1 == r2, f"{r1[0]:.6f} vs {r2[0]:.6f}")
check("predict values finite", all(np.isfinite(v) for v in r1),
      f"E_lin={r1[0]:.3f}±{r1[1]:.3f}  E_quad={r1[2]:.3f}±{r1[3]:.3f}")

r3 = eng.predict(1000.0, 0.5)
check("different input -> different result", r3[0] != r1[0], f"{r3[0]:.3f}")

# ── 5. predict_efficiency ────────────────────────────────────────────────
pe = eng.predict_efficiency(1000.0)
check("predict_efficiency finite", np.isfinite(pe[0]) and np.isfinite(pe[1]),
      f"KRF={pe[0]:.4g}+-{pe[1]:.4g}  RW={pe[3]:.4g}+-{pe[4]:.4g}")
# Wild extrapolation must not raise
for Ex in (0.001, 1e6):
    try:
        v = eng.predict_efficiency(Ex); ok = True
    except Exception as ex:
        ok = False; v = ex
    check(f"predict_efficiency E={Ex:g} no crash", ok, str(v)[:60])

# ── 6. Empty-MC guard (issue #4) ─────────────────────────────────────────
saved = eng.params_eff
eng.params_eff = np.empty((0, 4))
try:
    pe0 = eng.predict_efficiency(1000.0); ok = np.isnan(pe0[0])
except Exception as ex:
    ok = False; pe0 = ex
check("empty params_eff -> NaN not crash", ok, str(pe0)[:60])
eng.params_eff = saved

# ── 7. Vectorised band == old per-sample loop ────────────────────────────
E_g = np.linspace(eng.E.min()*0.96, eng.E.max()*1.02, 400)
p = eng.params_eff[:200]
old = np.array([G.f_krf(E_g, *pp) for pp in p])
new = G.f_krf(E_g[None, :], p[:,0:1], p[:,1:2], p[:,2:3], p[:,3:4])
check("KRF band vectorised == loop", np.allclose(old, new, equal_nan=True),
      f"maxdiff={np.nanmax(np.abs(old-new)):.3e}")
pr = eng.params_radware[:200]
oldr = np.array([G.f_radware_5p(E_g, *pp) for pp in pr])
newr = G.f_radware_5p(E_g[None,:], pr[:,0:1], pr[:,1:2], pr[:,2:3], pr[:,3:4], pr[:,4:5])
check("Radware band vectorised == loop", np.allclose(oldr, newr, equal_nan=True),
      f"maxdiff={np.nanmax(np.abs(oldr-newr)):.3e}")

# speed comparison
t0=time.time()
for _ in range(3): np.array([G.f_krf(E_g, *pp) for pp in eng.params_eff[:4000]])
t_loop=(time.time()-t0)/3
pk = eng.params_eff[:4000]
t0=time.time()
for _ in range(3): G.f_krf(E_g[None,:], pk[:,0:1], pk[:,1:2], pk[:,2:3], pk[:,3:4])
t_vec=(time.time()-t0)/3
print(f"\n  band build: loop {t_loop*1000:.1f} ms  ->  vectorised {t_vec*1000:.1f} ms "
      f"({t_loop/max(t_vec,1e-9):.0f}x faster)")

# ── 8. _birge guard ──────────────────────────────────────────────────────
check("_birge ndf=0 -> 1.0", G._birge(5.0, 0) == 1.0)
check("_birge normal", abs(G._birge(8.0, 2) - 2.0) < 1e-12)

print("\n" + ("ALL CHECKS PASSED" if not fails else f"FAILURES: {fails}"))
sys.exit(1 if fails else 0)
