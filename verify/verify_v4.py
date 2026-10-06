"""Engine test suite -- headless, no display required.

51 checks over CalibrationEngine: the numerically stable quadratic inversion,
input-file validation, a full 10 000-iteration calibration, Monte Carlo
reproducibility, the empty-MC guard, the vectorised confidence bands, and --
since the 2026-09-24 scientific audit -- in-range normalisation, Birge-scaled
query uncertainties and the extrapolation flags; since 2026-10-06, that both
MC ensembles are centred on their best fit (on the shipped AND the pre-v4.8
dataset), that band and query follow one interval rule, and the Radware
second-minimum report.

    python verify/verify_v4.py        # expect 51 PASS, "ALL CHECKS PASSED"

Count the PASS lines, not the verdict: fewer than 51 means an incomplete
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
check("predict_efficiency finite",
      all(np.isfinite(pe[m][k]) for m in ("krf", "rw") for k in ("value", "sigma")),
      f"KRF={pe['krf']['value']:.4g}+-{pe['krf']['sigma']:.4g}  "
      f"RW={pe['rw']['value']:.4g}+-{pe['rw']['sigma']:.4g}")
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
    pe0 = eng.predict_efficiency(1000.0)
    # No MC samples: no uncertainty -- but the best fit itself is still known.
    ok = np.isnan(pe0["krf"]["sigma"]) and np.isfinite(pe0["krf"]["value"])
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

# ── 9. Normalisation is taken inside the data (audit 2026-09-24) ─────────
check("eff_peak lies inside the fitted range",
      eng.E.min() <= eng.eff_peak_E <= eng.E.max(),
      f"peak at {eng.eff_peak_E:.1f} keV, data {eng.E.min():.1f}-{eng.E.max():.1f} keV")
check("eff_norm == 100 / eff_peak", abs(eng.eff_norm * eng.eff_peak - 100.0) < 1e-9)
_v, _Ep = G._curve_peak_in_range(lambda x: 1e6 - (x - 500.0) ** 2, 100.0, 900.0)
check("peak finder: interior maximum", abs(_Ep - 500.0) < 0.5, f"{_Ep:.2f} keV")
_v, _Ep = G._curve_peak_in_range(lambda x: 1.0 / x, 186.2, 2447.7)
check("peak finder: stops at the data edge, never beyond", _Ep == 186.2, f"{_Ep} keV")

import spectratools_export as X
_Ein = np.linspace(eng.E.min(), eng.E.max(), 300)
_cur, _norm = X.relative_efficiency_curves(eng, _Ein)
check("export and % mode share one normalisation",
      abs(_norm - 1.0 / eng.eff_peak) < 1e-15, f"1/{eng.eff_peak:.6g}")
check("exported curve peaks at 1 inside the fitted range",
      abs(np.nanmax(_cur[:, 0]) - 1.0) < 0.01, f"max {np.nanmax(_cur[:, 0]):.5f}")

# ── 10. Query sigmas carry the Birge factor (audit 2026-09-24) ───────────
check("CONTROL: Birge ratios > 1 here, so the checks below discriminate",
      eng.eff_birge > 1.0 and eng.birge1 > 1.0,
      f"KRF B={eng.eff_birge:.3f}  energy B1={eng.birge1:.1f}")
_raw = G.f_krf(1000.0, *eng.params_eff.T)
_p16, _p84 = np.percentile(_raw[np.isfinite(_raw)], [15.87, 84.13])
_s68 = 0.5 * (_p84 - _p16)
_pe = eng.predict_efficiency(1000.0)
check("efficiency query sigma = MC 68% half-width x Birge",
      abs(_pe["krf"]["sigma"] - _s68 * G._band_scale(eng.eff_birge)) < 1e-9 * _s68,
      f"{_pe['krf']['sigma']:.5g} = {_s68:.5g} x {G._band_scale(eng.eff_birge):.4f}")

# Replicate predict()'s own draws at dch = 0: the whole spread is calibration.
_rng = np.random.default_rng(G.SEED)
_rng.normal(2000.0, 0.0, G.N_MC_PRED)
_idx = _rng.integers(0, G.N_MC_CAL, G.N_MC_PRED)
_pl = eng.params_lin[_idx]
_cal = float(np.std((2000.0 - _pl[:, 0]) / _pl[:, 1]))
_r0 = eng.predict(2000.0, 0.0)
check("energy query sigma (dch=0) = B1 x calibration spread",
      abs(_r0[1] - G._band_scale(eng.birge1) * _cal) < 1e-9 * max(_r0[1], 1e-12),
      f"{_r0[1]:.6g} keV = {G._band_scale(eng.birge1):.4g} x {_cal:.4g}")
# With a large dch, the user's own uncertainty must NOT be inflated by B1.
_dch = 5.0
_expect = float(np.hypot(G._band_scale(eng.birge1) * _cal, _dch / eng.popt1[1]))
_r5 = eng.predict(2000.0, _dch)
check("energy query: the query's own dch is not Birge-inflated",
      abs(_r5[1] / _expect - 1.0) < 0.03,
      f"{_r5[1]:.4f} keV vs {_expect:.4f} expected "
      f"(inflating dch too would give ~{G._band_scale(eng.birge1) * _dch / eng.popt1[1]:.4g})")

# ── 11. Range flags (audit 2026-09-24) ───────────────────────────────────
check("energy_outside_fit: inside/edges False, beyond True",
      not eng.energy_outside_fit(1000.0)
      and not eng.energy_outside_fit(eng.E.min())
      and not eng.energy_outside_fit(eng.E.max())
      and eng.energy_outside_fit(eng.E.min() - 0.01)
      and eng.energy_outside_fit(eng.E.max() + 0.01))
check("channel_outside_fit: inside/edges False, beyond True",
      not eng.channel_outside_fit(2000.0)
      and not eng.channel_outside_fit(eng.ch.min())
      and not eng.channel_outside_fit(eng.ch.max())
      and eng.channel_outside_fit(eng.ch.min() - 0.01)
      and eng.channel_outside_fit(eng.ch.max() + 0.01))

# ── 12. MC centred on the best fit; one interval rule (2026-10-06) ───────
# In v4.8 every Radware MC refit started from a fresh parset() seed and, on
# the shipped data, converged 102 chi2 units above the best fit: the ensemble
# sat 7.4 MC-sigma off the plotted curve at 843 keV and the band, drawn as
# bf + B*(pct - bf), contained neither.  All 40 checks above passed anyway.
def _worst_offset(e, which):
    """max |MC mean - bf| / MC std over in-range reference energies."""
    worst = 0.0
    for x in (351.9, 609.3, 843.0, 1120.3, 1764.5, 2204.2):
        if not e.E.min() <= x <= e.E.max():
            continue
        s, bf, _ = e._model_samples(which, x)
        s = s[np.isfinite(s)]
        worst = max(worst, abs(np.mean(s) - bf) / np.std(s))
    return worst

for _which, _name in (("krf", "KRF"), ("rw", "Radware")):
    _w = _worst_offset(eng, _which)
    check(f"{_name} MC centred on the best fit (|mean-bf| < 0.5 MC sigma)",
          _w < 0.5, f"worst {_w:.3f} sigma")
check("bias check passes for both models, no MC health warning",
      eng.krf_bias_z < G.BIAS_Z_WARN and eng.rw_bias_z < G.BIAS_Z_WARN
      and not eng.mc_health_warnings(),
      f"max|z| KRF {eng.krf_bias_z:.3f}  Radware {eng.rw_bias_z:.3f}")
check("MC refit of the unperturbed data reproduces the best fit",
      abs(eng.krf_selfcheck_dchi2) < 1e-3 and abs(eng.rw_selfcheck_dchi2) < 1e-3,
      f"dchi2 KRF {eng.krf_selfcheck_dchi2:.1e}  Radware {eng.rw_selfcheck_dchi2:.1e}")
_m = (eng.eff_grid >= eng.E.min()) & (eng.eff_grid <= eng.E.max())
check("both bands contain their best-fit curve over the data range",
      all(np.all((b["lo"][_m] <= b["value"][_m]) & (b["value"][_m] <= b["hi"][_m]))
          for b in (eng.band_krf, eng.band_rw)), f"{int(_m.sum())} grid points")
_j = int(np.argmin(np.abs(eng.eff_grid - 843.0)))
_qg = eng.predict_efficiency(float(eng.eff_grid[_j]))["rw"]
check("query and band follow one rule (Radware, at a grid energy)",
      abs(_qg["lo"] - eng.band_rw["lo"][_j]) <= 1e-9 * _qg["value"]
      and abs(_qg["hi"] - eng.band_rw["hi"][_j]) <= 1e-9 * _qg["value"],
      f"{eng.eff_grid[_j]:.1f} keV: {_qg['value']:.1f} "
      f"+{_qg['plus']:.1f}/-{_qg['minus']:.1f}")
_q = eng.predict_efficiency(843.0)["rw"]
check("query value is the Radware best fit, not an MC statistic",
      _q["value"] == float(G.f_radware_5p(843.0, *eng.radware_popt)),
      f"843 keV: {_q['value']:.2f}  (MC median {_q['median']:.2f})")

# Controls: the interval rule must flag a biased ensemble and must not let an
# offset ensemble drag the interval off the best fit.
_samp = np.random.default_rng(0).normal(10.0, 1.0, 10000)
check("CONTROL: bias check flags an ensemble 3 sigma off the best fit",
      G._mc_interval(_samp, 7.0, 1.0)["z"] > G.BIAS_Z_WARN
      and abs(G._mc_interval(_samp, 10.0, 1.0)["z"]) < 0.05)
_iv = G._mc_interval(_samp + 5.0, 10.0, 3.0)
check("CONTROL: an offset ensemble cannot move the interval off the best fit",
      _iv["lo"] < 10.0 < _iv["hi"] and abs(_iv["sigma"] - 3.0) < 0.1,
      f"[{_iv['lo']:.2f}, {_iv['hi']:.2f}]  sigma {_iv['sigma']:.3f}")

# The shipped data has a second Radware minimum (chi2 ~470, dchi2/B^2 = 0.70)
# that the best-fit multistart must find and report, not mix into the band.
_alt = eng.radware_alt
check("Radware second minimum found and reported",
      _alt is not None and 0.0 < _alt["dchi2_B2"] < 1.0,
      "none" if _alt is None else
      f"chi2 {_alt['chi2']:.2f}  dchi2/B^2 {_alt['dchi2_B2']:.2f}  "
      f"max dev {_alt['max_dev']*100:+.1f}% at {_alt['at_E']:.0f} keV")

# The pre-v4.8 dataset: there the Radware best fit lies on a flat (a1, a2)
# valley, and a warm start ALONE loses half the refits past |p| < 500.  The
# parset() fallback must keep acceptance up and the ensemble centred.  2 000
# replicates keep this to a few seconds.
_old = G.CalibrationEngine()
_old.load(str(REPO / "verify" / "fixtures" / "226Ra_En_Area_pre_v4.8.txt"))
_old.calibrate()
_n_saved, G.N_MC_EFF = G.N_MC_EFF, 2000
try:
    _old.calibrate_efficiency()
finally:
    G.N_MC_EFF = _n_saved
_w = _worst_offset(_old, "rw")
check("pre-v4.8 data: Radware MC accepted and centred (parset fallback used)",
      _old.mc_rw_ok >= 0.99 * 2000 and _old.mc_rw_fallback > 0 and _w < 0.5
      and not _old.mc_health_warnings(),
      f"ok {_old.mc_rw_ok}/2000, fallback {_old.mc_rw_fallback}, "
      f"worst {_w:.3f} sigma, max|z| {_old.rw_bias_z:.3f}")

print("\n" + ("ALL CHECKS PASSED" if not fails else f"FAILURES: {fails}"))
sys.exit(1 if fails else 0)
