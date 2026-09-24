#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Energy & Efficiency Calibration  —  Interactive GUI
====================================================
Workflow:
  1. Click "Read calibration data"   →  choose your calibration data file
  2. Click "Make calibration"        →  energy + efficiency MC (~10–20 s)
  3. Enter ch₀ ± Δch₀, press Enter / "Calculate Energy"
     → energy results; any previous efficiency query is cleared
  4. Enter E₀ (keV), press Enter / "Get Efficiency"
     → efficiency results; any previous energy query is cleared
  5. Either "✕ Clear" button resets BOTH panels
  6. Right-click a subplot → Save As that subplot only
     Right-click figure margin → Save As full figure
  7. ☀ / 🌙 button (top-right) → light / dark theme

File columns (7, no index, ABSOLUTE uncertainties):
  ch  delta_ch  N  delta_N  E[keV]  I[%]  delta_I[%]
"""

import os, sys, shutil, tempfile, webbrowser, datetime, warnings
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from scipy.optimize import curve_fit, OptimizeWarning

# Writing the SpectraTools export lives in its own module: it needs no Tk and
# is therefore importable and testable without a display.  It MUST stay listed
# in packaging/linux/build_deb.sh and caleneff.spec, which install a fixed file
# list and would otherwise ship a DEB and RPM that cannot import it.
import spectratools_export

# curve_fit raises OptimizeWarning when it cannot estimate the covariance.
# The MC loops discard pcov entirely and skip any sample whose parameters come
# back non-finite, so 10 000 iterations would flood stderr with warnings the
# code already handles.  Where pcov *is* used (the energy best-fit) a failed
# estimate still shows up as inf in the results file, so nothing is hidden.
warnings.filterwarnings("ignore", category=OptimizeWarning)
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as _plt

# ── Settings ───────────────────────────────────────────────────────────────────
N_MC_CAL  =  10_000
N_MC_PRED =  10_000
N_MC_EFF  =  10_000
SEED      = 42

# Number of MC parameter sets used to draw a 1σ confidence band.  The band is
# a percentile envelope, which converges long before 10 000 samples — capping
# it keeps every redraw (a.u./% toggle, theme switch) cheap and bounds the
# temporary array to N_BAND × len(E_grid) floats.
N_BAND    =   4_000

# Minimum number of calibration points.  The quadratic energy fit has 3 free
# parameters, so ndf = n − 3 > 0 requires n ≥ 4; below that the Birge ratio
# divides by zero.  The efficiency models need more (KRF 4, Radware 5) and are
# guarded individually rather than blocking the load.
MIN_POINTS = 4

# Figure save formats — used by every right-click "Save as …" dialog.
# Matplotlib backends actually supported: png, pdf, svg, eps, ps, jpg/jpeg,
# tif/tiff, webp, raw, rgba, pgf.  We surface the user-friendly ones.
SAVE_FILETYPES = [
    ("PNG  (lossless raster)",       "*.png"),
    ("PDF  (vector, publications)",  "*.pdf"),
    ("SVG  (vector, editable)",      "*.svg"),
    ("EPS  (PostScript, LaTeX)",     "*.eps"),
    ("PostScript",                   "*.ps"),
    ("JPEG (lossy raster)",          "*.jpg *.jpeg"),
    ("TIFF (lossless raster)",       "*.tif *.tiff"),
    ("WebP image",                   "*.webp"),
    ("All files",                    "*.*"),
]
# Extensions matplotlib's savefig() understands directly via format=...
SAVE_EXTS = {"png", "pdf", "svg", "eps", "ps",
             "jpg", "jpeg", "tif", "tiff", "webp"}

def _documents_dir():
    """The user's Documents folder, or their home directory if absent.

    Everything the program writes defaults here rather than beside the
    executable.  An installed copy lives under Program Files, which a normal
    user cannot write to, so a results file placed next to the program -- or
    next to the bundled sample data, which is inside the program folder --
    could not be created at all.
    """
    home = os.path.expanduser("~")
    docs = os.path.join(home, "Documents")
    return docs if os.path.isdir(docs) else home

def _base_dir():
    """User-facing starting directory for file dialogs."""
    return _documents_dir()

def _is_writable(directory):
    """True if a file can actually be created in `directory`.

    Decided by creating one, not by inspecting permissions: on Windows the
    Program Files ACL grants a standard user read and execute but not write,
    and os.access(W_OK) does not reliably report that.
    """
    if not directory or not os.path.isdir(directory):
        return False
    try:
        fd, tmp = tempfile.mkstemp(prefix=".caleneff_wtest", dir=directory)
    except Exception:
        return False
    os.close(fd)
    try:
        os.remove(tmp)
    except OSError:
        pass
    return True

def _results_dir_for(datapath):
    """Directory to write the results file for `datapath` into.

    Beside the data file when that is writable, which is where the user
    expects it.  It is not writable when an installed copy auto-loads its own
    bundled sample: that file sits inside the program folder, so fall back to
    Documents instead of failing the write.
    """
    d = os.path.dirname(os.path.abspath(datapath))
    return d if _is_writable(d) else _documents_dir()

def _resource_dir():
    """Directory where bundled assets (data files, icon) live.
    In a PyInstaller onedir build sys._MEIPASS points to the _internal
    sub-folder; in onefile / script mode it equals _base_dir()."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

DEFAULT_FILE = os.path.join(_resource_dir(), "226Ra_En_Area.txt")   # auto-load if present

# ── Theme palettes ──────────────────────────────────────────────────────────────
_DARK = {
    'DARK':   "#1e1e2e", 'PANEL':  "#2a2a3e",
    'ACCENT': "#89b4fa", 'GREEN':  "#a6e3a1",
    'RED':    "#f38ba8", 'YELLOW': "#f9e2af",
    'TEXT':   "#ffffff", 'MUTED':  "#9090a8",   # white text, light-grey muted
    'BORDER': "#45475a", 'LIN_C':  "#89b4fa",
    'QUAD_C': "#f38ba8", 'EFF_C':  "#a6e3a1", 'RAD_C':  "#cba6f7",
}
_LIGHT = {
    'DARK':   "#f0f4f8", 'PANEL':  "#ffffff",
    'ACCENT': "#1565c0", 'GREEN':  "#2e7d32",
    'RED':    "#c62828", 'YELLOW': "#c35000",
    'TEXT':   "#000000", 'MUTED':  "#4a4a5a",   # black text, dark-grey muted
    'BORDER': "#bdbdbd", 'LIN_C':  "#1565c0",
    'QUAD_C': "#c62828", 'EFF_C':  "#2e7d32",  'RAD_C':  "#6c31a8",
}

# ── Reference URL & tooltip texts ──────────────────────────────────────────────
# A concise explanation of the Birge ratio used in precision measurements:
_BIRGE_URL = "https://arxiv.org/html/2406.08293v3"

_EN_CAL_TIP = (
    "Energy calibration parameters\n\n"
    "Linear:    ch(E) = a + b·E\n"
    "Quadratic: ch(E) = a + b·E + c·E²\n\n"
    "stat  = 1σ from covariance matrix  √diag(C)\n"
    "Birge = stat × B   where  B = √(χ²/ndf)\n\n"
    "Birge ratio B = √(χ²/ndf)\n"
    "  B ≈ 1 → fit matches stated σ (good)\n"
    "  B > 1 → scatter > σ; errors multiplied by B\n"
    "  B < 1 → stated σ are conservative\n\n"
    "χ²/ndf = Σ[(obs−fit)²/σ²]/(n−p)   reduced chi²\n"
    "RMS    = √[Σ(obs−fit)²/n]   in channel units\n\n"
    "Click label to open Birge ratio reference ↗"
)
_EFF_CAL_TIP = (
    "Efficiency calibration parameters\n\n"
    "ε(E) = (a·E + b/E) · exp(c·E + d/E)\n\n"
    "Measured efficiency:  ε = N / I\n"
    "Propagated error:  Δε = ε·√[(ΔN/N)² + (ΔI/I)²]\n\n"
    "MC fits ok: successful refits / 10,000 iterations\n"
    "Birge ratio: same interpretation as energy cal.\n\n"
    "Click label to open Birge ratio reference ↗"
)

# Per-row result tooltips (energy)
_TIP_E_MC = (
    "MC mean energy: mean of 10,000 MC inversions.\n"
    "Each trial draws ch₀ from N(ch₀, Δch₀) and\n"
    "samples calibration parameters from their MC\n"
    "distribution, then inverts ch(E) to find E."
)
_TIP_DE = (
    "MC 1σ uncertainty: standard deviation of the\n"
    "10,000 MC energy samples.\n"
    "Includes both channel measurement noise and\n"
    "calibration parameter uncertainty."
)
_TIP_E_BF = (
    "Best-fit energy: direct inversion of the best-fit\n"
    "calibration curve at the input channel ch₀.\n\n"
    "  Linear:    E = (ch₀ − a) / b\n"
    "  Quadratic: solve  a + b·E + c·E² = ch₀\n\n"
    "Use the MC σ row above as the uncertainty."
)
# Per-row result tooltips (efficiency — KRF)
_TIP_EFF_MC = (
    "KRF MC mean efficiency at E₀:\n"
    "Mean of f_krf(E₀) over 10,000 MC refits,\n"
    "each with N and I resampled from N(μ, σ).\n"
    "Value is in arbitrary units (depends on geometry)."
)
_TIP_DEFF = (
    "KRF MC 1σ uncertainty on ε:\n"
    "Standard deviation of ε over 10,000 refits of the\n"
    "KRF function, each with N and I resampled from\n"
    "their stated Gaussian uncertainties."
)
_TIP_EFF_BF = (
    "KRF best-fit efficiency: f_krf(E₀, *popt)\n"
    "where popt is the least-squares fit to all data.\n\n"
    "Use the MC σ row above as the uncertainty."
)
# Per-row result tooltips (efficiency — Radware)
_TIP_RAD_MC = (
    "Radware MC mean efficiency at E₀:\n"
    "Mean of f_radware_5p(E₀) over MC refits,\n"
    "each with N and I resampled from N(μ, σ).\n"
    "5-parameter model: C=0 and G=15 fixed\n"
    "(Radford's effit.c default procedure).\n"
    "Value is in arbitrary units (depends on geometry)."
)
_TIP_RAD_DEFF = (
    "Radware MC 1σ uncertainty on ε:\n"
    "Standard deviation of ε over MC refits of the\n"
    "5-parameter Radware function (C=0, G=15 fixed).\n"
    "Each iteration uses a fresh parset() seed\n"
    "from the resampled data — Radford's procedure."
)
_TIP_RAD_BF = (
    "Radware best-fit efficiency: f_radware_5p(E₀, *popt)\n"
    "where popt = [a1,a2,a4,a5,a6] (5-parameter fit,\n"
    "C=0 and G=15 fixed following Radford effit.c).\n\n"
    "Use the MC σ row above as the uncertainty."
)

# ── Formatting helper ──────────────────────────────────────────────────────────
def _ns(x, fmt=".5g"):
    """Format a float as a fixed-width string, or '—' if non-finite / non-numeric."""
    return (f"{x:{fmt}}" if isinstance(x, float) and np.isfinite(x) else "—")


def _band_percentiles(band, lo=15.87, hi=84.13):
    """1σ percentile envelope of an (n_samples, n_grid) MC band.

    Non-finite entries are masked to NaN first: KRF's exp(d/E) overflows to
    +inf and Radware's log-polynomial diverges when the curve is evaluated
    well outside the fitted range, and np.nanpercentile ignores NaN but not
    inf — so without the mask a handful of runaway samples would swallow the
    whole envelope.  A grid column that is entirely non-finite yields NaN,
    which fill_between renders as a gap rather than a bogus band.
    """
    band = np.where(np.isfinite(band), band, np.nan)
    with np.errstate(invalid="ignore"):
        return np.nanpercentile(band, [lo, hi], axis=0)


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
        r  = f / F                 (≥ 1 when both regions give ε < 1)

    With r = f/F >= 1 (both f1, f2 negative for eff < 1) and g large,
    (1 + r**g)**(-1/g) -> 1/r, so log_eff -> F: the result is dominated by
    max(f1, f2), the LESS negative branch, i.e. the higher efficiency. An
    earlier version of this docstring claimed the opposite.

    Implementation faithful to Radford's `eval()` in effit.c — note that f1,
    f2 are *log-efficiencies* (typically negative), NOT positive numbers.
    The earlier `np.maximum(…, 1e-30)` clipping forced them positive and made
    the loss landscape pathological — hence MC stalls.
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
    g_log_r = np.clip(g * np.log(r), -700.0, 700.0)
    log_y3  = -np.logaddexp(0.0, g_log_r) / g

    log_eff = np.clip(f * np.exp(log_y3), -700.0, 700.0)
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


def _radware_p0_5p(E, eff):
    """Radford parset() seed for the 5-parameter model.

    Calls _radware_p0() and strips the two fixed entries (a3=0, g=15),
    returning [a1, a2, a4, a5, a6] ready for f_radware_5p.
    """
    full = _radware_p0(E, eff)   # [a1, a2, 0, a4, a5, 0, 15]
    return [full[0], full[1], full[3], full[4], full[5]]


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


# ── Hover tooltip ──────────────────────────────────────────────────────────────
class _Tooltip:
    """Hover tooltip that reliably appears and disappears on Windows.

    Positioning: tooltip is placed 24 px below the *current cursor position*,
    never at the widget's bottom edge.  This ensures the popup never appears
    directly under the cursor (which would fire <Enter> on it immediately and
    cause a close/reopen flicker on tall widgets like the info_lbl).

    Dismissal: a 100 ms polling loop runs inside the tooltip Toplevel's own
    after() queue.  This avoids relying on root-window <Motion> propagation,
    which Canvas create_window() children can intercept.  <Leave> on the host
    widget remains a fast-path close.

    A 350 ms cooldown after each close prevents Windows from reopening the
    tooltip via the synthetic <Enter> it sends when the Toplevel disappears.
    """

    _COOLDOWN_MS = 350

    def __init__(self, widget, text, url=None, delay=450):
        self._w        = widget
        self._text     = text
        self._url      = url
        self._delay    = delay
        self._show_job = None
        self._cd_job   = None
        self._tip      = None
        self._cooling  = False

        widget.bind("<Enter>",   self._enter)
        widget.bind("<Leave>",   self._leave)
        widget.bind("<Destroy>", self._on_destroy)
        if url:
            widget.bind("<Button-1>", lambda e: webbrowser.open(url), add="+")
            try: widget.config(cursor="hand2")
            except Exception: pass

    # ── event handlers ────────────────────────────────────────────────
    def _enter(self, _event=None):
        if self._cooling: return
        self._cancel_show()
        self._show_job = self._w.after(self._delay, self._show)

    def _leave(self, _event=None):
        self._cancel_show()
        self._close()

    def _on_destroy(self, _event=None):
        self._cancel_show()
        self._cancel_cd()
        tip, self._tip = self._tip, None
        if tip:
            try: tip.destroy()
            except Exception: pass

    # ── internal helpers ──────────────────────────────────────────────
    def _cancel_show(self):
        if self._show_job:
            try: self._w.after_cancel(self._show_job)
            except Exception: pass
            self._show_job = None

    def _cancel_cd(self):
        if self._cd_job:
            try: self._w.after_cancel(self._cd_job)
            except Exception: pass
            self._cd_job = None

    def _start_cooldown(self):
        self._cooling = True
        self._cancel_cd()
        try:
            self._cd_job = self._w.after(self._COOLDOWN_MS, self._end_cooldown)
        except Exception:
            self._cooling = False

    def _end_cooldown(self):
        self._cooling = False
        self._cd_job  = None

    def _close(self):
        tip, self._tip = self._tip, None
        if tip:
            try: tip.destroy()
            except Exception: pass
            self._start_cooldown()

    # ── poll loop (runs inside tooltip Toplevel) ──────────────────────
    def _poll(self):
        """100 ms heartbeat: close when the cursor leaves the host widget."""
        if not self._tip:
            return
        try:
            mx = self._w.winfo_pointerx()
            my = self._w.winfo_pointery()
            wx = self._w.winfo_rootx(); wy = self._w.winfo_rooty()
            ww = self._w.winfo_width(); wh = self._w.winfo_height()
            inside = (wx <= mx <= wx + ww) and (wy <= my <= wy + wh)
        except Exception:
            inside = False
        if not inside:
            self._close()
            return
        try:
            self._tip.after(100, self._poll)
        except Exception:
            self._close()

    # ── popup ─────────────────────────────────────────────────────────
    def _show(self):
        if self._tip:
            return
        try:
            # Place tooltip 24 px below the CURSOR, not the widget edge.
            # This guarantees the popup never appears under the hot-spot.
            mx = self._w.winfo_pointerx()
            my = self._w.winfo_pointery()
            sw = self._w.winfo_screenwidth()
            sh = self._w.winfo_screenheight()
            x  = min(mx + 16, sw - 462)
            y  = my + 24

            self._tip = tw = tk.Toplevel()
            tw.wm_overrideredirect(True)
            tw.configure(bg="#1e1e2e")
            tw.attributes('-topmost', True)

            outer = tk.Frame(tw, bg="#45475a", padx=1, pady=1)
            outer.pack(fill="both", expand=True)
            inner = tk.Frame(outer, bg="#1e1e2e")
            inner.pack(fill="both", expand=True)
            tk.Label(inner, text=self._text,
                     bg="#1e1e2e", fg="#ffffff",
                     font=("Segoe UI", 9), justify="left",
                     padx=10, pady=8, wraplength=440).pack(anchor="w")
            if self._url:
                lnk = tk.Label(inner,
                               text="\U0001f517  Click widget to open reference",
                               bg="#1e1e2e", fg="#89b4fa",
                               font=("Segoe UI", 8, "underline"),
                               cursor="hand2", padx=10, pady=(0, 6))
                lnk.pack(anchor="w")
                lnk.bind("<Button-1>", lambda e: webbrowser.open(self._url))

            tw.update_idletasks()
            tip_h = tw.winfo_height()
            if y + tip_h > sh:      # flip above cursor when near screen bottom
                y = my - tip_h - 8
            y = max(0, y)

            tw.wm_geometry(f"+{max(x, 0)}+{y}")
            tw.lift()

            # Start the poll loop from the tooltip's own event queue
            tw.after(100, self._poll)
        except Exception:
            self._tip = None


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
        # Normalization factor for % mode: eff_norm = 100 / max(KRF curve)
        # Multiply any a.u. value by eff_norm to convert to %.
        self.eff_norm   = None
        self.eff_ready  = False
        self.mc_krf_ok  = self.mc_rw_ok = self.mc_bad = 0

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
                "    ch   Δch   N   ΔN   E[keV]   I[%]   ΔI[%]")

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

    def _fit_best(self, cb):
        if cb: cb(5, "Computing best-fit parameters …")
        p1_0 = _wls(self.E, self.ch, self.dch, 1)
        p2_0 = _wls(self.E, self.ch, self.dch, 2)
        self.popt1, self.pcov1 = curve_fit(f_lin,  self.E, self.ch, p0=p1_0,
                                            sigma=self.dch, absolute_sigma=True)
        self.popt2, self.pcov2 = curve_fit(f_quad, self.E, self.ch, p0=p2_0,
                                            sigma=self.dch, absolute_sigma=True)
        n = len(self.ch)
        r1 = self.ch - f_lin(self.E,  *self.popt1)
        r2 = self.ch - f_quad(self.E, *self.popt2)
        self.chi2_1 = float(np.sum((r1/self.dch)**2)); self.ndf1 = n - 2
        self.chi2_2 = float(np.sum((r2/self.dch)**2)); self.ndf2 = n - 3
        self.birge1 = _birge(self.chi2_1, self.ndf1)
        self.birge2 = _birge(self.chi2_2, self.ndf2)
        self.rms1   = float(np.sqrt(np.mean(r1**2)))
        self.rms2   = float(np.sqrt(np.mean(r2**2)))

    def _mc(self, cb):
        if cb: cb(12, f"MC calibration ({N_MC_CAL:,} samples) …")
        n   = len(self.ch); W = 1.0 / self.dch
        A1  = np.column_stack([np.ones(n), self.E])            * W[:, None]
        A2  = np.column_stack([np.ones(n), self.E, self.E**2]) * W[:, None]
        rng = np.random.default_rng(SEED)
        yw  = rng.normal(self.ch, self.dch, (N_MC_CAL, n)) * W[None, :]
        if cb: cb(20, "MC: linear fits …")
        self.params_lin  = _batch_wls(A1, yw)
        if cb: cb(58, "MC: quadratic fits …")
        self.params_quad = _batch_wls(A2, yw)
        if cb: cb(97, "Finalising …")

    def calibrate_efficiency(self, progress_cb=None):
        if not self.data_loaded: raise RuntimeError("Load data first.")
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

        # Normalization factor: 100 / peak(KRF curve) for % display mode
        _E_fine = np.linspace(max(self.E.min() * 0.9, 1.0),
                               self.E.max() * 1.1, 2000)
        _eff_fine = f_krf(_E_fine, *popt_krf)
        _eff_ok   = _eff_fine[np.isfinite(_eff_fine) & (_eff_fine > 0)]
        _peak = float(np.max(_eff_ok)) if len(_eff_ok) > 0 else 1.0
        self.eff_norm = 100.0 / max(_peak, 1e-30)

        # ── Radware best-fit — 5-parameter (Radford's procedure) ────────
        # Radford's effit.c fixes C (a3) = 0 and G = 15, leaving 5 free
        # parameters: A (a1), B (a2), D (a4), E (a5), F (a6).
        # Primary seed: Radford's parset() — data-driven; fallback to the
        # polyfit alternative.  Both use LM (Bevington CURFIT), no bounds.
        if progress_cb: progress_cb(8, "Best-fit Radware curve (5-param, C=0, G=15) …")
        p0_5        = _radware_p0_5p(self.E, eff)           # parset seed
        p0_poly_all = _radware_p0_polyfit(self.E, eff)
        p0_5_poly   = [p0_poly_all[i] for i in [0, 1, 3, 4, 5]]   # drop a3, g

        popt_rw = None
        best_chi2_rw = np.inf
        for seed in (p0_5, p0_5_poly):
            try:
                pp, _ = curve_fit(
                    f_radware_5p, self.E, eff, p0=seed,
                    sigma=deff, absolute_sigma=True,
                    method="lm", maxfev=20000,
                )
                if not (np.all(np.isfinite(pp)) and np.all(np.abs(pp) < 500)):
                    continue
                chi2 = float(np.sum(((eff - f_radware_5p(self.E, *pp)) / deff)**2))
                if chi2 < best_chi2_rw:
                    best_chi2_rw, popt_rw = chi2, pp
            except Exception:
                pass

        if popt_rw is not None:
            self.radware_popt = popt_rw          # [a1, a2, a4, a5, a6]
            res_r = eff - f_radware_5p(self.E, *popt_rw)
            self.radware_rms   = float(np.sqrt(np.mean(res_r**2)))
            self.radware_ndf   = len(self.E) - 5    # 5 free parameters
            self.radware_chi2  = float(np.sum((res_r/deff)**2))
            self.radware_birge = _birge(self.radware_chi2, self.radware_ndf)
        else:
            self.radware_popt = None
            popt_rw = None        # disable Radware in MC loop

        # ── MC loop — resample N and I, refit both ────────────────────
        # Speed strategy (10 000 iters × 2 models must finish in ~1 min):
        #   • Skip pathological samples (N_s≤0, I_s≤0, non-finite ratios).
        #   • Use Levenberg-Marquardt (method="lm") — 2-3× faster than TRF
        #     because LM has cheaper per-iteration linear algebra and no
        #     bound-projection step.  Warm-start from a good best-fit keeps
        #     the iterate inside the physical region without explicit bounds.
        #   • Relax tolerances to 1e-5 (default 1e-8 is overkill for MC —
        #     we only need σ-level accuracy, not micro-precision).
        #   • Hard cap maxfev=1500 → bounded worst case ~50 ms / fit.
        #   • Validate result is finite & sane before accepting; otherwise
        #     fall through to the next seed.
        #   • Progress callback every 100 iter → UI updates ~1× per second.
        rng = np.random.default_rng(SEED)
        store_krf = []; store_rw = []
        n_bad     = 0          # count rejected pathological samples
        MC_MAXFEV = 1500
        MC_TOL    = 1e-5       # ftol = xtol = gtol for MC fits

        for k in range(N_MC_EFF):
            if progress_cb and k % 100 == 0:
                progress_cb(10 + int(88*k/N_MC_EFF),
                            f"Efficiency MC ({k:,}/{N_MC_EFF:,}) …")

            N_s = rng.normal(self.N,     self.dN)
            I_s = rng.normal(self.I_pct, self.dI_pct)

            # Reject non-physical samples
            if (N_s <= 0).any() or (I_s <= 0).any():
                n_bad += 1
                continue
            eff_s = N_s / I_s
            if not np.isfinite(eff_s).all() or (eff_s <= 0).any():
                n_bad += 1
                continue

            # KRF — LM, warm-start from best-fit popt.
            try:
                pp, _ = curve_fit(
                    f_krf, self.E, eff_s, p0=popt_krf,
                    sigma=deff, absolute_sigma=True,
                    maxfev=MC_MAXFEV, method="lm",
                    ftol=MC_TOL, xtol=MC_TOL, gtol=MC_TOL,
                )
                if np.all(np.isfinite(pp)):
                    store_krf.append(pp)
            except Exception:
                pass

            # Radware — 5-parameter (C=0, G=15 fixed), Radford's procedure.
            # For each MC sample a fresh parset() seed is computed from eff_s,
            # then a single LM run is attempted — exactly as Radford's effit.c
            # calls parset() then fitter() for each new data set.
            # No rolling warm-start: the data-driven seed from the resampled
            # efficiency is specific to this sample and avoids chain bias.
            if self.radware_popt is not None:
                p0_mc = _radware_p0_5p(self.E, eff_s)
                try:
                    pp_r, _ = curve_fit(
                        f_radware_5p, self.E, eff_s, p0=p0_mc,
                        sigma=deff, absolute_sigma=True,
                        maxfev=MC_MAXFEV, method="lm",
                        ftol=MC_TOL, xtol=MC_TOL, gtol=MC_TOL,
                    )
                    if (np.all(np.isfinite(pp_r))
                            and np.all(np.abs(pp_r) < 500)):
                        store_rw.append(pp_r)
                except Exception:
                    pass

        if n_bad:
            # Surface to status bar via the progress callback (does not
            # interrupt UI; just informational)
            if progress_cb:
                progress_cb(99,
                    f"MC complete — {n_bad:,} non-physical samples skipped")

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
        self.eff_ready  = True
        if progress_cb: progress_cb(100, "Efficiency calibration done.")

    def predict_efficiency(self, E_val):
        """Evaluate both efficiency models and their MC spread at E₀.

        Both models can blow up when extrapolated outside the fitted range —
        KRF's exp(d/E) overflows for large d/E, Radware's log-polynomial
        diverges — so non-finite MC samples are filtered out, and fewer than
        10 survivors is reported as NaN rather than as a meaningless σ.
        """
        E = float(E_val)

        # KRF.  params_eff is always 2-D (possibly with zero rows) so the
        # column slices below are safe even when every MC fit failed.
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            if len(self.params_eff):
                p = self.params_eff
                v_k = f_krf(E, p[:, 0], p[:, 1], p[:, 2], p[:, 3])
                krf_mean, krf_std = _finite_mean_std(v_k, min_n=10)
            else:
                krf_mean = krf_std = float("nan")
            krf_bf_raw = float(f_krf(E, *self.eff_popt))
        krf_bf = krf_bf_raw if np.isfinite(krf_bf_raw) else float("nan")

        # Radware — 5-parameter model (C=0, G=15 fixed)
        rw_mean = rw_std = rw_bf = float("nan")
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            if self.params_radware is not None and len(self.params_radware):
                p = self.params_radware      # (N_ok, 5): [a1, a2, a4, a5, a6]
                v_r = f_radware_5p(E, p[:, 0], p[:, 1], p[:, 2],
                                   p[:, 3], p[:, 4])
                rw_mean, rw_std = _finite_mean_std(v_r, min_n=10)
            if self.radware_popt is not None:
                rw_bf_raw = float(f_radware_5p(E, *self.radware_popt))
                rw_bf = rw_bf_raw if np.isfinite(rw_bf_raw) else float("nan")
        return krf_mean, krf_std, krf_bf, rw_mean, rw_std, rw_bf

    def predict(self, ch_val, dch_val):
        """Invert ch(E) at ch₀ ± Δch₀ by Monte Carlo.

        Seeded from SEED so re-querying the same channel reproduces the same
        numbers: every query is appended to the _Res.txt log, and two identical
        queries disagreeing there would be indistinguishable from a real change.
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

        return (*_finite_mean_std(E_lin), *_finite_mean_std(E_quad),
                El_bf, Eq_bf)


# ─────────────────────────────────────────────────────────────────────────────
class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("CalEnEff")
        self._theme_name = "dark"
        for k, v in _DARK.items(): setattr(self, k, v)
        self.configure(bg=self.DARK)
        self.geometry("1540x900")
        self.resizable(True, True)
        # window icon
        _ico = os.path.join(_resource_dir(), "CalEnEff.ico")
        if os.path.exists(_ico):
            try:
                self.iconbitmap(_ico)
            except Exception:
                pass

        self.bind("<F1>", lambda e: self._open_howto())
        self.bind("<Control-o>", lambda e: self._on_read())
        self.bind("<Control-O>", lambda e: self._on_read())
        self.bind("<Control-s>", lambda e: self._on_file_save())
        self.bind("<Control-S>", lambda e: self._on_file_save())
        self._busy = False           # True while a calibration is running
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.engine      = CalibrationEngine()
        self._q_arts     = []   # energy query artists on ax_m/ax_r1/ax_r2
        self._eff_q_arts = []   # efficiency query artists on ax_eff
        self._res_file   = None  # path of the current results .txt file
        self._eff_pct_mode       = False   # False → a.u., True → %
        self._last_eff_query_au  = None    # (E_val, krf_mean, krf_std, krf_bf,
                                           #  rw_mean, rw_std, rw_bf) in a.u.

        self._apply_ttk_style("dark")
        self._build_ui()

        self._autoload_job = None
        if os.path.isfile(DEFAULT_FILE):
            self._autoload_job = self.after(100, self._autoload_default)

    def _autoload_default(self):
        """Load the bundled sample file shortly after startup.

        Skipped if the user already picked a file — the 100 ms delay exists so
        the window paints first, which leaves a window in which they can.
        """
        self._autoload_job = None
        if not self.engine.data_loaded:
            self._do_load(DEFAULT_FILE)

    def _on_close(self):
        """Ignore the window-close button while a calibration is running.

        _on_calibrate() calls update(), which dispatches input events — without
        this guard a click on [X] would destroy the widgets mid-run and the
        next progress callback would raise TclError from inside the fit.
        """
        if self._busy:
            self._status("⏳  Calibration running — please wait …", self.YELLOW)
            return
        self.destroy()

    # ── SpectraTools export ───────────────────────────────
    #
    # Three files, in the formats SpectraTools 6.1.1 reads:
    #
    #   <stem>_EnergyCal.txt  read by calibration.read_coefficients_file():
    #                         bare numbers, one coefficient per line.
    #   <stem>_bins.txt       read by efficiency_io.read_saved_efficiency():
    #                         '# SpectraTools relative efficiency' marker on
    #                         line 1, '# columns:' naming 5 columns with no dE,
    #                         one row per channel.
    #   <stem>_peaks.txt      the same curve at the calibration lines only. Its
    #                         reader resolves a _peaks file to the _bins file
    #                         beside it, so both are written together.

    def _on_export_spectratools(self):
        """Write the energy and efficiency calibrations for SpectraTools."""
        e = self.engine
        if not (e.cal_ready and e.eff_ready):
            messagebox.showinfo("Export for SpectraTools",
                                "Run a calibration first.")
            return
        try:
            a_cal, b_cal = spectratools_export.energy_cal_channel_to_energy(e)
        except ValueError as exc:
            messagebox.showerror("Export for SpectraTools", str(exc))
            return

        stem = filedialog.asksaveasfilename(
            title="Export for SpectraTools — base name",
            initialdir=_results_dir_for(e.filepath),
            initialfile=os.path.splitext(os.path.basename(e.filepath))[0],
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not stem:
            return
        stem = os.path.splitext(stem)[0]

        channels = simpledialog.askinteger(
            "Export for SpectraTools",
            "Number of channels in the spectrum this will be applied to:",
            parent=self, initialvalue=16384, minvalue=2, maxvalue=1 << 22)
        if not channels:
            return

        try:
            written = spectratools_export.write_files(
                e, stem, channels, a_cal, b_cal)
        except Exception as exc:
            messagebox.showerror("Export for SpectraTools",
                                 "Could not write the export:\n%s" % exc)
            self._status("⚠  Export failed: %s" % exc, self.YELLOW)
            return
        self._status("✔  Exported %d files for SpectraTools → %s"
                     % (len(written), os.path.basename(stem)), self.GREEN)
        messagebox.showinfo(
            "Export for SpectraTools",
            "Written:\n\n" + "\n".join(os.path.basename(p) for p in written)
            + "\n\nIn SpectraTools, load the _bins file from the efficiency "
              "window, and the _EnergyCal file as linear energy coefficients.")

    def _show_file_popup(self):
        """File menu: Open / Save / Save as / Exit.

        Save and Save as stay disabled until a calibration has produced
        results — there is nothing to write before that.
        """
        ready = self.engine.cal_ready
        m = tk.Menu(self, tearoff=0)
        m.add_command(label="Open…", accelerator="Ctrl+O",
                      command=self._on_read)
        m.add_separator()
        m.add_command(label="Save", accelerator="Ctrl+S",
                      command=self._on_file_save,
                      state="normal" if ready else "disabled")
        m.add_command(label="Save as…",
                      command=self._on_file_save_as,
                      state="normal" if ready else "disabled")
        m.add_separator()
        m.add_command(label="Export for SpectraTools…",
                      command=self._on_export_spectratools,
                      state="normal" if self.engine.eff_ready else "disabled")
        m.add_separator()
        m.add_command(label="Exit", command=self._on_close)
        x = self._file_btn.winfo_rootx()
        y = self._file_btn.winfo_rooty() + self._file_btn.winfo_height()
        try:
            m.tk_popup(x, y)
        finally:
            m.grab_release()

    def _on_file_save(self):
        """Write the results to the default {basename}_Res.txt path.

        A calibration already writes that file automatically, so usually this
        only reports where it is.  It does real work when the automatic write
        failed — a read-only directory, say — because _write_cal_to_file()
        sets _res_file back to None in that case, and this retries it.
        """
        if not self.engine.cal_ready:
            return
        if not (self._res_file and os.path.exists(self._res_file)):
            self._write_cal_to_file()
        if self._res_file and os.path.exists(self._res_file):
            self._status("✔  Results saved → %s"
                         % os.path.basename(self._res_file), self.GREEN)

    def _on_file_save_as(self):
        """Save the results under a new name and keep writing there.

        Copies the existing file rather than regenerating its text: query
        results are APPENDED to the results file as they are calculated, so a
        regenerated copy would silently drop every query already run.
        """
        if not self.engine.cal_ready:
            return
        if not (self._res_file and os.path.exists(self._res_file)):
            self._write_cal_to_file()
        if not (self._res_file and os.path.exists(self._res_file)):
            messagebox.showerror("Save as", "There are no results to save yet.")
            return
        path = filedialog.asksaveasfilename(
            title="Save results as", defaultextension=".txt",
            initialdir=os.path.dirname(self._res_file),
            initialfile=os.path.basename(self._res_file),
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            if os.path.abspath(path) != os.path.abspath(self._res_file):
                shutil.copyfile(self._res_file, path)
        except Exception as exc:
            messagebox.showerror("Save as", "Could not save:\n%s" % exc)
            self._status("⚠  Could not save results: %s" % exc, self.YELLOW)
            return
        # Adopt the new path so later queries append there, not to the old file.
        self._res_file = path
        self._status("✔  Results saved → %s" % os.path.basename(path),
                     self.GREEN)

    # ── Help button popup ──────────────────────────────────────────────
    def _show_help_popup(self):
        m = tk.Menu(self, tearoff=0)
        m.add_command(label="HowTo (F1)",         command=self._open_howto)
        m.add_command(label="Knowledge Database", command=self._open_knowledge_db)
        m.add_separator()
        m.add_command(label="About",              command=self._open_about)
        x = self._help_btn.winfo_rootx()
        y = self._help_btn.winfo_rooty() + self._help_btn.winfo_height()
        try:
            m.tk_popup(x, y)
        finally:
            m.grab_release()

    def _open_howto(self):
        from help_content import build_howto_html, open_help_page
        open_help_page(build_howto_html())

    def _open_knowledge_db(self):
        from help_content import build_knowledge_database_html, open_help_page
        open_help_page(build_knowledge_database_html())

    def _open_about(self):
        from help_content import build_about_html, open_help_page
        open_help_page(build_about_html())

    # ── ttk style ─────────────────────────────────────────────────────
    def _apply_ttk_style(self, name):
        s = ttk.Style()
        try: s.theme_use("default")
        except Exception: pass
        if name == "dark":
            s.configure("TProgressbar",
                troughcolor="#2a2a3e", background="#89b4fa",
                bordercolor="#45475a", lightcolor="#89b4fa", darkcolor="#89b4fa")
            s.configure("TScrollbar",
                troughcolor="#2a2a3e", background="#45475a",
                bordercolor="#1e1e2e", arrowcolor="#9090a8")
        else:
            s.configure("TProgressbar",
                troughcolor="#e0e0e0", background="#1565c0",
                bordercolor="#bdbdbd", lightcolor="#1565c0", darkcolor="#1565c0")
            s.configure("TScrollbar",
                troughcolor="#e0e0e0", background="#bdbdbd",
                bordercolor="#f0f4f8", arrowcolor="#4a4a5a")

    # ── UI builder ────────────────────────────────────────────────────
    def _build_ui(self):
        # top bar
        top = tk.Frame(self, bg=self.DARK, pady=7)
        top.pack(fill="x", padx=14)
        self._file_btn = tk.Button(
            top, text="File ▾",
            font=("Segoe UI", 9),
            bg=self.BORDER, fg=self.TEXT,
            activebackground=self.MUTED, activeforeground=self.DARK,
            relief="flat", bd=0, padx=8, pady=4,
            cursor="hand2", command=self._show_file_popup)
        self._file_btn.pack(side="left", padx=(0, 12))
        tk.Label(top,
                 text="Energy & Efficiency Calibration  —  Monte Carlo Fit",
                 font=("Segoe UI", 15, "bold"),
                 bg=self.DARK, fg=self.ACCENT).pack(side="left")
        self._help_btn = tk.Button(
            top, text="Help ▾",
            font=("Segoe UI", 9),
            bg=self.BORDER, fg=self.TEXT,
            activebackground=self.MUTED, activeforeground=self.DARK,
            relief="flat", bd=0, padx=8, pady=4,
            cursor="hand2", command=self._show_help_popup)
        self._help_btn.pack(side="right", padx=(4, 0))
        self._theme_btn = tk.Button(
            top, text="☀  Light",
            font=("Segoe UI", 9),
            bg=self.BORDER, fg=self.TEXT,
            activebackground=self.MUTED, activeforeground=self.DARK,
            relief="flat", bd=0, padx=8, pady=4,
            cursor="hand2", command=self._toggle_theme)
        self._theme_btn.pack(side="right", padx=(8, 0))
        self.status_lbl = tk.Label(top, text="Select a data file to begin.",
                                   font=("Segoe UI", 10),
                                   bg=self.DARK, fg=self.MUTED)
        self.status_lbl.pack(side="right")

        # progress bar
        self.prog_var = tk.IntVar(value=0)
        self.prog_bar = ttk.Progressbar(self, variable=self.prog_var,
                                        maximum=100, mode="determinate")
        self.prog_bar.pack(fill="x", padx=14, pady=(0, 4))

        # paned layout
        pane = tk.PanedWindow(self, orient="horizontal",
                              bg=self.BORDER, sashwidth=4)
        pane.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # ── LEFT PANEL ────────────────────────────────────────────────
        left = tk.Frame(pane, bg=self.PANEL, padx=14, pady=12)
        pane.add(left, minsize=340, width=420)

        canvas_l = tk.Canvas(left, bg=self.PANEL, highlightthickness=0)
        scroll_l = ttk.Scrollbar(left, orient="vertical", command=canvas_l.yview)
        inner = tk.Frame(canvas_l, bg=self.PANEL)
        inner.bind("<Configure>",
                   lambda e: canvas_l.configure(scrollregion=canvas_l.bbox("all")))
        canvas_l.create_window((0, 0), window=inner, anchor="nw")
        canvas_l.configure(yscrollcommand=scroll_l.set)
        canvas_l.pack(side="left", fill="both", expand=True)
        scroll_l.pack(side="right", fill="y")
        def _on_mousewheel(event):
            """Scroll the left panel, on all three windowing systems.

            Windows and macOS deliver <MouseWheel> carrying event.delta —
            ±120 per notch on Windows but only ±1 on macOS, so the old
            `delta // 120` truncated to zero and did nothing there.  X11
            (Linux) delivers Button-4 / Button-5 with no delta at all, so the
            DEB and RPM builds had no wheel scrolling whatsoever.  Normalise
            all three to a single step.
            """
            if   event.num == 4: step = -1        # X11 wheel up
            elif event.num == 5: step =  1        # X11 wheel down
            elif event.delta:    step = -1 if event.delta > 0 else 1
            else:                return
            canvas_l.yview_scroll(step, "units")

        for _seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            canvas_l.bind_all(_seq, _on_mousewheel)

        lp = inner   # short alias

        # -- file
        self._sep(lp, "DATA FILE")
        fp_frame = tk.Frame(lp, bg=self.PANEL)
        fp_frame.pack(fill="x", pady=(4, 8))
        self.filepath_var = tk.StringVar(value="(none)")
        tk.Label(fp_frame, textvariable=self.filepath_var,
                 bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 8),
                 anchor="w", wraplength=390).pack(fill="x")

        # -- calibration buttons
        bf1 = tk.Frame(lp, bg=self.PANEL); bf1.pack(fill="x", pady=(0, 4))
        self.btn_read = self._btn(bf1, "\U0001f4c2  Read calibration data",
                                  self._on_read, self.ACCENT,
                                  side="left", padx=(0, 4))
        self.btn_cal  = self._btn(bf1, "⚙  Make calibration",
                                  self._on_calibrate, "#cba6f7",
                                  side="left", state="disabled")

        # ── ENERGY QUERY ──────────────────────────────────────────────
        self._sep(lp, "ENERGY QUERY  ch → E")
        ig = tk.Frame(lp, bg=self.PANEL); ig.pack(fill="x", pady=(4, 2))
        self.ch_var  = self._entry_row(ig, 0, "Measured channel  ch₀",    "2000")
        self.dch_var = self._entry_row(ig, 1, "Channel uncertainty  Δch₀", "0.5")
        ig.columnconfigure(0, weight=1)

        bf2 = tk.Frame(lp, bg=self.PANEL); bf2.pack(fill="x", pady=(8, 4))
        self.btn_calc = self._btn(bf2, "⟶  Calculate Energy",
                                  self._calculate, self.GREEN,
                                  side="left", padx=(0, 4), state="disabled")
        self.btn_clr  = self._btn(bf2, "✕  Clear",
                                  self._clear_all, self.YELLOW,
                                  side="left", state="disabled")

        # energy result blocks
        self._sep(lp, "LINEAR FIT   ch = a + b·E")
        self.lin_frame = tk.Frame(lp, bg=self.PANEL)
        self.lin_frame.pack(fill="x", pady=(4, 8))
        self._result_block(self.lin_frame, "lin", self.LIN_C)

        self._sep(lp, "QUADRATIC FIT   ch = a + b·E + c·E²")
        self.quad_frame = tk.Frame(lp, bg=self.PANEL)
        self.quad_frame.pack(fill="x", pady=(4, 8))
        self._result_block(self.quad_frame, "quad", self.QUAD_C)

        # ── EFFICIENCY QUERY ──────────────────────────────────────────
        self._sep(lp, "EFFICIENCY QUERY  E → ε")
        eq = tk.Frame(lp, bg=self.PANEL); eq.pack(fill="x", pady=(4, 2))
        tk.Label(eq, text="Energy  E₀  (keV)",
                 bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 10), anchor="w").grid(
                     row=0, column=0, sticky="ew", pady=4)
        self.E_q_var = tk.StringVar(value="1000")
        ent_eq = tk.Entry(eq, textvariable=self.E_q_var, width=12,
                          font=("Segoe UI", 12, "bold"),
                          bg=self.DARK, fg=self.ACCENT,
                          insertbackground=self.ACCENT, relief="flat", bd=5)
        ent_eq.grid(row=0, column=1, sticky="e", padx=(10, 0))
        ent_eq.bind("<Return>", lambda e: self._query_eff())
        eq.columnconfigure(0, weight=1)

        bfq = tk.Frame(lp, bg=self.PANEL); bfq.pack(fill="x", pady=(8, 4))
        self.btn_eff_query = self._btn(bfq, "⟶  Get Efficiency",
                                       self._query_eff, self.EFF_C,
                                       side="left", padx=(0, 4), state="disabled")
        self.btn_eff_clr   = self._btn(bfq, "✕  Clear",
                                       self._clear_all, self.YELLOW,
                                       side="left", state="disabled")
        self._pct_btn      = self._btn(bfq, "a.u. → %",
                                       self._toggle_pct_mode, self.TEXT,
                                       side="left", padx=(4, 0), state="disabled")

        # efficiency result
        self._sep(lp, "EFFICIENCY RESULT")
        self._eff_val_mc    = tk.StringVar(value="—")
        self._eff_derr      = tk.StringVar(value="—")
        self._eff_val_bf    = tk.StringVar(value="—")
        self._eff_rw_val_mc = tk.StringVar(value="—")
        self._eff_rw_derr   = tk.StringVar(value="—")
        self._eff_rw_val_bf = tk.StringVar(value="—")

        def _eff_block(parent, sub_label, sub_color, rows):
            tk.Label(parent, text=sub_label, bg=self.PANEL, fg=sub_color,
                     font=("Segoe UI", 8, "bold italic"),
                     anchor="w").pack(anchor="w", padx=4, pady=(5, 1))
            fr = tk.Frame(parent, bg=self.PANEL); fr.pack(fill="x")
            for i, (lbl_txt, var, col, hint, tip) in enumerate(rows):
                r = 2 * i
                lbl_w = tk.Label(fr, text=lbl_txt, bg=self.PANEL, fg=self.TEXT,
                                 font=("Segoe UI", 9), anchor="w")
                lbl_w.grid(row=r, column=0, sticky="ew", padx=2, pady=(3, 0))
                tk.Label(fr, textvariable=var, bg=self.PANEL, fg=col,
                         font=("Courier New", 11, "bold"),
                         anchor="e").grid(row=r, column=1, sticky="e",
                                          padx=4, pady=(3, 0))
                hint_lbl = tk.Label(fr, text=f"  ← {hint}",
                                    bg=self.PANEL, fg=self.MUTED,
                                    font=("Segoe UI", 7, "italic"), anchor="w")
                hint_lbl.grid(row=r+1, column=0, columnspan=2,
                              sticky="ew", padx=12, pady=(0, 1))
                _Tooltip(lbl_w,    tip)
                _Tooltip(hint_lbl, tip)
            fr.columnconfigure(1, weight=1)

        _eff_block(lp, "KRF", self.EFF_C, [
            ("ε  (MC mean)",  self._eff_val_mc, self.EFF_C,
             "mean of 10k MC refits",   _TIP_EFF_MC),
            ("Δε  (MC σ)",    self._eff_derr,   self.YELLOW,
             "σ of 10k MC refits",      _TIP_DEFF),
            ("ε  (best-fit)", self._eff_val_bf, self.EFF_C,
             "f_krf(E₀, *popt)",        _TIP_EFF_BF),
        ])
        _eff_block(lp, "Radware", self.RAD_C, [
            ("ε  (MC mean)",  self._eff_rw_val_mc, self.RAD_C,
             "mean of MC refits",         _TIP_RAD_MC),
            ("Δε  (MC σ)",    self._eff_rw_derr,   self.YELLOW,
             "σ of MC refits",            _TIP_RAD_DEFF),
            ("ε  (best-fit)", self._eff_rw_val_bf, self.RAD_C,
             "f_radware_5p(E₀, *popt)",   _TIP_RAD_BF),
        ])
        tk.Frame(lp, bg=self.PANEL, height=6).pack()   # bottom spacer

        # ── RIGHT PANEL ───────────────────────────────────────────────
        right = tk.Frame(pane, bg=self.DARK)
        pane.add(right, minsize=700)

        self._right_en  = tk.Frame(right, bg=self.DARK)
        self._right_en.pack(side="left", fill="both", expand=True, padx=(4, 2), pady=4)
        self._right_eff = tk.Frame(right, bg=self.DARK)
        self._right_eff.pack(side="left", fill="both", expand=True, padx=(2, 4), pady=4)

        self.fig_en  = Figure(figsize=(5.5, 6.5), dpi=100, facecolor=self.DARK,
                              layout="constrained")
        self.fig_eff = Figure(figsize=(5.5, 6.5), dpi=100, facecolor=self.DARK,
                              layout="constrained")
        self._init_axes()
        self.canvas_en  = FigureCanvasTkAgg(self.fig_en,  master=self._right_en)
        self.canvas_en.get_tk_widget().pack(fill="both", expand=True)
        self.canvas_eff = FigureCanvasTkAgg(self.fig_eff, master=self._right_eff)
        self.canvas_eff.get_tk_widget().pack(fill="both", expand=True)
        self._rclick_cid_en  = self.fig_en.canvas.mpl_connect(
            'button_press_event', self._on_fig_en_rightclick)
        self._rclick_cid_eff = self.fig_eff.canvas.mpl_connect(
            'button_press_event', self._on_fig_eff_rightclick)

    # ── widget helpers ────────────────────────────────────────────────
    def _sep(self, parent, text):
        tk.Frame(parent, bg=self.BORDER, height=1).pack(fill="x", pady=(8, 2))
        lbl = tk.Label(parent, text=text, bg=self.PANEL, fg=self.MUTED,
                       font=("Segoe UI", 8, "bold"))
        lbl.pack(anchor="w")
        return lbl

    def _btn(self, parent, text, cmd, color, side="left",
             padx=(0, 0), state="normal"):
        b = tk.Button(parent, text=text,
                      font=("Segoe UI", 9, "bold"),
                      bg=color, fg=self.DARK,
                      activebackground=color, activeforeground=self.DARK,
                      relief="flat", bd=0, padx=10, pady=7,
                      cursor="hand2", state=state, command=cmd)
        b.pack(side=side, padx=padx, expand=True, fill="x")
        return b

    def _entry_row(self, parent, row, label, default):
        tk.Label(parent, text=label, bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 10), anchor="w").grid(
                     row=row, column=0, sticky="ew", pady=4)
        var = tk.StringVar(value=default)
        ent = tk.Entry(parent, textvariable=var, width=12,
                       font=("Segoe UI", 12, "bold"),
                       bg=self.DARK, fg=self.ACCENT,
                       insertbackground=self.ACCENT, relief="flat", bd=5)
        ent.grid(row=row, column=1, sticky="e", padx=(10, 0))
        ent.bind("<Return>", lambda e: self._calculate())
        return var

    def _result_block(self, parent, tag, color):
        """
        3 rows: MC mean, MC σ, best-fit.  Each row = value + italic hint.
        Tooltips on both the label and the (wider) hint label.
        """
        rows = [
            ("E  (MC mean)",   "E_mc", "keV",
             "mean of 10k MC draws",        _TIP_E_MC),
            ("ΔE  (MC σ)",     "dE",   "keV",
             "σ of 10k MC draws",           _TIP_DE),
            ("E  (best-fit)",  "E_bf", "keV",
             "direct inversion of ch(E)",   _TIP_E_BF),
        ]
        for i, (lbl, key, unit, hint, tip) in enumerate(rows):
            r = 2 * i
            lbl_w = tk.Label(parent, text=lbl, bg=self.PANEL, fg=self.TEXT,
                             font=("Segoe UI", 9), anchor="w")
            lbl_w.grid(row=r, column=0, sticky="ew", padx=2, pady=(4, 0))
            var = tk.StringVar(value="—")
            # E_mc (i=0) and E_bf (i=2) use the fit colour; ΔE (i=1) is yellow
            tk.Label(parent, textvariable=var, bg=self.PANEL,
                     fg=color if i != 1 else self.YELLOW,
                     font=("Courier New", 11, "bold"),
                     anchor="e").grid(row=r, column=1, sticky="e",
                                      padx=4, pady=(4, 0))
            tk.Label(parent, text=unit, bg=self.PANEL, fg=self.MUTED,
                     font=("Segoe UI", 8)).grid(row=r, column=2,
                                                sticky="w", pady=(4, 0))
            hint_lbl = tk.Label(parent, text=f"  ← {hint}",
                                bg=self.PANEL, fg=self.MUTED,
                                font=("Segoe UI", 7, "italic"), anchor="w")
            hint_lbl.grid(row=r+1, column=0, columnspan=3,
                          sticky="ew", padx=12, pady=(0, 2))
            _Tooltip(lbl_w,    tip)
            _Tooltip(hint_lbl, tip)
            setattr(self, f"_{tag}_{key}", var)
        parent.columnconfigure(1, weight=1)

    def _set(self, tag, key, val):
        getattr(self, f"_{tag}_{key}").set(val)

    def _reset_energy_results(self):
        for tag in ("lin", "quad"):
            for key in ("E_mc", "dE", "E_bf"):
                self._set(tag, key, "—")

    def _reset_eff_results(self):
        self._eff_val_mc.set("—"); self._eff_val_bf.set("—"); self._eff_derr.set("—")
        self._eff_rw_val_mc.set("—"); self._eff_rw_val_bf.set("—")
        self._eff_rw_derr.set("—")
        self._last_eff_query_au = None

    def _reset_results(self):
        self._reset_energy_results(); self._reset_eff_results()

    # ── matplotlib ────────────────────────────────────────────────────
    def _style_ax(self, ax):
        ax.set_facecolor(self.PANEL)
        ax.tick_params(colors=self.MUTED, labelsize=8)
        for sp in ax.spines.values(): sp.set_color(self.BORDER)
        ax.grid(True, color=self.BORDER, lw=0.6, alpha=0.9)

    def _init_axes(self):
        # Re-assert constrained layout after clear() — keeps spacing automatic
        self.fig_en.clear()
        self.fig_eff.clear()
        self.fig_en.set_layout_engine("constrained")
        self.fig_eff.set_layout_engine("constrained")

        # Manual margins removed — constrained_layout handles all spacing
        gs_en  = self.fig_en.add_gridspec(3, 1, height_ratios=[4, 1.4, 1.4])
        self.ax_m  = self.fig_en.add_subplot(gs_en[0])
        self.ax_r1 = self.fig_en.add_subplot(gs_en[1], sharex=self.ax_m)
        self.ax_r2 = self.fig_en.add_subplot(gs_en[2], sharex=self.ax_m)

        gs_eff = self.fig_eff.add_gridspec(3, 1, height_ratios=[4, 1.4, 1.8])
        self.ax_eff    = self.fig_eff.add_subplot(gs_eff[0])
        self.ax_eff_r  = self.fig_eff.add_subplot(gs_eff[1], sharex=self.ax_eff)
        self.ax_eff_mc = self.fig_eff.add_subplot(gs_eff[2])

        for ax in (self.ax_m, self.ax_r1, self.ax_r2,
                   self.ax_eff, self.ax_eff_r, self.ax_eff_mc):
            self._style_ax(ax)

        # Energy column — constrained_layout accounts for every xlabel/ticklabel
        # automatically, so all three axes can carry "E (keV)" without overlap.
        _plt.setp(self.ax_m.get_xticklabels(),  visible=False)
        _plt.setp(self.ax_r1.get_xticklabels(), visible=False)
        self.ax_m.set_ylabel("Channel  ch",  color=self.TEXT, fontsize=9)
        self.ax_m.set_xlabel("E  (keV)",     color=self.TEXT, fontsize=9)
        self.ax_r1.set_ylabel("Δch (lin.)",  color=self.TEXT, fontsize=8)
        self.ax_r1.set_xlabel("E  (keV)",    color=self.TEXT, fontsize=8)
        self.ax_r2.set_ylabel("Δch (quad.)", color=self.TEXT, fontsize=8)
        self.ax_r2.set_xlabel("E  (keV)",    color=self.TEXT, fontsize=9)
        self.ax_m.set_title("ch(E)  calibration",
                             color=self.TEXT, fontsize=10, pad=4)
        self.ax_m.text(0.5, 0.5, "Load data and run calibration",
                       transform=self.ax_m.transAxes, ha="center", va="center",
                       color=self.MUTED, fontsize=12, style="italic")

        # Efficiency column — constrained_layout handles spacing for all labels.
        _plt.setp(self.ax_eff.get_xticklabels(), visible=False)
        self.ax_eff.set_ylabel("ε = N/I  (a.u.)", color=self.TEXT, fontsize=9)
        self.ax_eff.set_xlabel("E  (keV)",         color=self.TEXT, fontsize=9)
        self.ax_eff.set_title("Efficiency  ε(E)",
                               color=self.TEXT, fontsize=10, pad=4)
        self.ax_eff.text(0.5, 0.5, "Run efficiency calibration",
                         transform=self.ax_eff.transAxes,
                         ha="center", va="center",
                         color=self.MUTED, fontsize=12, style="italic")
        self.ax_eff_r.set_ylabel("Δε",       color=self.TEXT, fontsize=8)
        self.ax_eff_r.set_xlabel("E  (keV)", color=self.TEXT, fontsize=9)
        # ax_eff_mc: independent axis (shows ε distribution at queried E₀)
        self.ax_eff_mc.set_xlabel("ε  (a.u.)", color=self.TEXT, fontsize=8)
        self.ax_eff_mc.set_ylabel("MC count",  color=self.TEXT, fontsize=8)
        self.ax_eff_mc.set_title("MC distribution at E₀",
                                  color=self.TEXT, fontsize=9, pad=3)
        self.ax_eff_mc.text(0.5, 0.5, "Query an energy to see MC distribution",
                            transform=self.ax_eff_mc.transAxes,
                            ha="center", va="center",
                            color=self.MUTED, fontsize=9, style="italic")

        self._xlim = self._ylim = None
        self._eff_xlim = self._eff_ylim = None
        if hasattr(self, "canvas_en"):  self.canvas_en.draw()
        if hasattr(self, "canvas_eff"): self.canvas_eff.draw()

    def _draw_calibration(self):
        e = self.engine; E = e.E; ch = e.ch; dch = e.dch
        for ax in (self.ax_m, self.ax_r1, self.ax_r2):
            ax.cla(); self._style_ax(ax)
        _plt.setp(self.ax_m.get_xticklabels(),  visible=False)
        _plt.setp(self.ax_r1.get_xticklabels(), visible=False)
        self.ax_m.set_ylabel("Channel  ch",  color=self.TEXT, fontsize=9)
        self.ax_m.set_xlabel("E  (keV)",     color=self.TEXT, fontsize=9)
        self.ax_r1.set_ylabel("Δch (lin.)",  color=self.TEXT, fontsize=8)
        self.ax_r1.set_xlabel("E  (keV)",    color=self.TEXT, fontsize=8)
        self.ax_r2.set_ylabel("Δch (quad.)", color=self.TEXT, fontsize=8)
        self.ax_r2.set_xlabel("E  (keV)",    color=self.TEXT, fontsize=9)
        fname = os.path.basename(e.filepath) if e.filepath else "calibration"
        self.ax_m.set_title(f"ch(E) — {fname}  ({e.n} peaks)",
                            color=self.TEXT, fontsize=10, pad=4)

        E_g = np.linspace(E.min()*0.96, E.max()*1.02, 500)
        clg = f_lin(E_g,  *e.popt1); cqg = f_quad(E_g, *e.popt2)
        rng = np.random.default_rng(1)
        idx = rng.integers(0, N_MC_CAL, 4000)
        pl = e.params_lin[idx]; pq = e.params_quad[idx]
        cl = pl[:,0:1] + pl[:,1:2]*E_g
        cq = pq[:,0:1] + pq[:,1:2]*E_g + pq[:,2:3]*E_g**2
        ll, lh = np.percentile(cl, [15.87, 84.13], axis=0)
        ql, qh = np.percentile(cq, [15.87, 84.13], axis=0)
        b1 = _band_scale(e.birge1); b2 = _band_scale(e.birge2)
        ll = clg - b1*(clg - ll); lh = clg + b1*(lh - clg)
        ql = cqg - b2*(cqg - ql); qh = cqg + b2*(qh - cqg)
        r1 = ch - f_lin(E, *e.popt1); r2 = ch - f_quad(E, *e.popt2)

        ax = self.ax_m
        ax.errorbar(E, ch, yerr=dch, fmt='o', ms=5,
                    color=self.TEXT, ecolor=self.MUTED,
                    capsize=3, capthick=1.2, elinewidth=1.2,
                    label="Data  (±Δch)", zorder=6)
        ax.plot(E_g, clg, color=self.LIN_C,  lw=2, label="Linear")
        ax.fill_between(E_g, ll, lh, alpha=0.18, color=self.LIN_C)
        ax.plot(E_g, cqg, color=self.QUAD_C, lw=2, label="Quadratic")
        ax.fill_between(E_g, ql, qh, alpha=0.18, color=self.QUAD_C)
        ax.legend(fontsize=8, facecolor=self.PANEL,
                  labelcolor=self.TEXT, edgecolor=self.BORDER, loc="upper left")

        for ax_r, res, col, rms in ((self.ax_r1, r1, self.LIN_C,  e.rms1),
                                    (self.ax_r2, r2, self.QUAD_C, e.rms2)):
            ax_r.errorbar(E, res, yerr=dch, fmt='o', ms=4,
                          color=col, ecolor=self.MUTED, capsize=2, elinewidth=1)
            ax_r.axhline(0, color=col, lw=1.4, ls="--")
            ax_r.axhline( rms, color=col, lw=0.8, ls=":", alpha=0.7)
            ax_r.axhline(-rms, color=col, lw=0.8, ls=":", alpha=0.7)
            ax_r.text(0.99, 0.82, f"RMS={rms:.3f} ch",
                      transform=ax_r.transAxes, ha="right", fontsize=8, color=col)

        self._xlim = ax.get_xlim(); self._ylim = ax.get_ylim()
        self._q_arts.clear()
        self.canvas_en.draw()

    def _draw_efficiency(self):
        e = self.engine; E = e.E
        sc, y_unit = self._eff_scale()

        eff  = e.eff  * sc
        deff = e.deff * sc

        ax = self.ax_eff; ax.cla(); self._style_ax(ax)
        _plt.setp(ax.get_xticklabels(), visible=False)
        ax.set_ylabel(f"ε = N/I  ({y_unit})", color=self.TEXT, fontsize=9)
        ax.set_xlabel("E  (keV)",               color=self.TEXT, fontsize=9)
        fname = os.path.basename(e.filepath) if e.filepath else "efficiency"
        ax.set_title(f"ε(E) — {fname}  ({e.n} peaks)",
                     color=self.TEXT, fontsize=10, pad=4)
        ax.errorbar(E, eff, yerr=deff, fmt='o', ms=5,
                    color=self.TEXT, ecolor=self.MUTED,
                    capsize=3, capthick=1.2, elinewidth=1.2,
                    label="Data  (±Δε)", zorder=6)
        E_g = np.linspace(E.min()*0.96, E.max()*1.02, 400)

        # Data-driven y-limits — anchor to measured points, not MC bands
        y_lo = max(0.0, float(np.nanmin(eff - deff)) * 0.70)
        y_hi =         float(np.nanmax(eff + deff))   * 1.40
        if y_hi <= y_lo:
            y_hi = y_lo + 1.0

        # KRF curve + MC band (clip band to data-relative window)
        eg_k = f_krf(E_g, *e.eff_popt) * sc
        ax.plot(E_g, eg_k, color=self.EFF_C, lw=2, label="KRF")
        if e.params_eff is not None and len(e.params_eff) > 0:
            pk = e.params_eff[:N_BAND]
            band_k = f_krf(E_g[None, :], pk[:, 0:1], pk[:, 1:2],
                           pk[:, 2:3], pk[:, 3:4]) * sc
            kl, kh = _band_percentiles(band_k)
            bk = _band_scale(e.eff_birge)
            kl = eg_k - bk * (eg_k - kl)
            kh = eg_k + bk * (kh - eg_k)
            kl = np.clip(kl, y_lo * 0.5 - 0.1*y_hi, y_hi * 1.5)
            kh = np.clip(kh, y_lo * 0.5 - 0.1*y_hi, y_hi * 1.5)
            ax.fill_between(E_g, kl, kh, alpha=0.18, color=self.EFF_C,
                            label=f"KRF 1σ  (×{bk:.2f})")

        # Radware curve + MC band  (5-parameter: C=0, G=15 fixed)
        if e.radware_popt is not None:
            eg_r = f_radware_5p(E_g, *e.radware_popt) * sc
            ax.plot(E_g, eg_r, color=self.RAD_C, lw=2, ls="--",
                    label="Radware")
            if e.params_radware is not None and len(e.params_radware) > 0:
                pr = e.params_radware[:N_BAND]
                band_r = f_radware_5p(E_g[None, :], pr[:, 0:1], pr[:, 1:2],
                                      pr[:, 2:3], pr[:, 3:4], pr[:, 4:5]) * sc
                rl, rh = _band_percentiles(band_r)
                br = _band_scale(e.radware_birge)
                rl = eg_r - br * (eg_r - rl)
                rh = eg_r + br * (rh - eg_r)
                rl = np.clip(rl, y_lo * 0.5 - 0.1*y_hi, y_hi * 1.5)
                rh = np.clip(rh, y_lo * 0.5 - 0.1*y_hi, y_hi * 1.5)
                ax.fill_between(E_g, rl, rh, alpha=0.14, color=self.RAD_C,
                                label=f"Rad 1σ  (×{br:.2f})")

        ax.set_ylim(y_lo, y_hi)
        ax.legend(fontsize=8, facecolor=self.PANEL,
                  labelcolor=self.TEXT, edgecolor=self.BORDER, loc="upper right")
        self._eff_q_arts.clear()
        self._eff_xlim = ax.get_xlim(); self._eff_ylim = (y_lo, y_hi)

        ax_r = self.ax_eff_r; ax_r.cla(); self._style_ax(ax_r)
        ax_r.set_ylabel(f"Δε ({y_unit})", color=self.TEXT, fontsize=8)
        ax_r.set_xlabel("E  (keV)", color=self.TEXT, fontsize=9)
        res_k = (e.eff - f_krf(E, *e.eff_popt)) * sc
        ax_r.errorbar(E, res_k, yerr=deff, fmt='o', ms=4,
                      color=self.EFF_C, ecolor=self.MUTED, capsize=2, elinewidth=1,
                      label="KRF")
        ax_r.axhline(0,                    color=self.EFF_C, lw=1.4, ls="--")
        ax_r.axhline( e.eff_rms * sc,      color=self.EFF_C, lw=0.8, ls=":", alpha=0.7)
        ax_r.axhline(-e.eff_rms * sc,      color=self.EFF_C, lw=0.8, ls=":", alpha=0.7)
        ax_r.text(0.01, 0.82, f"KRF RMS={e.eff_rms*sc:.4g}",
                  transform=ax_r.transAxes, ha="left", fontsize=7, color=self.EFF_C)
        all_res = [res_k]
        if e.radware_popt is not None:
            res_r = (e.eff - f_radware_5p(E, *e.radware_popt)) * sc
            ax_r.errorbar(E, res_r, yerr=deff, fmt='s', ms=4,
                          color=self.RAD_C, ecolor=self.MUTED, capsize=2,
                          elinewidth=1, label="Radware")
            ax_r.text(0.01, 0.60, f"Rad RMS={e.radware_rms*sc:.4g}",
                      transform=ax_r.transAxes, ha="left", fontsize=7,
                      color=self.RAD_C)
            all_res.append(res_r)
        # Compute rmax per residual array (each has shape (n,) == deff.shape)
        # so we avoid a shape mismatch from concatenating before adding deff.
        rmax = max(float(np.nanmax(np.abs(r) + deff)) for r in all_res) * 1.45
        if rmax < 1e-30:
            rmax = 1.0
        ax_r.set_ylim(-rmax, rmax)
        ax_r.legend(fontsize=7, facecolor=self.PANEL,
                    labelcolor=self.TEXT, edgecolor=self.BORDER,
                    loc="upper right")

        self._reset_eff_mc_placeholder()
        self.canvas_eff.draw()

    def _reset_eff_mc_placeholder(self):
        _, y_unit = self._eff_scale()
        ax = self.ax_eff_mc; ax.cla(); self._style_ax(ax)
        ax.set_xlabel(f"ε  ({y_unit})", color=self.TEXT, fontsize=8)
        ax.set_ylabel("MC count",       color=self.TEXT, fontsize=8)
        ax.set_title("MC distribution at E₀", color=self.TEXT, fontsize=9, pad=3)
        ax.text(0.5, 0.5, "Query an energy to see MC distribution",
                transform=ax.transAxes, ha="center", va="center",
                color=self.MUTED, fontsize=9, style="italic")

    # ── button handlers ───────────────────────────────────────────────
    def _on_read(self):
        path = filedialog.askopenfilename(
            title="Select calibration data file", initialdir=_base_dir(),
            filetypes=[("Text / data files", "*.txt *.dat *.csv *.asc"),
                       ("All files", "*.*")])
        if path: self._do_load(path)

    def _do_load(self, path):
        # Cancel the pending startup auto-load.  Without this it can fire from
        # inside the modal error dialog's own event loop below and re-enter
        # this method, loading the sample file behind an error message that is
        # still on screen — leaving the status bar describing one file while a
        # different one is actually loaded.
        if self._autoload_job is not None:
            try: self.after_cancel(self._autoload_job)
            except Exception: pass
            self._autoload_job = None

        self._res_file = None
        try:
            self.engine.reset(); self.engine.load(path)
        except Exception as exc:
            self.filepath_var.set("(none)")
            self.btn_cal.config(state="disabled")
            self._reset_results()
            self._init_axes()
            self._status(f"❌  {exc}", self.RED)
            messagebox.showerror("Load error", str(exc))
            return
        e = self.engine
        self.filepath_var.set(path)
        self._status(
            f"✔  Loaded  {os.path.basename(path)}  —  {e.n} peaks  |  "
            f"E: {e.E.min():.1f}–{e.E.max():.1f} keV  |  "
            f"ch: {e.ch.min():.0f}–{e.ch.max():.0f}", self.GREEN)
        self.btn_cal.config(state="normal")
        self.btn_calc.config(state="disabled")
        self.btn_clr.config(state="disabled")
        self.btn_eff_query.config(state="disabled")
        self.btn_eff_clr.config(state="disabled")
        self._pct_btn.config(state="disabled")
        # Reset toggle state when a new file is loaded
        self._eff_pct_mode = False
        self._pct_btn.config(text="a.u. → %")
        self._reset_results()
        self._init_axes()

    def _on_calibrate(self):
        if not self.engine.data_loaded:
            messagebox.showwarning("No data", "Load a data file first."); return
        for b in (self.btn_cal, self.btn_calc,
                  self.btn_clr, self.btn_eff_query, self.btn_eff_clr,
                  self._pct_btn):
            b.config(state="disabled")
        self._clear_all_silent()
        self.prog_var.set(0)
        self.prog_bar.pack(fill="x", padx=14, pady=(0, 4))

        # self.update() rather than update_idletasks(): the latter runs only
        # redraw and geometry tasks and never drains the OS message queue, so
        # Windows flags the window "Not Responding" during the ~1 min run and
        # it cannot be moved or resized.  update() dispatches input events too,
        # which is safe here because every button is disabled and the _busy
        # flag makes the window-close button a no-op until the run finishes.
        self._busy = True
        try:
            self.update()

            def en_cb(pct, msg):
                self._on_progress(int(pct*0.48), f"[Energy] {msg}")
                self.update()
            try:
                self.engine.calibrate(progress_cb=en_cb)
            except Exception as exc:
                self._on_cal_error(str(exc)); return

            self._on_progress(50, "Starting efficiency calibration …")
            self.update()

            def eff_cb(pct, msg):
                self._on_progress(50 + int(pct*0.50), f"[Eff.] {msg}")
                self.update()
            try:
                self.engine.calibrate_efficiency(progress_cb=eff_cb)
            except Exception as exc:
                self.prog_bar.pack_forget()
                self._write_cal_to_file()
                fname = os.path.basename(self._res_file) if self._res_file else ""
                self._status(
                    f"⚠  Energy OK; efficiency failed: {exc}"
                    + (f"  |  Results → {fname}" if fname else ""),
                    self.YELLOW)
                self.btn_cal.config(state="normal")
                self.btn_calc.config(state="normal")
                self._draw_calibration(); return

            self._on_both_done()
        finally:
            self._busy = False

    def _on_progress(self, pct, msg):
        self.prog_var.set(pct); self._status(f"⏳  {msg}", self.YELLOW)

    def _on_cal_error(self, msg):
        self.prog_bar.pack_forget(); self._status(f"❌  {msg}", self.RED)
        self.btn_cal.config(state="normal")

    def _on_both_done(self):
        e = self.engine
        self.prog_bar.pack_forget()
        self.btn_cal.config(state="normal")
        self.btn_calc.config(state="normal")
        self.btn_eff_query.config(state="normal")
        self._pct_btn.config(state="normal")
        self._write_cal_to_file()
        fname = os.path.basename(self._res_file) if self._res_file else ""

        # Report MC health rather than a bare "ready": a run in which most
        # refits failed still yields a best-fit curve and a plausible-looking
        # plot, so silence here would present a weak result as a strong one.
        warn = (e.mc_krf_ok < N_MC_EFF // 2) or (e.mc_bad > N_MC_EFF // 10)
        self._status(
            ("⚠" if warn else "✔")
            + f"  Calibration ready  |  MC ok: KRF {e.mc_krf_ok:,}"
            + f", Radware {e.mc_rw_ok:,}  of {N_MC_EFF:,}"
            + (f", {e.mc_bad:,} non-physical" if e.mc_bad else "")
            + (f"  |  Results → {fname}" if fname else ""),
            self.YELLOW if warn else self.GREEN)
        self._draw_calibration(); self._draw_efficiency()

    # ── Result file I/O ───────────────────────────────────────────────
    def _write_cal_to_file(self):
        """Write all calibration parameters, efficiency data, and fit tables
        to {datafile_basename}_Res.txt.  Overwrites on each calibration run."""
        e   = self.engine
        base = os.path.splitext(os.path.basename(e.filepath))[0]
        self._res_file = os.path.join(_results_dir_for(e.filepath),
                                      f"{base}_Res.txt")
        now  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sep  = "=" * 80
        dash = "─" * 80

        a1, b1     = e.popt1
        a2, b2, c2 = e.popt2
        sa1 = np.sqrt(e.pcov1[0, 0]); sb1 = np.sqrt(e.pcov1[1, 1])
        sa2 = np.sqrt(e.pcov2[0, 0]); sb2 = np.sqrt(e.pcov2[1, 1])
        sc2 = np.sqrt(e.pcov2[2, 2])

        out = []
        out += [sep,
                "Energy & Efficiency Calibration  —  Results",
                f"Data file : {os.path.basename(e.filepath)}",
                f"Generated : {now}",
                sep, ""]

        # ── Energy calibration parameters ─────────────────────────────
        out += [dash, "ENERGY CALIBRATION PARAMETERS", dash, ""]
        out += ["Linear fit   ch(E) = a + b·E",
                f"  a = {a1:+.6f}  ±{sa1:.3e} (stat)  ±{sa1*e.birge1:.6f} (Birge)",
                f"  b = {b1:.9f}  ±{sb1:.3e} (stat)  ±{sb1*e.birge1:.3e} (Birge)",
                f"  χ²/ndf = {e.chi2_1:.4e} / {e.ndf1}   "
                f"Birge = {e.birge1:.4f}   RMS = {e.rms1:.6f} ch",
                ""]
        out += ["Quadratic fit   ch(E) = a + b·E + c·E²",
                f"  a = {a2:+.6f}  ±{sa2:.3e} (stat)  ±{sa2*e.birge2:.6f} (Birge)",
                f"  b = {b2:.9f}  ±{sb2:.3e} (stat)  ±{sb2*e.birge2:.3e} (Birge)",
                f"  c = {c2:.6e}  ±{sc2:.3e} (stat)  ±{sc2*e.birge2:.3e} (Birge)",
                f"  χ²/ndf = {e.chi2_2:.4e} / {e.ndf2}   "
                f"Birge = {e.birge2:.4f}   RMS = {e.rms2:.6f} ch",
                "",
                f"Birge ratio reference: {_BIRGE_URL}", ""]

        # ── Efficiency calibration parameters ─────────────────────────
        if e.eff_ready:
            a, b, c, d = e.eff_popt
            out += [dash, "EFFICIENCY CALIBRATION PARAMETERS — KRF", dash, ""]
            out += ["KRF:  ε(E) = (a·E + b/E) · exp(c·E + d/E)",
                    f"  a = {a:.6e}    b = {b:.6e}",
                    f"  c = {c:.6e}    d = {d:.6e}",
                    f"  χ²/ndf = {e.eff_chi2:.4e} / {e.eff_ndf}   "
                    f"Birge = {e.eff_birge:.4f}   RMS = {e.eff_rms:.6e}",
                    f"  KRF MC fits ok : {len(e.params_eff):,} / {N_MC_EFF:,}",
                    ""]
            if e.radware_popt is not None:
                # Deliberately not named a1/a2/… — those already hold the
                # linear energy-fit parameters unpacked at the top of this
                # method, and rebinding them here would silently corrupt any
                # later use of the energy values.
                ra1, ra2, ra4, ra5, ra6 = e.radware_popt   # a3=0, g=15 fixed
                out += ["Radware (5-param, Radford effit.c procedure):",
                        "  ln ε = f·(1 + r^G)^(-1/G)  with G=15 fixed",
                        "  f = min(f1,f2);  f1 = a1+a2·x  [C=0 fixed]",
                        "                   f2 = a4+a5·y+a6·y²",
                        "  x = ln(E/100),  y = ln(E/1000)",
                        f"  a1={ra1:.6e}  a2={ra2:.6e}  a3= 0.000000e+00 (fixed)",
                        f"  a4={ra4:.6e}  a5={ra5:.6e}  a6={ra6:.6e}",
                        f"  G = 1.500000e+01 (fixed)",
                        f"  χ²/ndf = {e.radware_chi2:.4e} / {e.radware_ndf}   "
                        f"Birge = {e.radware_birge:.4f}   RMS = {e.radware_rms:.6e}",
                        f"  Radware MC fits ok : "
                        f"{len(e.params_radware):,} / {N_MC_EFF:,}"
                        if e.params_radware is not None else "  Radware MC fits ok : 0",
                        ""]
            out += [f"Birge ratio reference: {_BIRGE_URL}", ""]

        # ── Efficiency data (observed) ─────────────────────────────────
        if e.eff_ready:
            out += [dash, "EFFICIENCY DATA (observed)", dash, ""]
            out.append(f"  {'E[keV]':>10}  {'ε[a.u.]':>14}  {'Δε[a.u.]':>14}")
            out.append(f"  {'─'*10}  {'─'*14}  {'─'*14}")
            for i in range(e.n):
                out.append(f"  {e.E[i]:10.3f}  {e.eff[i]:14.6e}  {e.deff[i]:14.6e}")
            out.append("")

        # ── Fit data: linear ch(E) ─────────────────────────────────────
        out += [dash, "FIT DATA  —  linear ch(E)", dash, ""]
        out.append(f"  {'E[keV]':>10}  {'ch_fit':>12}  {'Δch':>10}")
        out.append(f"  {'─'*10}  {'─'*12}  {'─'*10}")
        ch_lin = f_lin(e.E, *e.popt1)
        for i in range(e.n):
            out.append(f"  {e.E[i]:10.3f}  {ch_lin[i]:12.4f}  {e.dch[i]:10.4f}")
        out.append("")

        # ── Fit data: quadratic ch(E) ──────────────────────────────────
        out += [dash, "FIT DATA  —  quadratic ch(E)", dash, ""]
        out.append(f"  {'E[keV]':>10}  {'ch_fit':>12}  {'Δch':>10}")
        out.append(f"  {'─'*10}  {'─'*12}  {'─'*10}")
        ch_quad = f_quad(e.E, *e.popt2)
        for i in range(e.n):
            out.append(f"  {e.E[i]:10.3f}  {ch_quad[i]:12.4f}  {e.dch[i]:10.4f}")
        out.append("")

        # ── Fit data: efficiency ε(E) ──────────────────────────────────
        if e.eff_ready:
            has_rw = e.radware_popt is not None
            hdr = (f"  {'E[keV]':>10}  {'ε_KRF[a.u.]':>14}  "
                   f"{'ε_Rad[a.u.]':>14}  {'Δε[a.u.]':>14}")
            sep_row = f"  {'─'*10}  {'─'*14}  {'─'*14}  {'─'*14}"
            out += [dash, "FIT DATA  —  efficiency ε(E)", dash, "", hdr, sep_row]
            eff_fit_k = f_krf(e.E, *e.eff_popt)
            eff_fit_r = (f_radware_5p(e.E, *e.radware_popt) if has_rw
                         else [float("nan")] * e.n)
            for i in range(e.n):
                out.append(
                    f"  {e.E[i]:10.3f}  {eff_fit_k[i]:14.6e}"
                    f"  {eff_fit_r[i]:14.6e}  {e.deff[i]:14.6e}")
            out.append("")

        # ── Query results section header (entries appended later) ──────
        out += [dash, "QUERY RESULTS", dash, ""]

        try:
            with open(self._res_file, "w", encoding="utf-8") as fh:
                fh.write("\n".join(out) + "\n")
        except Exception as exc:
            self._res_file = None
            self._status(f"⚠  Could not write result file: {exc}", self.YELLOW)

    def _append_query_to_file(self, text):
        """Append a query result block to the result file (no-op if no file)."""
        if not self._res_file:
            return
        try:
            with open(self._res_file, "a", encoding="utf-8") as fh:
                fh.write(text)
        except Exception:
            pass

    # ── Energy query  (ch → E)  ───────────────────────────────────────
    def _calculate(self):
        if not self.engine.cal_ready: return
        try:
            ch_val  = float(self.ch_var.get())
            dch_val = abs(float(self.dch_var.get()))
        except ValueError:
            self._status("❌  Enter valid numbers.", self.RED); return

        self._status("⏳  Computing …", self.YELLOW)
        self.btn_calc.config(state="disabled")
        self.update_idletasks()

        try:
            res = self.engine.predict(ch_val, dch_val)
        except Exception as exc:
            self._status(f"❌  {exc}", self.RED)
            self.btn_calc.config(state="normal"); return

        El, dEl, Eq, dEq, El_bf, Eq_bf = res
        self._set("lin",  "E_mc", f"{El:.4f}")
        self._set("lin",  "dE",   f"±{dEl:.4f}")
        self._set("lin",  "E_bf", f"{El_bf:.4f}" if not np.isnan(El_bf) else "—")
        self._set("quad", "E_mc", f"{Eq:.4f}")
        self._set("quad", "dE",   f"±{dEq:.4f}")
        self._set("quad", "E_bf", f"{Eq_bf:.4f}" if not np.isnan(Eq_bf) else "—")

        self.btn_calc.config(state="normal")
        self.btn_clr.config(state="normal")
        self.btn_eff_clr.config(state="normal")
        self._draw_query(ch_val, dch_val, El, dEl, Eq, dEq)

        # Append query to result file
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        El_bf_str = f"{El_bf:.4f}" if not np.isnan(El_bf) else "—"
        Eq_bf_str = f"{Eq_bf:.4f}" if not np.isnan(Eq_bf) else "—"
        self._append_query_to_file(
            f"[{now}]  ENERGY QUERY\n"
            f"  ch₀ = {ch_val:.4f}   Δch₀ = {dch_val:.4f}\n"
            f"  Linear:    E(MC mean) = {El:.4f} ± {dEl:.4f} keV"
            f"   E(best-fit) = {El_bf_str} keV\n"
            f"  Quadratic: E(MC mean) = {Eq:.4f} ± {dEq:.4f} keV"
            f"   E(best-fit) = {Eq_bf_str} keV\n\n")

        self._status(
            f"✔  ch={ch_val:.1f}±{dch_val}  →  "
            f"E(lin)={El:.3f}±{dEl:.3f} keV   "
            f"E(quad)={Eq:.3f}±{dEq:.3f} keV",
            self.GREEN)

    def _draw_query(self, ch_val, dch_val, El, dEl, Eq, dEq):
        self._remove_arts(self._q_arts); self._q_arts.clear()
        ax = self.ax_m
        self._q_arts.append(
            ax.axhspan(ch_val-dch_val, ch_val+dch_val,
                       alpha=0.14, color=self.YELLOW, zorder=3))
        self._q_arts.append(
            ax.axhline(ch_val, color=self.YELLOW, lw=1.2, ls="--", alpha=0.7, zorder=4))
        # vertical crosshair lines on ax_m — yellow so they contrast with the curves
        self._q_arts.append(
            ax.axvline(El, color=self.YELLOW, lw=1.8, ls="--", alpha=0.85, zorder=5))
        self._q_arts.append(
            ax.axvline(Eq, color=self.YELLOW, lw=1.8, ls=":",  alpha=0.85, zorder=5))
        self._q_arts.append(
            ax.errorbar([El], [ch_val], xerr=[dEl], yerr=[dch_val],
                        fmt='D', ms=10, color=self.LIN_C, ecolor=self.LIN_C,
                        capsize=6, capthick=2, elinewidth=2, zorder=9,
                        label=f"→{El:.3f}±{dEl:.3f} keV (lin)"))
        self._q_arts.append(
            ax.errorbar([Eq], [ch_val], xerr=[dEq], yerr=[dch_val],
                        fmt='s', ms=9, color=self.QUAD_C, ecolor=self.QUAD_C,
                        capsize=6, capthick=2, elinewidth=2, zorder=9,
                        label=f"→{Eq:.3f}±{dEq:.3f} keV (quad)"))
        for axr, Eq_, col in ((self.ax_r1, El, self.LIN_C),
                              (self.ax_r2, Eq, self.QUAD_C)):
            self._q_arts.append(
                axr.axvline(Eq_, color=col, lw=1.5, ls=":", alpha=0.8))
        ax.legend(fontsize=8, facecolor=self.PANEL,
                  labelcolor=self.TEXT, edgecolor=self.BORDER, loc="upper left")
        ax.set_xlim(self._xlim); ax.set_ylim(self._ylim)
        self.canvas_en.draw()

    # ── Efficiency query  (E → ε)  ────────────────────────────────────
    def _eff_scale(self):
        """(scale factor, unit label) for the current efficiency display mode."""
        e   = self.engine
        pct = self._eff_pct_mode and (e.eff_norm is not None)
        return (e.eff_norm if pct else 1.0), ("%" if pct else "a.u.")

    def _display_eff_results(self, sc):
        """Write the cached a.u. query into the six result labels, scaled by sc.

        Shared by _query_eff() and _toggle_pct_mode() so the two paths cannot
        drift apart.  Returns the scaled tuple for the subsequent plot call,
        or None when no query is cached.
        """
        if self._last_eff_query_au is None:
            return None
        (E_val, krf_mean, krf_std, krf_bf,
         rw_mean, rw_std, rw_bf) = self._last_eff_query_au

        def s(x):
            return float(x * sc) if isinstance(x, float) and np.isfinite(x) else x

        km, ks, kb = s(krf_mean), s(krf_std), s(krf_bf)
        rm, rs, rb = s(rw_mean),  s(rw_std),  s(rw_bf)

        self._eff_val_mc.set(_ns(km))
        self._eff_derr.set(f"±{ks:.5g}" if np.isfinite(ks) else "—")
        self._eff_val_bf.set(_ns(kb))
        self._eff_rw_val_mc.set(_ns(rm))
        self._eff_rw_derr.set(f"±{rs:.5g}" if np.isfinite(rs) else "—")
        self._eff_rw_val_bf.set(_ns(rb))
        return E_val, km, ks, kb, rm, rs, rb

    def _query_eff(self):
        if not self.engine.eff_ready: return
        try:
            E_val = float(self.E_q_var.get())
        except ValueError:
            self._status("❌  Enter a valid energy value.", self.RED); return

        self._status("⏳  Computing …", self.YELLOW)
        self.btn_eff_query.config(state="disabled")
        self.update_idletasks()

        try:
            krf_mean, krf_std, krf_bf, rw_mean, rw_std, rw_bf = \
                self.engine.predict_efficiency(E_val)
        except Exception as exc:
            self._status(f"❌  {exc}", self.RED)
            self.btn_eff_query.config(state="normal"); return

        # Store raw a.u. results for toggle redraw
        self._last_eff_query_au = (E_val,
                                   krf_mean, krf_std, krf_bf,
                                   rw_mean,  rw_std,  rw_bf)

        sc, y_unit = self._eff_scale()
        _, km_d, ks_d, kb_d, rm_d, rs_d, rb_d = self._display_eff_results(sc)

        self.btn_eff_clr.config(state="normal")
        self.btn_clr.config(state="normal")
        try:
            self._draw_eff_query(E_val, km_d, ks_d, kb_d, rm_d, rs_d, rb_d,
                                 scale=sc)
        except Exception as exc:
            self._status(f"❌  Plot error: {exc}", self.RED)
            self.btn_eff_query.config(state="normal"); return
        finally:
            self.btn_eff_query.config(state="normal")

        # Append query to result file (always a.u. values in file)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._append_query_to_file(
            f"[{now}]  EFFICIENCY QUERY\n"
            f"  E₀ = {E_val:.4f} keV\n"
            f"  KRF    ε(MC mean)  = {_ns(krf_mean, '.6e')} ± {_ns(krf_std, '.6e')} a.u.\n"
            f"  KRF    ε(best-fit) = {_ns(krf_bf, '.6e')} a.u.\n"
            f"  Radware ε(MC mean)  = {_ns(rw_mean, '.6e')} ± {_ns(rw_std, '.6e')} a.u.\n"
            f"  Radware ε(best-fit) = {_ns(rw_bf, '.6e')} a.u.\n\n")

        krf_part = (f"  KRF={km_d:.4g}±{ks_d:.4g} {y_unit}"
                    if np.isfinite(krf_mean) else "  KRF=N/A")
        rw_part  = (f"  Rad={rm_d:.4g}±{rs_d:.4g} {y_unit}"
                    if np.isfinite(rw_mean) else "  Rad=N/A")
        self._status(
            f"✔  ε({E_val:.1f} keV){krf_part}{rw_part}",
            self.GREEN)

    def _draw_eff_query(self, E_val, krf_mean, krf_std, krf_bf=None,
                        rw_mean=None, rw_std=None, rw_bf=None, scale=1.0):
        """Draw query markers on ax_eff.  All value arguments are in display
        units (already scaled by `scale`).  The MC histogram is scaled here."""
        self._remove_arts(self._eff_q_arts); self._eff_q_arts.clear()
        ax = self.ax_eff
        # Vertical crosshair (E₀) — always drawn
        self._eff_q_arts.append(
            ax.axvline(E_val, color=self.YELLOW, lw=1.4, ls="--", alpha=0.8))

        # KRF: only plot when the value is finite
        krf_ok = (isinstance(krf_mean, float) and np.isfinite(krf_mean)
                  and isinstance(krf_std, float) and np.isfinite(krf_std))
        if krf_ok:
            self._eff_q_arts.append(
                ax.axhline(krf_mean, color=self.EFF_C, lw=1.2, ls="--",
                           alpha=0.75, zorder=5))
            self._eff_q_arts.append(
                ax.errorbar([E_val], [krf_mean], yerr=[krf_std],
                            fmt='D', ms=9, color=self.EFF_C, ecolor=self.YELLOW,
                            capsize=6, capthick=2, elinewidth=2, zorder=9,
                            label=f"KRF  {krf_mean:.3g}±{krf_std:.2g}"))
            if krf_bf is not None and np.isfinite(krf_bf):
                self._eff_q_arts.append(
                    ax.plot(E_val, krf_bf, marker='*', ms=12,
                            color=self.EFF_C, zorder=10,
                            label=f"KRF bf  {krf_bf:.3g}")[0])
        # Radware: horizontal line + square marker
        rw_ok = (rw_mean is not None and isinstance(rw_mean, float)
                 and np.isfinite(rw_mean))
        if rw_ok:
            self._eff_q_arts.append(
                ax.axhline(rw_mean, color=self.RAD_C, lw=1.2, ls="--",
                           alpha=0.75, zorder=5))
            self._eff_q_arts.append(
                ax.errorbar([E_val], [rw_mean], yerr=[rw_std],
                            fmt='s', ms=8, color=self.RAD_C, ecolor=self.YELLOW,
                            capsize=6, capthick=2, elinewidth=2, zorder=9,
                            label=f"Rad  {rw_mean:.3g}±{rw_std:.2g}"))
            if rw_bf is not None and np.isfinite(rw_bf):
                self._eff_q_arts.append(
                    ax.plot(E_val, rw_bf, marker='*', ms=12,
                            color=self.RAD_C, zorder=10,
                            label=f"Rad bf  {rw_bf:.3g}")[0])
        ax.legend(fontsize=8, facecolor=self.PANEL,
                  labelcolor=self.TEXT, edgecolor=self.BORDER, loc="upper right")
        if self._eff_xlim is not None:
            ax.set_xlim(self._eff_xlim); ax.set_ylim(self._eff_ylim)
        # vertical crosshair on residuals panel
        self._eff_q_arts.append(
            self.ax_eff_r.axvline(E_val, color=self.YELLOW, lw=1.4,
                                  ls=":", alpha=0.8))

        # MC histogram — overlay KRF and Radware distributions (apply scale)
        e = self.engine
        _, y_unit = self._eff_scale()
        ax_mc = self.ax_eff_mc; ax_mc.cla(); self._style_ax(ax_mc)
        ax_mc.set_xlabel(f"ε  ({y_unit})", color=self.TEXT, fontsize=8)
        ax_mc.set_ylabel("MC count",        color=self.TEXT, fontsize=8)
        ax_mc.set_title(f"MC dist.  E₀={E_val:.1f} keV",
                        color=self.TEXT, fontsize=9, pad=3)

        def _mc_bins(samples, n=60):
            """Return bin edges robust to degenerate or non-finite samples."""
            s = samples[np.isfinite(samples)]
            if len(s) < 2:
                return 10
            lo, hi = np.percentile(s, [0.5, 99.5])
            if lo >= hi:
                lo, hi = s.min(), s.max()
            if lo >= hi:
                return 10
            return np.linspace(lo, hi, n + 1)

        any_hist = False
        if len(e.params_eff):
            with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
                p = e.params_eff
                krf_mc = f_krf(float(E_val), p[:, 0], p[:, 1],
                               p[:, 2], p[:, 3]) * scale
            krf_mc_ok = krf_mc[np.isfinite(krf_mc)]
        else:
            krf_mc_ok = np.empty(0)
        if krf_ok and len(krf_mc_ok) > 1:
            ax_mc.hist(krf_mc_ok, bins=_mc_bins(krf_mc_ok),
                       color=self.EFF_C, alpha=0.60,
                       edgecolor=self.PANEL, linewidth=0.4, label="KRF")
            ax_mc.axvline(krf_mean, color=self.EFF_C, lw=2, zorder=5)
            ax_mc.axvspan(krf_mean - krf_std, krf_mean + krf_std,
                          alpha=0.18, color=self.EFF_C, zorder=4)
            if krf_bf is not None and np.isfinite(krf_bf):
                ax_mc.axvline(krf_bf, color=self.EFF_C, lw=1.6, ls="--", zorder=6)
            any_hist = True
        if rw_ok and e.params_radware is not None and len(e.params_radware) > 0:
            p = e.params_radware
            with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
                rw_mc = (f_radware_5p(float(E_val), p[:,0], p[:,1], p[:,2],
                                      p[:,3], p[:,4]) * scale)
            rw_mc_ok = rw_mc[np.isfinite(rw_mc)]
            if len(rw_mc_ok) > 1:
                ax_mc.hist(rw_mc_ok, bins=_mc_bins(rw_mc_ok),
                           color=self.RAD_C, alpha=0.55,
                           edgecolor=self.PANEL, linewidth=0.4, label="Radware")
                ax_mc.axvline(rw_mean, color=self.RAD_C, lw=2, zorder=5)
                ax_mc.axvspan(rw_mean - rw_std, rw_mean + rw_std,
                              alpha=0.18, color=self.RAD_C, zorder=4)
                if rw_bf is not None and np.isfinite(rw_bf):
                    ax_mc.axvline(rw_bf, color=self.RAD_C, lw=1.6, ls="--", zorder=6)
                any_hist = True
        if any_hist:
            ax_mc.legend(fontsize=8, facecolor=self.PANEL,
                         labelcolor=self.TEXT, edgecolor=self.BORDER,
                         loc="upper right")
        else:
            ax_mc.text(0.5, 0.5,
                       f"No finite MC samples at E₀={E_val:.1f} keV\n"
                       "(extrapolation outside fitted range)",
                       transform=ax_mc.transAxes, ha="center", va="center",
                       color=self.MUTED, fontsize=9, style="italic")
        self.canvas_eff.draw()

    # ── a.u. / % toggle ──────────────────────────────────────────────
    def _toggle_pct_mode(self):
        """Switch the efficiency display between a.u. and % and redraw."""
        if not self.engine.eff_ready:
            return
        self._eff_pct_mode = not self._eff_pct_mode
        label = "% → a.u." if self._eff_pct_mode else "a.u. → %"
        self._pct_btn.config(text=label)

        # Redraw the main efficiency plot
        try:
            self._draw_efficiency()
        except Exception as exc:
            # Surface any plot error in the status bar instead of letting
            # Tkinter swallow it silently.
            self._status(f"❌  Efficiency redraw failed: {exc}", self.RED)
            return

        # If a query is cached, redraw it with the new scale
        sc, y_unit = self._eff_scale()
        scaled = self._display_eff_results(sc)
        if scaled is not None:
            E_val, km, ks, kb, rm, rs, rb = scaled
            try:
                self._draw_eff_query(E_val, km, ks, kb, rm, rs, rb, scale=sc)
            except Exception as exc:
                self._status(f"⚠  Eff. plot redraw failed: {exc}", self.YELLOW)

        self._status(f"✔  Efficiency display: {y_unit}", self.GREEN)

    # ── Clear (unified — either button clears both panels) ─────────────
    def _clear_all(self):
        self._remove_arts(self._q_arts);     self._q_arts.clear()
        self._remove_arts(self._eff_q_arts); self._eff_q_arts.clear()
        self._reset_results()
        self.btn_clr.config(state="disabled")
        if hasattr(self, "btn_eff_clr"): self.btn_eff_clr.config(state="disabled")

        if self._xlim is not None and self.engine.cal_ready:
            self.ax_m.set_xlim(self._xlim); self.ax_m.set_ylim(self._ylim)
            self._rebuild_en_legend()

        if self._eff_xlim is not None and self.engine.eff_ready:
            self.ax_eff.set_xlim(self._eff_xlim); self.ax_eff.set_ylim(self._eff_ylim)
            self._rebuild_eff_legend()
            self._reset_eff_mc_placeholder()

        self.canvas_en.draw(); self.canvas_eff.draw()
        if self.engine.cal_ready or self.engine.eff_ready:
            self._status("Query cleared.", self.MUTED)

    def _clear_all_silent(self):
        """Remove arts and reset results without canvas.draw() (pre-calibration)."""
        self._remove_arts(self._q_arts);     self._q_arts.clear()
        self._remove_arts(self._eff_q_arts); self._eff_q_arts.clear()
        self._reset_results()

    def _rebuild_en_legend(self):
        handles, labels = self.ax_m.get_legend_handles_labels()
        self.ax_m.legend(
            [h for h, l in zip(handles, labels) if not l.startswith("→")],
            [l for l in labels if not l.startswith("→")],
            fontsize=8, facecolor=self.PANEL,
            labelcolor=self.TEXT, edgecolor=self.BORDER, loc="upper left")

    def _rebuild_eff_legend(self):
        handles, labels = self.ax_eff.get_legend_handles_labels()
        self.ax_eff.legend(
            [h for h, l in zip(handles, labels) if not l.startswith("ε(")],
            [l for l in labels if not l.startswith("ε(")],
            fontsize=8, facecolor=self.PANEL,
            labelcolor=self.TEXT, edgecolor=self.BORDER, loc="upper right")

    @staticmethod
    def _remove_arts(arts):
        from matplotlib.container import ErrorbarContainer
        for art in arts:
            if isinstance(art, ErrorbarContainer):
                # Remove the container from the axes' container list so that
                # ax.legend() no longer picks it up (the container survives
                # individual artist .remove() calls otherwise).
                try:
                    ax = art[0].axes
                    if ax is not None and art in ax.containers:
                        ax.containers.remove(art)
                except Exception: pass
                try: art[0].remove()
                except Exception: pass
                for c in art[1]:
                    try: c.remove()
                    except Exception: pass
                for b in art[2]:
                    try: b.remove()
                    except Exception: pass
            else:
                try: art.remove()
                except Exception: pass

    # ── Figure right-click → save ─────────────────────────────────────
    # Clicking inside a specific subplot saves that panel only.
    # Clicking on the figure margin (inaxes is None) saves the full figure.
    # Use explicit `is` comparisons — avoids any dict-hashing edge cases with
    # matplotlib Axes objects.
    def _on_fig_en_rightclick(self, event):
        if event.button != 3 or not self.engine.data_loaded: return
        ax = event.inaxes
        if ax is self.ax_m:
            label, axes = "energy_calibration",   [self.ax_m]
        elif ax is self.ax_r1:
            label, axes = "energy_rms_linear",    [self.ax_r1]
        elif ax is self.ax_r2:
            label, axes = "energy_rms_quadratic", [self.ax_r2]
        elif ax is None:
            label, axes = "energy_calibration_full", [self.ax_m, self.ax_r1, self.ax_r2]
        else:
            return
        path = filedialog.asksaveasfilename(
            title="Save as …", defaultextension=".png",
            filetypes=SAVE_FILETYPES,
            initialfile=f"{label}.png", initialdir=_base_dir())
        if not path: return
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        self._save_panel(self.fig_en, self.canvas_en, axes, label,
                         ext if ext in SAVE_EXTS else "png",
                         saved_path=path)

    def _on_fig_eff_rightclick(self, event):
        if event.button != 3 or not self.engine.data_loaded: return
        ax = event.inaxes
        if ax is self.ax_eff:
            label, axes = "efficiency_calibration", [self.ax_eff]
        elif ax is self.ax_eff_r:
            label, axes = "efficiency_rms",         [self.ax_eff_r]
        elif ax is self.ax_eff_mc:
            label, axes = "efficiency_MC_dist",     [self.ax_eff_mc]
        elif ax is None:
            label, axes = "efficiency_full", [self.ax_eff, self.ax_eff_r, self.ax_eff_mc]
        else:
            return
        path = filedialog.asksaveasfilename(
            title="Save as …", defaultextension=".png",
            filetypes=SAVE_FILETYPES,
            initialfile=f"{label}.png", initialdir=_base_dir())
        if not path: return
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        self._save_panel(self.fig_eff, self.canvas_eff, axes, label,
                         ext if ext in SAVE_EXTS else "png",
                         saved_path=path)

    def _save_panel(self, fig, canvas, axes_list, label, fmt, saved_path=None):
        if saved_path is None:
            saved_path = filedialog.asksaveasfilename(
                title="Save as …",
                defaultextension=f".{fmt}",
                filetypes=SAVE_FILETYPES,
                initialfile=f"{label}.{fmt}",
                initialdir=_base_dir())
            if not saved_path: return
            # User may have changed the extension in the dialog
            ext = os.path.splitext(saved_path)[1].lower().lstrip(".")
            if ext in SAVE_EXTS:
                fmt = ext

        # Matplotlib's savefig() takes 'jpeg' / 'tiff' as the canonical name;
        # 'jpg' / 'tif' work as aliases on modern versions but normalise here
        # to avoid backend complaints on older installs.
        savefig_fmt = {"jpg": "jpeg", "tif": "tiff"}.get(fmt, fmt)

        try:
            canvas.draw()
            renderer = fig.canvas.get_renderer()
            bboxes = []
            for a in axes_list:
                bb = a.get_tightbbox(renderer)
                if bb is None:
                    bb = a.get_window_extent(renderer)   # fallback: bare axes box
                if bb is not None:
                    bboxes.append(bb)
            fc = fig.get_facecolor()
            pad = 16   # px padding around cropped region

            save_kwargs = dict(format=savefig_fmt, dpi=150, facecolor=fc)
            # JPEG has no alpha channel; matplotlib will flatten transparency
            # against `facecolor`, so the dark theme background is preserved.

            if bboxes:
                from matplotlib.transforms import Bbox
                x0 = min(b.x0 for b in bboxes) - pad
                y0 = min(b.y0 for b in bboxes) - pad
                x1 = max(b.x1 for b in bboxes) + pad
                y1 = max(b.y1 for b in bboxes) + pad
                bi = Bbox([[x0, y0], [x1, y1]]).transformed(
                    fig.dpi_scale_trans.inverted())
                fig.savefig(saved_path, bbox_inches=bi, **save_kwargs)
            else:
                fig.savefig(saved_path, bbox_inches="tight", **save_kwargs)
            self._status(f"✔  Saved → {os.path.basename(saved_path)}", self.GREEN)
        except Exception as exc:
            self._status(f"❌  Save failed: {exc}", self.RED)

    # ── Theme ─────────────────────────────────────────────────────────
    def _tk_color(self, widget, color_str):
        try:
            r, g, b = widget.winfo_rgb(color_str)
            return "#{:02x}{:02x}{:02x}".format(r>>8, g>>8, b>>8)
        except Exception:
            s = str(color_str).strip().lower()
            return s if s.startswith("#") and len(s)==7 else s

    def _retheme_widget(self, widget, cmap):
        for attr in ("background","foreground","insertbackground",
                     "activebackground","activeforeground",
                     "highlightbackground","selectbackground","selectforeground"):
            try:
                raw = str(widget.cget(attr))
                norm = self._tk_color(widget, raw)
                if norm in cmap: widget.configure(**{attr: cmap[norm]})
            except Exception: pass
        for child in widget.winfo_children():
            self._retheme_widget(child, cmap)

    def _toggle_theme(self):
        self._apply_theme("light" if self._theme_name=="dark" else "dark")

    def _apply_theme(self, name):
        old_t = _DARK if self._theme_name=="dark" else _LIGHT
        new_t = _DARK if name=="dark" else _LIGHT
        cmap = {}
        for k in old_t:
            norm = self._tk_color(self, old_t[k])
            if norm not in cmap: cmap[norm] = new_t[k]
        self._theme_name = name
        for k, v in new_t.items(): setattr(self, k, v)
        self._theme_btn.config(
            text="☀  Light" if name=="dark" else "\U0001f319  Dark")
        self._retheme_widget(self, cmap)
        self._apply_ttk_style(name)
        self.fig_en.set_facecolor(self.DARK)
        self.fig_eff.set_facecolor(self.DARK)
        self._init_axes()
        if self.engine.cal_ready:  self._draw_calibration()
        if self.engine.eff_ready:  self._draw_efficiency()

    # ── Status bar ────────────────────────────────────────────────────
    def _status(self, msg, color):
        self.status_lbl.config(text=msg, fg=color)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Pre-warm libraries that do expensive one-time initialisation on first use:
    #   • numpy/MKL — builds the Intel thread pool on the first BLAS call;
    #     if this fires inside curve_fit while update_idletasks() is pumping
    #     the Tk event queue it can crash the frozen exe on first run.
    #   • matplotlib font manager — scans system fonts and writes fontlist-*.json
    #     to disk; same re-entrant Tk hazard when triggered inside canvas.draw().
    # Doing both here, before any Tkinter object is created, is safe and means
    # the second and all subsequent runs are instant (cache already on disk).
    import numpy as _np
    _np.dot([1.0], [1.0])                  # MKL thread-pool init
    del _np
    import matplotlib.font_manager as _fm
    _fm.fontManager                         # font-cache build / load
    del _fm

    app = App()
    app.mainloop()
