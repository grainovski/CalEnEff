#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CalEnEff calculation engine -- no Tk, importable and testable headless.

Everything that turns a calibration file into numbers lives here: the fit
models, the Monte Carlo machinery, the interval rule shared by the band, the
query and the export, and CalibrationEngine itself.  ra226_gui.py is the
window around it.

This module MUST stay listed in packaging/linux/build_deb.sh, build_rpm.sh and
caleneff.spec: the DEB and the RPM install a fixed file list, and a module
missing from it ships a package that cannot start.
"""

import warnings
import numpy as np
from scipy.optimize import curve_fit, OptimizeWarning

# curve_fit raises OptimizeWarning when it cannot estimate the covariance.
# The MC loops discard pcov entirely and skip any sample whose parameters come
# back non-finite, so 10 000 iterations would flood stderr with warnings the
# code already handles.  Where pcov *is* used (the energy best-fit) a failed
# estimate still shows up as inf in the results file, so nothing is hidden.
warnings.filterwarnings("ignore", category=OptimizeWarning)


# ── Settings ───────────────────────────────────────────────────────────────────
N_MC_CAL  =  10_000
N_MC_PRED =  10_000
N_MC_EFF  =  10_000
SEED      = 42

# Points on the energy grid the efficiency bands are evaluated on.  The bands
# are computed ONCE per calibration from every accepted MC sample and cached on
# the engine, so redraws (a.u./% toggle, theme switch) cost nothing and the
# band and a query at the same energy come from the same samples.
EFF_GRID_N = 400

# Bias check.  z = (MC median − best fit) / (unscaled MC 68 % half-width) at
# each calibration energy.  A healthy parametric bootstrap gives |z| of a few
# hundredths (≤ 0.17 measured on every healthy ensemble); the Radware ensemble
# of v4.8, whose refits converged to a different local minimum, gave 8.65.
# Above 1 the best fit lies outside the unscaled MC 68 % interval, so the MC
# spread no longer describes scatter about the reported value.
BIAS_Z_WARN = 1.0

# Extra deterministic starting points for the Radware best fit, on top of the
# parset and polyfit seeds.  The χ² surface has several local minima; on the
# v4.8 example data parset alone lands 102 χ² units above the global one.
N_RW_EXTRA_STARTS = 60

# Radware is fitted to ε rescaled so that its geometric mean is exp(RW_LN_CENTRE).
# Radford's combination acts on ln ε itself, so without a fixed convention the
# fitted SHAPE depends on the user's arbitrary units (live time, activity, I in
# % or as a fraction): ε ~ 1-4 put ln ε across 0 and moved ε(843 keV) by 10 %.
# 9.5 is where the v4.9 example data already sat (ln ε 8.5-10.6), so its result
# is unchanged, and it is far from 0 for any realistic spread of efficiencies.
RW_LN_CENTRE = 9.5

# Birge ratio above which the fit notes call the scatter systematic rather than
# random.  Birge scaling assumes random scatter; B this large is almost always a
# missing effect (for Ra-226 typically true-coincidence summing).
BIRGE_SYSTEMATIC = 3.0

# MC replicates: a non-positive N or I is redrawn individually, at most this
# many times, instead of discarding the whole replicate.
MC_MAX_REDRAW = 100

# Grid points per chunk when evaluating MC bands: bounds the temporary arrays to
# N_MC_EFF x chunk floats (the full 10 000 x 400 grid peaked at 320 MB).
BAND_CHUNK = 50

# Minimum number of calibration points.  The quadratic energy fit has 3 free
# parameters, so ndf = n − 3 > 0 requires n ≥ 4; below that the Birge ratio
# divides by zero.  The efficiency models need more (KRF 4, Radware 5) and are
# guarded individually rather than blocking the load.
MIN_POINTS = 4


def _mc_interval(samples, bf, birge, min_n=10):
    """The ONE rule for an efficiency value and its 1σ, used by the plotted
    band, the query, the histogram and the export alike.

    samples : MC values, shape (n_samples,) or (n_samples, n_grid)
    bf      : the best-fit value(s), scalar or shape (n_grid,)
    birge   : the model's Birge ratio; scaled inflate-only via _band_scale

    Returns a dict of arrays (or floats for 1-D input):
        value  = bf                       -- the reported value
        minus  = B·(p50 − p16)            -- lower 1σ
        plus   = B·(p84 − p50)            -- upper 1σ
        lo, hi = value − minus, value + plus
        sigma  = B·(p84 − p16)/2          -- symmetric summary
        median = p50,  p16, p84           -- the raw (unscaled) MC quantiles
        z      = (p50 − bf) / ((p84 − p16)/2)   -- bias check, unscaled
        B, n   = scale factor used, number of finite samples

    Centred on the best fit with half-widths measured from the MC MEDIAN, so a
    residual offset between ensemble and best fit can never move the interval
    (the old band, bf + B·(percentile − bf), moved by B × that offset) and the
    best fit is always inside it.  Percentiles rather than the std keep any
    asymmetry and ignore the odd runaway refit.  Entries with fewer than
    `min_n` finite samples are NaN.  Non-finite samples are masked first:
    KRF's exp(d/E) overflows and Radware's log-polynomial diverges far outside
    the fitted range, and np.nanpercentile ignores NaN but not inf.
    """
    s = np.asarray(samples, dtype=float)
    scalar = s.ndim == 1
    if scalar:
        s = s[:, None]
    bf = np.broadcast_to(np.asarray(bf, dtype=float), s.shape[1:]).astype(float)
    finite = np.isfinite(s)
    n = finite.sum(axis=0)
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN columns
        if finite.all():
            p16, p50, p84 = np.percentile(s, [15.87, 50.0, 84.13], axis=0)
        else:
            p16, p50, p84 = np.nanpercentile(np.where(finite, s, np.nan),
                                             [15.87, 50.0, 84.13], axis=0)
        bad = (n < max(min_n, 1)) | ~np.isfinite(bf)
        p16, p50, p84 = (np.where(bad, np.nan, p) for p in (p16, p50, p84))
        B = _band_scale(birge)
        s68 = 0.5 * (p84 - p16)
        minus, plus = B * (p50 - p16), B * (p84 - p50)
        value = np.where(bad, np.nan, bf)
        z = np.where(s68 > 0, (p50 - bf) / np.where(s68 > 0, s68, 1.0), np.nan)
    out = dict(value=value, minus=minus, plus=plus,
               lo=value - minus, hi=value + plus, sigma=B * s68,
               median=p50, p16=p16, p84=p84, z=z, n=n)
    if scalar:
        out = {k: (float(v[0]) if k != "n" else int(v[0])) for k, v in out.items()}
    out["B"] = float(B)
    return out


def _scale_interval(iv, sc):
    """An _mc_interval dict with every efficiency value multiplied by sc
    (a.u. → %).  z, n and B are ratios or counts and stay as they are."""
    return {k: (v * sc if k not in ("z", "n", "B") else v)
            for k, v in iv.items()}


def _nan_interval():
    """_mc_interval's result when there is nothing to evaluate."""
    nan = float("nan")
    return dict(value=nan, minus=nan, plus=nan, lo=nan, hi=nan, sigma=nan,
                median=nan, p16=nan, p84=nan, z=nan, n=0, B=1.0)


def _rows(mask, limit=10):
    """1-based row numbers where `mask` is True, truncated for readability."""
    idx   = np.flatnonzero(mask) + 1
    shown = ", ".join(str(i) for i in idx[:limit])
    return shown + (f" … (+{len(idx)-limit} more)" if len(idx) > limit else "")


def _finite_mean_std(x, min_n=1):
    """(mean, std) over the finite entries of x; (nan, nan) if too few remain.

    Used instead of np.nanmean/np.nanstd because an inverted calibration curve
    can produce ±inf as well as NaN, and the nan* functions propagate inf.
    `min_n` sets how many finite samples are required before the σ is
    considered meaningful at all.
    """
    v = np.asarray(x, dtype=float)
    v = v[np.isfinite(v)]
    if v.size < max(min_n, 1):
        return float("nan"), float("nan")
    return float(np.mean(v)), float(np.std(v))


def _band_scale(birge):
    """Factor for widening an uncertainty band by a Birge ratio -- never below 1.

    A Birge ratio under 1 means the quoted sigma were conservative relative to
    the observed scatter. Scaling a band by such a ratio would make the reported
    interval NARROWER than the Monte Carlo spread it was derived from, which
    understates the uncertainty and has no statistical justification. Inflate
    only: B > 1 widens, B <= 1 leaves the band as the MC produced it.

    None and NaN (an un-run or degenerate fit) also return 1.0, so a band is
    never silently scaled by a missing number.
    """
    try:
        b = float(birge)
    except (TypeError, ValueError):
        return 1.0
    return b if b > 1.0 else 1.0


def _inflate_calibration_part(total, cal, B):
    """Inflate only the calibration share of a Monte Carlo spread by B.

    A query's MC spread mixes two independent sources: the calibration's own
    parameter uncertainty (cal) and the uncertainty of the queried value itself
    (e.g. the channel's Δch).  A Birge ratio says the CALIBRATION's stated σ
    were too small; it says nothing about the user's Δch, so scaling the total
    would inflate the user's own measurement too.  In variances:

        σ² = σ_total² + (B² − 1)·σ_cal²

    which is σ_total when B = 1 and B·σ_cal when the query adds nothing.
    """
    if not (np.isfinite(total) and np.isfinite(cal)):
        return total
    return float(np.sqrt(total * total + (B * B - 1.0) * cal * cal))


def _curve_peak_in_range(func, E_lo, E_hi, n=4000):
    """(value, energy) of the maximum of func over [E_lo, E_hi] -- the data.

    Never outside it: a relative efficiency normalised to an extrapolated
    value inherits the extrapolation's arbitrariness.  Returns (1.0, nan) if
    the curve has no finite positive value there, so a caller dividing by the
    result cannot divide by zero.
    """
    E = np.linspace(float(E_lo), float(E_hi), int(n))
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        v = np.asarray(func(E), dtype=float)
    ok = np.isfinite(v) & (v > 0)
    if not ok.any():
        return 1.0, float("nan")
    k = int(np.argmax(np.where(ok, v, -np.inf)))
    return float(v[k]), float(E[k])


def _birge(chi2, ndf):
    """Birge ratio B = √(χ²/ndf).

    Returns 1.0 when ndf ≤ 0 — an exactly-determined fit carries no scatter
    information, so the stated σ are used unscaled instead of dividing by zero.
    """
    return float(np.sqrt(chi2 / ndf)) if ndf > 0 else 1.0


def _invert_quadratic(a, b, c, ch, ref):
    """Solve  a + b·E + c·E² = ch  for E, returning the root nearest `ref`.

    Uses the cancellation-free (Citardauq) form

        q = −½·(b + sign(b)·√disc),      E₁ = q/c,      E₂ = (a−ch)/q

    rather than the schoolbook (−b ± √disc)/2c.  The schoolbook form divides
    *both* roots by 2c, so MC samples where c drifts near zero — the normal
    case for a nearly linear detector — blow up to ±inf and poison the mean.
    Here only E₁, the spurious far root, degenerates as c → 0; E₂ stays finite
    and tends to the linear solution (ch−a)/b, so selecting the root nearest
    the linear reference `ref` reliably picks the physical one.

    sign(0) is taken as +1 so q can never collapse to zero.  Samples with a
    negative discriminant, or where neither root is finite, return NaN.
    """
    a, b, c, ch, ref = (np.asarray(v, dtype=float)
                        for v in (a, b, c, ch, ref))
    C = a - ch
    with np.errstate(divide="ignore", invalid="ignore"):
        disc = b * b - 4.0 * c * C
        sq   = np.sqrt(np.where(disc >= 0, disc, np.nan))
        q    = -0.5 * (b + np.where(b >= 0, 1.0, -1.0) * sq)
        e1   = q / c        # degenerates as c → 0
        e2   = C / q        # well behaved as c → 0
        d1, d2 = np.abs(e1 - ref), np.abs(e2 - ref)
        # Prefer a finite root; between two finite roots take the nearer one.
        pick1 = np.isfinite(e1) & (~np.isfinite(e2) | (d1 <= d2))
        out   = np.where(pick1, e1, e2)
    return np.where(np.isfinite(out), out, np.nan)


# ── Fit functions ──────────────────────────────────────────────────────────────
def f_lin(E, a, b):     return a + b * E
def f_quad(E, a, b, c): return a + b * E + c * E**2

def f_krf(E, a, b, c, d):
    """KRF 4-parameter efficiency:  ε(E) = (aE + b/E)·exp(cE + d/E)"""
    return (a * E + b / E) * np.exp(c * E + d / E)

def f_radware(E, a1, a2, a3, a4, a5, a6, g):
    """Radware 7-parameter efficiency (Radford EFFIT v4.0, 1999).

    ln ε(E) = f · (1 + r^g)^(-1/g)
    where:
        f1 = a1 + a2·x + a3·x²     x = ln(E/100)   (low-E region)
        f2 = a4 + a5·y + a6·y²     y = ln(E/1000)  (high-E region)
        f  = min(f1, f2)
        F  = max(f1, f2)
        r  = f / F

    This is Radford's (f1^-g + f2^-g)^(-1/g) written so it can be evaluated
    for any sign, via log-sum-exp.  It acts on ln ε ITSELF, so which branch
    dominates depends on the unit of ε:

    * ln ε > 0 (both branches positive, Radford's intended regime: EFFIT
      fits efficiencies in arbitrary units well above 1): the
      combination tends to min(f1, f2), so the rising low-energy branch and
      the falling high-energy branch meet at the efficiency maximum.
    * ln ε < 0 (absolute efficiencies < 1): it tends to max(f1, f2) instead.
    * ln ε near 0: neither -- the fit degrades badly.  Measured on the v4.9
      example data scaled so that ε ~ 1-4: χ² 452 -> 525, ε(843 keV) +10 %.

    CalibrationEngine therefore never fits raw ε: it rescales ε to a fixed
    log range first (see RW_LN_CENTRE), which makes the Radware result
    independent of the user's units.  Do not call this on raw ε directly.
    """
    E  = np.asarray(E, dtype=float)
    x  = np.log(E * 0.01)            # ln(E/100)
    y  = np.log(E * 0.001)           # ln(E/1000)
    f1 = a1 + (a2 + a3*x) * x        # Horner form: 1 fewer multiplication
    f2 = a4 + (a5 + a6*y) * y

    f = np.minimum(f1, f2)
    F = np.maximum(f1, f2)
    # F=0 is astronomically unlikely; tiny additive shift handles it
    # without an extra np.where allocation.
    r = np.maximum(f / (F + (F == 0) * 1e-300), 1e-300)

    # Stable (1 + r^g)^(-1/g) via log-sum-exp:
    # np.minimum/np.maximum rather than np.clip: identical results, but clip's
    # Python-level dispatch cost 7.8 s of a 58 s profiled calibration, this
    # function being called ~430 000 times on 23-element arrays.
    g_log_r = np.minimum(np.maximum(g * np.log(r), -700.0), 700.0)
    log_y3  = -np.logaddexp(0.0, g_log_r) / g

    log_eff = np.minimum(np.maximum(f * np.exp(log_y3), -700.0), 700.0)
    return np.exp(log_eff)

# ── Efficiency fitting helpers ─────────────────────────────────────────────────

def _krf_p0(E, eff):
    """Data-driven initial parameters for KRF: ε=(aE+b/E)exp(cE+d/E).

    Derive a,b from geometric-mean efficiency and energy so the model
    reproduces the typical scale; seed c,d small so the exponential is ~1.
    """
    Eg  = float(np.exp(np.mean(np.log(np.maximum(E,   1e-30)))))
    eg  = float(np.exp(np.mean(np.log(np.maximum(eff, 1e-30)))))
    a0  = eg / (2.0 * Eg)
    b0  = eg * Eg / 2.0
    return [a0, b0, -1e-4, 1.0]


def _radware_p0(E, eff):
    """Initial parameters using Radford's `parset()` logic from effit.c.

    Finds the data points whose energies are nearest to the low-E reference
    (100 keV) and high-E reference (1000 keV) and seeds:
        a1 = ln(ε[ix1]) + a2·(ln 100  − ln E[ix1])     a2 =  1.5
        a4 = ln(ε[ix2]) + a5·(ln 1000 − ln E[ix2])     a5 = -0.9
        a3 = a6 = 0,   g = 15
    This places the polynomials so a1 ≈ ln ε(100) and a4 ≈ ln ε(1000) — the
    natural physical interpretation, with both being NEGATIVE for ε < 1.
    """
    E   = np.asarray(E,   dtype=float)
    eff = np.asarray(eff, dtype=float)

    ix1 = int(np.argmin(np.abs(E -  100.0)))
    ix2 = int(np.argmin(np.abs(E - 1000.0)))

    ln_e1 = float(np.log(max(eff[ix1], 1e-30)))
    ln_e2 = float(np.log(max(eff[ix2], 1e-30)))

    a2, a5 = 1.5, -0.9
    a1 = ln_e1 + a2 * (np.log( 100.0) - np.log(E[ix1]))
    a4 = ln_e2 + a5 * (np.log(1000.0) - np.log(E[ix2]))
    return [a1, a2, 0.0, a4, a5, 0.0, 15.0]


def _radware_p0_polyfit(E, eff):
    """Alternative seed: independent 2-degree polyfits of ln ε vs x and y.

    Kept as a secondary multi-start candidate; less reliable than the
    parset-style seed but useful when ε is far from a clean power-law shape.
    """
    lne = np.log(np.maximum(eff, 1e-30))
    x   = np.log(E /  100.0)
    y   = np.log(E / 1000.0)
    cx  = np.polyfit(x, lne, 2)   # [x², x, const]
    cy  = np.polyfit(y, lne, 2)
    return [float(cx[2]), float(cx[1]), float(cx[0]),
            float(cy[2]), float(cy[1]), float(cy[0]), 15.0]


def f_radware_5p(E, a1, a2, a4, a5, a6):
    """5-parameter Radware efficiency — C (a3) = 0 and G = 15 fixed.

    This is Radford's default fitting configuration in effit.c (getdat()):
        efgd.freepars[2] = 0;   // C = 0 fixed
        efgd.freepars[6] = 0;   // G = 15 fixed
        efgd.nfp = 2;           // two parameters fixed → 5 free
    Fixing C and G makes the Levenberg-Marquardt fitter (Bevington CURFIT)
    substantially more stable while preserving full physical accuracy for
    typical HPGe detectors.
    """
    return f_radware(E, a1, a2, 0.0, a4, a5, a6, 15.0)


def _krf_jac(E, a, b, c, d):
    """Analytic Jacobian of f_krf, shape (len(E), 4).

    Given to the MC refits so Levenberg-Marquardt does not estimate it by
    finite differences (one extra model evaluation per parameter per step).
    """
    E = np.asarray(E, dtype=float)
    g = np.exp(c * E + d / E)
    f = (a * E + b / E) * g
    return np.column_stack([E * g, g / E, E * f, f / E])


_JAC_EPS = np.sqrt(np.finfo(float).eps)


def _radware_5p_jac(E, *p):
    """Forward-difference Jacobian of f_radware_5p in ONE vectorised call.

    The same differences MINPACK would take (step sqrt(eps)·|p|), but the six
    model evaluations run as one array operation instead of six Python calls.
    Shape (len(E), 5).
    """
    E = np.asarray(E, dtype=float)
    p = np.asarray(p, dtype=float)
    h = _JAC_EPS * np.where(p == 0, 1.0, np.abs(p))
    P = np.vstack([p[None, :], p[None, :] + np.diag(h)])          # (6, 5)
    V = f_radware_5p(E[None, :], *(P[:, j:j + 1] for j in range(5)))
    return ((V[1:] - V[0]) / h[:, None]).T


def _rw_scale(eff):
    """Factor k with geomean(k·ε) = exp(RW_LN_CENTRE); see RW_LN_CENTRE."""
    lne = np.log(np.asarray(eff, dtype=float))
    return float(np.exp(RW_LN_CENTRE - np.mean(lne)))


def _radware_p0_5p(E, eff):
    """Radford parset() seed for the 5-parameter model.

    Calls _radware_p0() and strips the two fixed entries (a3=0, g=15),
    returning [a1, a2, a4, a5, a6] ready for f_radware_5p.
    """
    full = _radware_p0(E, eff)   # [a1, a2, 0, a4, a5, 0, 15]
    return [full[0], full[1], full[3], full[4], full[5]]


def _radware_extra_starts(E, eff, n, seed=SEED):
    """`n` deterministic random starting points for the Radware 5-p best fit.

    Drawn uniformly in a box around the physically sensible region (a1, a4
    within ±6 of the data's ln ε range, a2 in [−15, 25], a5 and a6 in
    [−8, 8]) from a FIXED seed, so a calibration is reproducible.  The χ²
    surface is multimodal: on the v4.8 example data 2 500 such starts reach
    the global minimum 27 % of the time, a second one (χ² +18) 6 %, and the
    minimum parset() leads to (χ² +102) 29 %.
    """
    lne = np.log(np.maximum(np.asarray(eff, dtype=float), 1e-30))
    lo_e, hi_e = float(lne.min()) - 6.0, float(lne.max()) + 6.0
    rng = np.random.default_rng(seed + 1)
    lo = np.array([lo_e, -15.0, lo_e, -8.0, -8.0])
    hi = np.array([hi_e,  25.0, hi_e,  8.0,  8.0])
    return list(lo + (hi - lo) * rng.random((int(n), 5)))


def _distinct_curve(f, E, p_a, p_b, rtol=1e-3):
    """True if two parameter sets give curves differing by > rtol on E."""
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        a, b = f(E, *p_a), f(E, *p_b)
    ok = np.isfinite(a) & np.isfinite(b) & (a > 0)
    return bool(ok.any() and np.max(np.abs(b[ok] / a[ok] - 1.0)) > rtol)


def _multistart(func, E, eff, deff, p0_list, bounds, maxfev=20000):
    """Try multiple starting points; return the fit with lowest weighted χ².

    Tolerances kept at scipy defaults — multi-start (not tighter ftol) is
    what reduces inter-model divergence.  Any candidate that fails to
    converge is silently skipped.  Returns *None* only if every candidate
    fails.
    """
    best_p, best_chi2 = None, np.inf
    for p0 in p0_list:
        try:
            p, _ = curve_fit(
                func, E, eff, p0=p0,
                sigma=deff, absolute_sigma=True,
                bounds=bounds, maxfev=maxfev,
                method="trf",
            )
            chi2 = float(np.sum(((eff - func(E, *p)) / deff) ** 2))
            if chi2 < best_chi2:
                best_chi2, best_p = chi2, p
        except Exception:
            pass
    return best_p


# ── Linear / quadratic calibration helpers ─────────────────────────────────────

def _wls(E, ch, dch, deg):
    cols = [E**k for k in range(deg + 1)]
    A    = np.column_stack(cols)
    W    = 1.0 / dch
    p, *_ = np.linalg.lstsq(A * W[:, None], ch * W, rcond=None)
    return p

def _batch_wls(A_weighted, yw_all):
    ATA  = A_weighted.T @ A_weighted
    ATyw = yw_all @ A_weighted
    L    = np.linalg.cholesky(ATA)
    return np.linalg.solve(L.T, np.linalg.solve(L, ATyw.T)).T


# ─────────────────────────────────────────────────────────────────────────────
class CalibrationEngine:

    def __init__(self):
        self.reset()

    def reset(self):
        self.data_loaded  = False
        self.cal_ready    = False
        self.error_msg    = None
        self.filepath     = None
        self.n            = 0
        self.ch = self.dch = self.E = None
        self.N = self.dN = self.I_pct = self.dI_pct = None
        self.popt1 = self.popt2 = None
        self.pcov1 = self.pcov2 = None
        self.params_lin = self.params_quad = None
        self.birge1 = self.birge2 = None
        self.rms1   = self.rms2   = None
        self.chi2_1 = self.chi2_2 = None
        self.ndf1   = self.ndf2   = None
        self.eff = self.deff = None
        self.eff_popt   = None
        self.params_eff = None
        self.eff_rms    = self.eff_birge = None
        self.eff_chi2   = self.eff_ndf   = None
        self.radware_popt   = None
        self.params_radware = None
        self.radware_rms    = self.radware_birge = None
        self.radware_chi2   = self.radware_ndf   = None
        # Normalisation, shared by % mode and the SpectraTools export: the peak
        # of the best-fit KRF curve WITHIN the fitted energy range (eff_peak,
        # reached at eff_peak_E).  eff_norm = 100 / eff_peak converts a.u. to %.
        self.eff_norm   = None
        self.eff_peak   = self.eff_peak_E = None
        self.eff_ready  = False
        self.mc_krf_ok  = self.mc_rw_ok = self.mc_bad = 0
        # Radware MC refits that needed the parset() fallback because the
        # warm start from the best fit was rejected.
        self.mc_rw_fallback = 0
        self.mc_redrawn = 0
        # Radware is fitted to radware_scale·ε (see RW_LN_CENTRE).
        self.radware_scale = 1.0
        self.model_spread = None
        self.dE = None
        self.sig1 = self.sig2 = None
        # A second Radware minimum within Δχ²/B² < 1 of the best fit, if the
        # multistart found one: dict(chi2, popt, dchi2_B2, max_dev, at_E).
        self.radware_alt = None
        # Self-check: χ² of the MC refit procedure applied to the UNPERTURBED
        # data, minus the best-fit χ².  > 1 means the MC samples a different
        # minimum from the curve that is plotted.
        self.krf_selfcheck_dchi2 = self.rw_selfcheck_dchi2 = None
        # Cached bands (dicts from _mc_interval, a.u.) on eff_grid, and the
        # bias check max |z| over the calibration energies, per model.
        self.eff_grid = None
        self.band_krf = self.band_rw = None
        self.krf_bias_z = self.rw_bias_z = None

    def load(self, filepath):
        """Read and validate a 7-column calibration file.

        Every check below guards a specific downstream failure.  Without them
        a malformed file loads cleanly and then dies deep inside numpy or
        scipy with a message that points at the fit rather than at the data.
        """
        data = np.loadtxt(filepath, ndmin=2)   # ndmin=2 keeps 1-row files 2-D
        if data.shape[1] < 7:
            raise ValueError(
                f"File has {data.shape[1]} column(s); 7 are required:\n"
                "    ch   Δch   N   ΔN   E[keV]   I[%]   ΔI[%]   [ΔE keV]")
        # Optional 8th column: the uncertainty of the reference energy, keV.
        # Without it the energies are treated as exact, as before.
        dE = (data[:, 7].copy() if data.shape[1] >= 8
              else np.zeros(data.shape[0]))
        if data.shape[1] >= 8 and not np.isfinite(dE).all():
            raise ValueError("Non-numeric or infinite ΔE (column 8) on row(s): "
                             f"{_rows(~np.isfinite(dE))}")
        if np.any(dE < 0):
            raise ValueError("ΔE (column 8) is an absolute uncertainty and must "
                             f"be ≥ 0.\nRow(s) {_rows(dE < 0)} are negative.")

        ch, dch       = data[:, 0], data[:, 1]
        N,  dN        = data[:, 2], data[:, 3]
        E             = data[:, 4]
        I_pct, dI_pct = data[:, 5], data[:, 6]
        n = len(ch)

        if n < MIN_POINTS:
            raise ValueError(
                f"Only {n} calibration point(s) — at least {MIN_POINTS} are "
                "needed.\nThe quadratic fit has 3 free parameters, so ndf = "
                "n − 3 must exceed 0.")
        if not np.isfinite(data[:, :7]).all():
            bad = ~np.isfinite(data[:, :7]).all(axis=1)
            raise ValueError(
                f"Non-numeric or infinite value on row(s): {_rows(bad)}")
        if np.any(dch <= 0):
            raise ValueError(
                "Δch must be > 0 on every row — it is the fit weight 1/Δch.\n"
                f"Row(s) {_rows(dch <= 0)} have Δch ≤ 0.")
        if np.any(E <= 0):
            raise ValueError(
                "E must be > 0 keV — the efficiency models evaluate ln(E) and "
                f"b/E.\nRow(s) {_rows(E <= 0)} have E ≤ 0.")
        if np.any(N <= 0):
            raise ValueError(
                "N (peak area) must be > 0 — ε = N/I must be positive to fit.\n"
                f"Row(s) {_rows(N <= 0)} have N ≤ 0.")
        if np.any(I_pct <= 0):
            raise ValueError(
                "I (emission intensity) must be > 0 — ε = N/I.\n"
                f"Row(s) {_rows(I_pct <= 0)} have I ≤ 0.")
        if np.any(dN < 0) or np.any(dI_pct < 0):
            raise ValueError(
                "ΔN and ΔI are absolute uncertainties and must be ≥ 0.\n"
                f"Row(s) {_rows((dN < 0) | (dI_pct < 0))} are negative.")
        if np.any((dN == 0) & (dI_pct == 0)):
            raise ValueError(
                "ΔN and ΔI are both 0 on row(s) "
                f"{_rows((dN == 0) & (dI_pct == 0))} — Δε would be 0 and the "
                "efficiency χ² would divide by zero.")

        self.ch, self.dch = ch, dch
        self.N,  self.dN  = N,  dN
        self.E            = E
        self.dE           = dE
        self.I_pct, self.dI_pct = I_pct, dI_pct
        self.n = n
        self.filepath = filepath
        self.data_loaded = True
        self.cal_ready   = False
        self.eff_ready   = False

    def calibrate(self, progress_cb=None):
        if not self.data_loaded: raise RuntimeError("Load data first.")
        try:
            self._fit_best(progress_cb)
            self._mc(progress_cb)
            self.cal_ready = True
        except Exception as exc:
            self.error_msg = str(exc); raise

    def _effective_sigma(self, slope):
        """σ of ch including the reference-energy uncertainty: the effective-
        variance method, σ² = Δch² + (dch/dE · ΔE)².  Equals Δch exactly when
        the file has no ΔE column."""
        if not np.any(self.dE):
            return self.dch
        return np.sqrt(self.dch ** 2 + (slope * self.dE) ** 2)

    def _fit_best(self, cb):
        if cb: cb(5, "Computing best-fit parameters …")
        # Effective variance needs the slope, which needs the fit: two passes
        # are plenty for a near-linear calibration (the slope barely moves).
        self.sig1 = self.sig2 = self.dch
        for _ in range(2 if np.any(self.dE) else 1):
            p1_0 = _wls(self.E, self.ch, self.sig1, 1)
            p2_0 = _wls(self.E, self.ch, self.sig2, 2)
            self.popt1, self.pcov1 = curve_fit(
                f_lin, self.E, self.ch, p0=p1_0,
                sigma=self.sig1, absolute_sigma=True)
            self.popt2, self.pcov2 = curve_fit(
                f_quad, self.E, self.ch, p0=p2_0,
                sigma=self.sig2, absolute_sigma=True)
            self.sig1 = self._effective_sigma(self.popt1[1])
            self.sig2 = self._effective_sigma(
                self.popt2[1] + 2.0 * self.popt2[2] * self.E)
        n = len(self.ch)
        r1 = self.ch - f_lin(self.E,  *self.popt1)
        r2 = self.ch - f_quad(self.E, *self.popt2)
        self.chi2_1 = float(np.sum((r1/self.sig1)**2)); self.ndf1 = n - 2
        self.chi2_2 = float(np.sum((r2/self.sig2)**2)); self.ndf2 = n - 3
        self.birge1 = _birge(self.chi2_1, self.ndf1)
        self.birge2 = _birge(self.chi2_2, self.ndf2)
        self.rms1   = float(np.sqrt(np.mean(r1**2)))
        self.rms2   = float(np.sqrt(np.mean(r2**2)))

    def _mc(self, cb):
        if cb: cb(12, f"MC calibration ({N_MC_CAL:,} samples) …")
        n   = len(self.ch)
        rng = np.random.default_rng(SEED)
        # One set of standard normals shared by both models, each scaled by its
        # own σ (they differ only when the file carries ΔE).  ch + σ·z is
        # exactly what rng.normal(ch, σ) returns, so without ΔE the samples are
        # bit-identical to every earlier version.
        z = rng.standard_normal((N_MC_CAL, n))
        W1, W2 = 1.0 / self.sig1, 1.0 / self.sig2
        A1  = np.column_stack([np.ones(n), self.E])            * W1[:, None]
        A2  = np.column_stack([np.ones(n), self.E, self.E**2]) * W2[:, None]
        if cb: cb(20, "MC: linear fits …")
        self.params_lin  = _batch_wls(A1, (self.ch + self.sig1 * z) * W1)
        if cb: cb(58, "MC: quadratic fits …")
        self.params_quad = _batch_wls(A2, (self.ch + self.sig2 * z) * W2)
        if cb: cb(97, "Finalising …")

    def calibrate_efficiency(self, progress_cb=None):
        if not self.data_loaded: raise RuntimeError("Load data first.")
        # Not ready until this run completes: a run that fails part-way must not
        # leave the previous run's curves and bands looking current.
        self.eff_ready = False
        self.band_krf = self.band_rw = None
        if progress_cb: progress_cb(2, "Computing efficiency points …")
        eff  = self.N / self.I_pct
        deff = eff * np.sqrt((self.dN/self.N)**2 + (self.dI_pct/self.I_pct)**2)
        self.eff = eff; self.deff = deff

        bounds_krf = ([0, 0, -np.inf, -np.inf], [np.inf, np.inf, 0, np.inf])

        # ── KRF best-fit — multi-start ────────────────────────────────
        if progress_cb: progress_cb(5, "Best-fit KRF curve …")
        p0_data = _krf_p0(self.E, eff)
        krf_candidates = [
            p0_data,
            [p0_data[0]*2,  p0_data[1]*2,  -1e-4, 1.0],
            [p0_data[0]*0.5,p0_data[1]*0.5,-5e-4, 0.5],
            [p0_data[0],    p0_data[1],    -1e-3, 2.0],
            [1.0, 1e3, -1e-3, 0.0],          # original fixed seed as fallback
        ]
        popt_krf = _multistart(f_krf, self.E, eff, deff,
                               krf_candidates, bounds_krf)
        if popt_krf is None:
            raise RuntimeError("KRF fit failed to converge from all starting points.")
        self.eff_popt = popt_krf
        res_k = eff - f_krf(self.E, *popt_krf)
        self.eff_rms   = float(np.sqrt(np.mean(res_k**2)))
        self.eff_ndf   = len(self.E) - 4
        self.eff_chi2  = float(np.sum((res_k/deff)**2))
        self.eff_birge = _birge(self.eff_chi2, self.eff_ndf)

        # Normalisation: the KRF peak WITHIN the fitted range.  It used to be
        # the maximum over 0.9*Emin .. 1.1*Emax, and on a curve still rising at
        # the lowest calibration line -- the usual case above ~150 keV -- that
        # maximum sat on the grid's lower edge: an extrapolated value fixed by
        # an arbitrary 0.9.  The SpectraTools export took a different
        # extrapolated maximum again, so one curve read 2.1% differently in the
        # app and in SpectraTools.  Both now use this single number.
        self.eff_peak, self.eff_peak_E = _curve_peak_in_range(
            lambda x: f_krf(x, *popt_krf),
            float(self.E.min()), float(self.E.max()))
        self.eff_norm = 100.0 / self.eff_peak

        # ── Radware best-fit — 5-parameter (Radford's procedure) ────────
        # Radford's effit.c fixes C (a3) = 0 and G = 15, leaving 5 free
        # parameters: A (a1), B (a2), D (a4), E (a5), F (a6).
        # Seeds: Radford's parset(), the polyfit alternative, and
        # N_RW_EXTRA_STARTS deterministic random starts; all LM (Bevington
        # CURFIT), no bounds; the lowest χ² wins.  The χ² surface has several
        # local minima and parset() alone does not reliably find the global
        # one -- on the v4.8 example data it lands 102 χ² units above it, and
        # the global minimum was found only because polyfit happened to start
        # in the right basin.
        if progress_cb: progress_cb(8, "Best-fit Radware curve (5-param, C=0, G=15) …")
        # Fit k·ε, not ε: see RW_LN_CENTRE.  Parameters live in that scaled
        # space; rw_curve() divides k back out.
        k = self.radware_scale = _rw_scale(eff)
        eff_k, deff_k = eff * k, deff * k
        p0_5        = _radware_p0_5p(self.E, eff_k)         # parset seed
        p0_poly_all = _radware_p0_polyfit(self.E, eff_k)
        p0_5_poly   = [p0_poly_all[i] for i in [0, 1, 3, 4, 5]]   # drop a3, g
        rw_seeds = [p0_5, p0_5_poly] + _radware_extra_starts(
            self.E, eff_k, N_RW_EXTRA_STARTS)

        rw_minima = []                      # (chi2, pp) of every accepted fit
        for seed in rw_seeds:
            try:
                with np.errstate(over="ignore", invalid="ignore",
                                 divide="ignore"):
                    pp, _ = curve_fit(
                        f_radware_5p, self.E, eff_k, p0=seed,
                        sigma=deff_k, absolute_sigma=True,
                        method="lm", maxfev=20000,
                    )
                    if not (np.all(np.isfinite(pp)) and np.all(np.abs(pp) < 500)):
                        continue
                    chi2 = float(np.sum(((eff_k - f_radware_5p(self.E, *pp))
                                         / deff_k)**2))
                if np.isfinite(chi2):
                    rw_minima.append((chi2, pp))
            except Exception:
                pass
        rw_minima.sort(key=lambda t: t[0])
        popt_rw = rw_minima[0][1] if rw_minima else None

        self.radware_alt = None
        if popt_rw is not None:
            self.radware_popt = popt_rw          # [a1, a2, a4, a5, a6] of k·ε
            res_r = eff - self.rw_curve(self.E)
            self.radware_rms   = float(np.sqrt(np.mean(res_r**2)))
            self.radware_ndf   = len(self.E) - 5    # 5 free parameters
            self.radware_chi2  = float(np.sum((res_r/deff)**2))
            self.radware_birge = _birge(self.radware_chi2, self.radware_ndf)
            # A different curve almost as good: Δχ²/B² < 1 means the two are
            # statistically indistinguishable once the Birge scaling is
            # applied.  The MC (warm-started from the best fit) describes the
            # uncertainty WITHIN the best fit's minimum, so this ambiguity is
            # not in the band; it is reported as a model systematic instead.
            B2 = _band_scale(self.radware_birge) ** 2
            E_in = np.linspace(float(self.E.min()), float(self.E.max()), 400)
            for chi2_a, pp_a in rw_minima[1:]:
                d = (chi2_a - self.radware_chi2) / B2
                if d >= 1.0:
                    break
                if not _distinct_curve(f_radware_5p, E_in, popt_rw, pp_a):
                    continue                 # the same minimum, found again
                with np.errstate(over="ignore", invalid="ignore"):
                    dev = (f_radware_5p(E_in, *pp_a)
                           / f_radware_5p(E_in, *popt_rw) - 1.0)
                j = int(np.nanargmax(np.abs(dev)))
                self.radware_alt = dict(chi2=float(chi2_a), popt=pp_a,
                                        dchi2_B2=float(d),
                                        max_dev=float(dev[j]),
                                        at_E=float(E_in[j]))
                break
        else:
            self.radware_popt = None
            popt_rw = None        # disable Radware in MC loop

        # ── MC loop — resample N and I, refit both ────────────────────
        # A parametric bootstrap: every iteration redraws N and I from their
        # stated uncertainties and refits both models.
        #   • Skip pathological samples (N_s≤0, I_s≤0, non-finite ratios).
        #   • Levenberg-Marquardt (method="lm") — 2-3× faster than TRF:
        #     cheaper per-iteration linear algebra, no bound projection.
        #   • BOTH models are warm-started from their own best fit.  The start
        #     is FIXED (every refit starts from the same popt, never from the
        #     previous sample's result), so there is no chain and no chain
        #     bias: the samples stay independent.  What the warm start buys is
        #     that every refit lands in the SAME local minimum as the plotted
        #     curve, so the MC describes the uncertainty of that curve.
        #     Radware used to start each refit from a fresh parset() seed;
        #     on data whose lowest line lies well above 100 keV that seed sits
        #     in a different basin, and on the v4.8 example data 9 999 of
        #     10 000 refits converged 102 χ² units above the best fit -- the
        #     ensemble was 7.4 MC-σ off the plotted curve at 843 keV.
        #   • Radware falls back to parset(eff_s) only when the warm-started
        #     fit is rejected.  That happens when the best fit lies on a flat
        #     (a1, a2) valley -- the low-energy branch active only below the
        #     data -- and LM slides along it past |p| < 500 at an unchanged
        #     χ²; on the pre-v4.8 data that was half the refits.
        #   • Relaxed tolerances (1e-5) and maxfev=1500: measured to change
        #     the result by ≤ 0.01 σ; no refit ever needed more than ~300
        #     evaluations.
        #   • Progress callback every 100 iter → UI updates ~1× per second.
        MC_MAXFEV = 1500
        MC_TOL    = 1e-5       # ftol = xtol = gtol for MC fits

        # Jacobians: analytic for KRF, one vectorised forward difference for
        # Radware -- the same derivatives LM would estimate, without one
        # Python-level model call per parameter per step.
        def _lm(func, jac, y, p0, sig):
            pp, _ = curve_fit(func, self.E, y, p0=p0, jac=jac,
                              sigma=sig, absolute_sigma=True,
                              maxfev=MC_MAXFEV, method="lm",
                              ftol=MC_TOL, xtol=MC_TOL, gtol=MC_TOL)
            return pp

        def refit_krf(y):
            try:
                pp = _lm(f_krf, _krf_jac, y, popt_krf, deff)
            except Exception:
                return None
            return pp if np.all(np.isfinite(pp)) else None

        def refit_rw(y):
            """(params of k·ε, used_fallback), or (None, False) if both fail."""
            yk = y * k
            for fallback, p0 in ((False, popt_rw), (True, None)):
                if p0 is None:
                    p0 = _radware_p0_5p(self.E, yk)
                try:
                    pp = _lm(f_radware_5p, _radware_5p_jac, yk, p0, deff_k)
                except Exception:
                    continue
                if np.all(np.isfinite(pp)) and np.all(np.abs(pp) < 500):
                    return pp, fallback
            return None, False

        # Self-check: the MC refit procedure applied to the UNPERTURBED data
        # must reproduce the best fit.  If it does not, the MC samples a
        # different minimum from the plotted curve -- the v4.8 Radware defect.
        pk = refit_krf(eff)
        self.krf_selfcheck_dchi2 = (
            float(np.sum(((eff - f_krf(self.E, *pk)) / deff) ** 2))
            - self.eff_chi2 if pk is not None else float("inf"))
        self.rw_selfcheck_dchi2 = None
        if popt_rw is not None:
            pr, _ = refit_rw(eff)
            self.rw_selfcheck_dchi2 = (
                float(np.sum(((eff_k - f_radware_5p(self.E, *pr)) / deff_k)
                             ** 2)) - self.radware_chi2
                if pr is not None else float("inf"))

        rng = np.random.default_rng(SEED)
        store_krf = []; store_rw = []
        n_bad     = 0          # replicates abandoned (redraws exhausted)
        n_redraw  = 0          # individual N or I values redrawn
        n_fb      = 0          # Radware refits that needed the fallback

        def _positive(x, mu, sd):
            """Redraw non-positive entries of x individually from N(mu, sd).

            A replicate used to be discarded whole whenever ANY of its N or I
            came out ≤ 0; with large relative uncertainties that threw away
            most replicates (42 % at ΔN = 50 %) and biased the survivors.
            Redrawing only the offending value truncates each point's own
            distribution at 0, which is the physical constraint.  No draws
            are consumed unless a value is non-positive, so ordinary data
            produce exactly the samples they always did.
            """
            nonlocal n_redraw
            for _ in range(MC_MAX_REDRAW):
                bad = x <= 0
                if not bad.any():
                    return x
                n_redraw += int(bad.sum())
                x[bad] = rng.normal(mu[bad], sd[bad])
            return None

        for it in range(N_MC_EFF):
            if progress_cb and it % 100 == 0:
                progress_cb(10 + int(85*it/N_MC_EFF),
                            f"Efficiency MC ({it:,}/{N_MC_EFF:,}) …")

            N_s = rng.normal(self.N,     self.dN)
            I_s = rng.normal(self.I_pct, self.dI_pct)
            N_s = _positive(N_s, self.N, self.dN)
            I_s = _positive(I_s, self.I_pct, self.dI_pct) if N_s is not None else None
            if N_s is None or I_s is None:
                n_bad += 1
                continue
            eff_s = N_s / I_s
            if not np.isfinite(eff_s).all() or (eff_s <= 0).any():
                n_bad += 1
                continue

            pp = refit_krf(eff_s)
            if pp is not None:
                store_krf.append(pp)

            # Radware — 5-parameter (C=0, G=15 fixed).
            if popt_rw is not None:
                pp_r, fb = refit_rw(eff_s)
                if pp_r is not None:
                    store_rw.append(pp_r)
                    n_fb += fb

        if (n_bad or n_redraw) and progress_cb:
            progress_cb(99, f"MC complete — {n_redraw:,} non-positive values "
                            f"redrawn, {n_bad:,} replicates abandoned")

        # Keep params_eff 2-D even when every MC fit failed.  np.array([]) is
        # 1-D, so params_eff[:, 0] would raise "too many indices" and surface
        # as a cryptic status-bar error rather than an honest "MC failed".
        self.params_eff     = (np.asarray(store_krf, dtype=float)
                               if store_krf else np.empty((0, 4)))
        self.params_radware = (np.asarray(store_rw, dtype=float)
                               if store_rw else None)
        self.mc_krf_ok = len(self.params_eff)
        self.mc_rw_ok  = (0 if self.params_radware is None
                          else len(self.params_radware))
        self.mc_bad    = n_bad
        self.mc_redrawn = n_redraw
        self.mc_rw_fallback = n_fb

        # Bands, cached once from EVERY accepted sample, and the bias check.
        if progress_cb: progress_cb(96, "Efficiency bands …")
        self._build_eff_bands()

        # KRF-vs-Radware spread inside the data: a model systematic that
        # neither band contains.
        self.model_spread = None
        if self.radware_popt is not None:
            E_in = np.linspace(float(self.E.min()), float(self.E.max()), 400)
            with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
                rel = f_krf(E_in, *popt_krf) / self.rw_curve(E_in) - 1.0
            j = int(np.nanargmax(np.abs(rel)))
            self.model_spread = dict(max_rel=float(rel[j]), at_E=float(E_in[j]))

        self.eff_ready  = True
        if progress_cb: progress_cb(100, "Efficiency calibration done.")

    def _model_samples(self, which, E):
        """(MC samples, best fit, Birge) of one model at energies E (a.u.).

        samples has shape (n_samples, len(E)) for array E, (n_samples,) for a
        scalar; None when the model has no MC samples or no best fit.
        """
        scalar = np.ndim(E) == 0
        Ec = np.atleast_1d(np.asarray(E, dtype=float))[None, :]
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            if which == "krf":
                p = self.params_eff
                if p is None or not len(p) or self.eff_popt is None:
                    return None
                s  = f_krf(Ec, p[:, 0:1], p[:, 1:2], p[:, 2:3], p[:, 3:4])
                bf = f_krf(Ec[0], *self.eff_popt)
                B  = self.eff_birge
            else:
                p = self.params_radware
                if p is None or not len(p) or self.radware_popt is None:
                    return None
                k  = self.radware_scale
                s  = f_radware_5p(Ec, p[:, 0:1], p[:, 1:2], p[:, 2:3],
                                  p[:, 3:4], p[:, 4:5]) / k
                bf = f_radware_5p(Ec[0], *self.radware_popt) / k
                B  = self.radware_birge
        if scalar:
            return s[:, 0], float(bf[0]), B
        return s, bf, B

    def _build_eff_bands(self):
        """Cache both models' bands on eff_grid and their bias check z.

        z is taken at the calibration energies, not on the grid: the grid runs
        4 % below and 2 % above the data, where an extrapolated curve can have
        a legitimately skewed MC distribution that says nothing about whether
        the refits found the right minimum.
        """
        E = self.E
        self.eff_grid = np.linspace(E.min() * 0.96, E.max() * 1.02, EFF_GRID_N)
        self.band_krf = self.band_rw = None
        self.krf_bias_z = self.rw_bias_z = None
        for which in ("krf", "rw"):
            band = self.intervals(which, self.eff_grid)
            if band is None:
                continue
            at_E = self.intervals(which, E)
            zmax = float(np.nanmax(np.abs(at_E["z"]))) \
                if np.isfinite(at_E["z"]).any() else float("nan")
            if which == "krf":
                self.band_krf, self.krf_bias_z = band, zmax
            else:
                self.band_rw, self.rw_bias_z = band, zmax

    def intervals(self, which, E):
        """_mc_interval of one model over an array of energies, in chunks of
        BAND_CHUNK so the temporaries stay small; None without MC samples."""
        E = np.atleast_1d(np.asarray(E, dtype=float))
        parts = []
        for i in range(0, len(E), BAND_CHUNK):
            got = self._model_samples(which, E[i:i + BAND_CHUNK])
            if got is None:
                return None
            parts.append(_mc_interval(*got))
        out = {key: np.concatenate([q[key] for q in parts])
               for key in parts[0] if key != "B"}
        out["B"] = parts[0]["B"]
        return out

    def rw_curve(self, E, params=None):
        """The Radware curve in the user's units: f_radware_5p / k."""
        p = self.radware_popt if params is None else params
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            return f_radware_5p(E, *p) / self.radware_scale

    def fit_notes(self):
        """Plain-language caveats about the fits, possibly empty.

        Not failures -- conditions the user must know to read the numbers:
        a model that could not be fitted, a fit with no degrees of freedom,
        a Birge ratio so large that the scatter is systematic, and the
        KRF-vs-Radware spread no band contains.
        """
        out = []
        n = self.n
        if self.radware_popt is None:
            out.append(f"Radware not fitted: its 5 free parameters need at least "
                       f"5 lines (6 for a Birge ratio); this file has {n}."
                       if n < 5 else
                       f"Radware fit failed from all {N_RW_EXTRA_STARTS + 2} "
                       f"starting points.")
        for name, ndf in (("KRF", self.eff_ndf), ("Radware", self.radware_ndf)):
            if ndf is not None and ndf <= 0:
                out.append(f"{name} has no degrees of freedom (ndf = {ndf}): the "
                           f"curve passes through every point, there is no Birge "
                           f"ratio, and its band reflects the stated uncertainties "
                           f"only.")
        for name, B in (("KRF", self.eff_birge), ("Radware", self.radware_birge)):
            if B is not None and np.isfinite(B) and B > BIRGE_SYSTEMATIC:
                out.append(f"{name} Birge ratio {B:.2f}: the points scatter "
                           f"{B:.1f}x beyond their stated uncertainties. The band "
                           f"is widened by B as if that scatter were random; if it "
                           f"is systematic (for Ra-226 typically uncorrected "
                           f"true-coincidence summing), lines affected by it are "
                           f"not described by the band.")
        ms = getattr(self, "model_spread", None)
        if ms is not None:
            out.append(f"KRF and Radware differ by up to {100 * ms['max_rel']:+.1f} % "
                       f"inside the data (at {ms['at_E']:.0f} keV). Neither band "
                       f"contains this model uncertainty; quote it separately "
                       f"where it matters.")
        return out

    def mc_health_warnings(self):
        """Human-readable warnings about the efficiency MC, possibly empty."""
        out = []
        for name, z, dchi2 in (
                ("KRF", self.krf_bias_z, self.krf_selfcheck_dchi2),
                ("Radware", self.rw_bias_z, self.rw_selfcheck_dchi2)):
            if z is not None and np.isfinite(z) and z > BIAS_Z_WARN:
                out.append(f"{name} MC not centred on the best fit "
                           f"(bias check max|z| = {z:.2f} > {BIAS_Z_WARN:g}); "
                           f"its uncertainty is unreliable")
            if dchi2 is not None and dchi2 > 1.0:
                out.append(f"{name} MC refit does not reproduce the best fit "
                           f"on the unperturbed data (Δχ² = {dchi2:.3g})")
        return out

    def energy_outside_fit(self, E_val):
        """True if E_val lies outside the energies the efficiency was fitted to.

        Inside that range a query interpolates between calibration lines;
        outside it the answer is model extrapolation, which KRF and Radware can
        disagree about by orders of magnitude a few tens of keV beyond the
        data.
        """
        return not (float(self.E.min()) <= float(E_val) <= float(self.E.max()))

    def channel_outside_fit(self, ch_val):
        """True if ch_val lies outside the channels the energy fit used."""
        return not (float(self.ch.min()) <= float(ch_val) <= float(self.ch.max()))

    def predict_efficiency(self, E_val):
        """Both models' efficiency and 1σ at E₀, as _mc_interval dicts.

        Returns {"krf": {...}, "rw": {...}} with value = the best fit, minus /
        plus = the Birge-scaled 1σ half-widths from the MC 16/50/84 %
        quantiles, sigma = their symmetric mean, and median / z = the bias
        check -- exactly the rule the plotted band uses, so a query and the
        band through the same energy agree by construction.  (They used to
        be the MC mean ± B·std, which on the v4.8 Radware fit sat outside the
        band and away from the best-fit curve.)

        Both models can blow up when extrapolated outside the fitted range —
        KRF's exp(d/E) overflows, Radware's log-polynomial diverges — so
        non-finite MC samples are filtered out, and fewer than 10 survivors
        give NaN rather than a meaningless σ.  A model with no MC samples gets
        NaN everywhere; its best fit is still evaluated when there is one.
        """
        E = float(E_val)
        out = {}
        for which, popt in (("krf", self.eff_popt), ("rw", self.radware_popt)):
            got = self._model_samples(which, E)
            if got is not None:
                out[which] = _mc_interval(*got)
                continue
            iv = _nan_interval()
            if popt is not None:
                with np.errstate(over="ignore", invalid="ignore",
                                 divide="ignore"):
                    bf = float(f_krf(E, *popt) if which == "krf"
                               else self.rw_curve(E))
                iv["value"] = bf if np.isfinite(bf) else float("nan")
            out[which] = iv
        # The model systematic at E0: neither interval contains it.
        kv, rv = out["krf"]["value"], out["rw"]["value"]
        out["model_diff"] = (kv - rv if np.isfinite(kv) and np.isfinite(rv)
                             else float("nan"))
        return out

    def predict(self, ch_val, dch_val):
        """Invert ch(E) at ch₀ ± Δch₀ by Monte Carlo.

        Seeded from SEED so re-querying the same channel reproduces the same
        numbers: every query is appended to the _Res.txt log, and two identical
        queries disagreeing there would be indistinguishable from a real change.

        The returned σ inflate the calibration's share of the spread by its
        Birge ratio (see _inflate_calibration_part) and leave the query's own
        Δch alone.  They used to be the unscaled spread, which on a dataset
        with B1 = 3345 reported a few 1e-5 keV for a calibration whose
        residuals were a few tenths of a keV.
        """
        rng  = np.random.default_rng(SEED)
        ch_m = rng.normal(ch_val, dch_val, N_MC_PRED)
        idx  = rng.integers(0, N_MC_CAL, N_MC_PRED)
        pl   = self.params_lin[idx]; pq = self.params_quad[idx]

        a1, b1 = pl[:, 0], pl[:, 1]
        with np.errstate(divide="ignore", invalid="ignore"):
            E_lin = (ch_m - a1) / b1
        # The linear solution is the reference used to pick the physical root
        # of the quadratic — see _invert_quadratic().
        E_quad = _invert_quadratic(pq[:, 0], pq[:, 1], pq[:, 2], ch_m, E_lin)

        # Best-fit inversion using popt (no MC noise)
        a1b, b1b = self.popt1
        El_bf = (ch_val - a1b) / b1b
        El_bf = float(El_bf) if np.isfinite(El_bf) else float("nan")
        Eq_bf = float(_invert_quadratic(*self.popt2, ch_val, El_bf))

        # The same parameter samples at the exact channel: the spread of these
        # is the calibration's share alone, with the query's Δch taken out.
        with np.errstate(divide="ignore", invalid="ignore"):
            E_lin_cal = (ch_val - a1) / b1
        E_quad_cal = _invert_quadratic(pq[:, 0], pq[:, 1], pq[:, 2],
                                       ch_val, E_lin_cal)
        El, sl = _finite_mean_std(E_lin)
        Eq, sq = _finite_mean_std(E_quad)
        sl = _inflate_calibration_part(sl, _finite_mean_std(E_lin_cal)[1],
                                       _band_scale(self.birge1))
        sq = _inflate_calibration_part(sq, _finite_mean_std(E_quad_cal)[1],
                                       _band_scale(self.birge2))
        return El, sl, Eq, sq, El_bf, Eq_bf
