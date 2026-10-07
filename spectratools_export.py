"""Write CalEnEff's calibrations in the formats SpectraTools 6.1.1 reads.

The format is not guesswork: it was taken from SpectraTools' own reader and
writer, and the output is verified by round-tripping through them.

    energy coefficients   read by  calibration.read_coefficients_file()
                          bare numbers, one coefficient per line, nothing else
    <stem>_bins.txt       read by  efficiency_io.read_saved_efficiency()
                          '# SpectraTools relative efficiency' on line 1, a
                          '# columns:' line naming five columns with no dE,
                          then one row per channel
    <stem>_peaks.txt      the same curve at the calibration lines only. Its
                          reader resolves a _peaks file to the _bins file
                          beside it and refuses it otherwise, so both are
                          always written together.

Nothing here touches Tk. These functions take a CalibrationEngine and are
importable and testable without a display; ra226_gui's App only adds the
dialogs and the status line.

PACKAGING: this module must be listed explicitly in packaging/linux/build_deb.sh
and packaging/linux/caleneff.spec. Both install a fixed file list, so a new
module is silently omitted from the DEB and the RPM while PyInstaller picks it
up automatically on Windows -- the app would then work from source and on
Windows and fail with ModuleNotFoundError on Ubuntu and AlmaLinux.
"""

import os

import numpy as np

#: Knots used when evaluating a curve for export; see relative_efficiency_curves.
EXPORT_KNOTS = 2048

try:
    from build_info import VERSION as _VERSION_STR
except Exception:
    _VERSION_STR = "unreleased"


def energy_cal_channel_to_energy(engine):
    """`engine`'s calibration as SpectraTools wants it: E(ch) = a + b·ch.

    CalEnEff fits the opposite direction, ch(E) = a + b·E, so the linear fit is
    inverted exactly: a' = -a/b, b' = 1/b.

    Only the linear fit is exported. A quadratic ch(E) has no exact
    three-coefficient inverse, and writing an approximate one into a file that a
    reader will treat as exact would be worse than not writing it.
    """
    a, b = (float(v) for v in engine.popt1)
    if not b:
        raise ValueError("energy calibration slope is zero; cannot invert")
    return -a / b, 1.0 / b


def engine_f_krf(engine, E):
    """The KRF best fit at E (used when there are no MC samples)."""
    from caleneff_engine import f_krf
    return f_krf(np.asarray(E, dtype=float), *engine.eff_popt)


def relative_efficiency_curves(engine, energies):
    """(eff_krf, deff_krf, eff_rw, deff_rw) at `energies`, normalised.

    Evaluated on at most EXPORT_KNOTS knots and interpolated, because
    engine.predict_efficiency() re-evaluates the whole Monte Carlo sample at
    every energy: doing that once per channel takes minutes on a 16k spectrum.
    SpectraTools writes its own files the same way and for the same reason.

    Normalised so the applied (KRF) curve peaks at 1 WITHIN THE FITTED RANGE,
    which is what "relative efficiency" means in that format -- by
    engine.eff_peak, the very number the app's % mode uses, so the two agree.
    Outside the fitted range the curve is extrapolated and may exceed 1.

    The eff columns are each model's BEST FIT, and the deff columns its
    symmetric 1σ: half the MC 15.87–84.13 % quantile range times its own Birge
    ratio, inflate-only -- the same rule as the app's band and queries
    (predict_efficiency applies it), and SpectraTools writes scaled deff too.
    (Up to v4.8 the eff columns were the MC mean, which on the v4.8 example
    data sat 7 MC-σ off the Radware best fit.)
    """
    E = np.asarray(energies, dtype=float)
    if E.size <= EXPORT_KNOTS:
        knots = E
    else:
        knots = np.linspace(E.min(), E.max(), EXPORT_KNOTS)
    # All knots in one vectorised pass per model (in chunks inside
    # engine.intervals) -- the same rule as predict_efficiency, without one
    # Python call per knot.  A model without MC samples still exports its
    # best fit, with NaN uncertainty.
    nan = np.full(len(knots), np.nan)
    kiv = engine.intervals("krf", knots)
    riv = engine.intervals("rw", knots)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        k_val = (kiv["value"] if kiv is not None
                 else engine_f_krf(engine, knots))
        r_val = (riv["value"] if riv is not None
                 else (engine.rw_curve(knots)
                       if engine.radware_popt is not None else nan))
    picked = np.column_stack([
        k_val, kiv["sigma"] if kiv is not None else nan,
        r_val, riv["sigma"] if riv is not None else nan]).astype(float)
    # NOT the maximum over the export's own energies: those run from about
    # 0 keV to the top channel, so that maximum was an extrapolated hump below
    # the data (137 keV on the shipped set) and disagreed with the app by 2.1%.
    peak = getattr(engine, "eff_peak", None)
    if peak is None or not np.isfinite(peak) or peak <= 0:
        raise ValueError("the KRF curve has no positive peak in the fitted "
                         "range to normalise to")
    picked = picked / peak
    if knots is E:
        out = picked
    else:
        out = np.column_stack([np.interp(E, knots, picked[:, j])
                               for j in range(4)])
    return out, 1.0 / peak


def _fmt(v):
    """'%.3f' for a finite number, 'n/a' otherwise."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "n/a"
    return "%.3f" % v if np.isfinite(v) else "n/a"


def header(engine, source_name, norm, e_lo, e_hi, npeaks,
           a_cal, b_cal, columns, extra_notes=()):
    """The '#' header block both efficiency files carry.

    The first line must contain SpectraTools' FILE_MARKER or its reader rejects
    the file outright, and the 'columns:' line must name exactly as many columns
    as the table has.
    """
    e = engine
    rw = e.params_radware
    lines = [
        "SpectraTools relative efficiency",
        "",
        "applied model      : KRF",
        "normalisation      : %.6g   (1 / peak of the applied curve within "
        "the fitted range, at %.1f keV)" % (norm, e.eff_peak_E),
        "fitted energy range: %.4f .. %.4f keV" % (e_lo, e_hi),
        "peaks              : %d" % npeaks,
        "KRF  params        : %s" % ", ".join("%.12g" % v for v in e.eff_popt),
        "KRF  chi2/ndf      : %.6f / %d   Birge %.4f   RMS %.6g"
        % (e.eff_chi2, e.eff_ndf, e.eff_birge, e.eff_rms),
        # SpectraTools' own wording, so a file read on its own says which
        # factor the deff columns carry -- including when it is 1 because
        # the ratio was below 1.
        "band scaling       : x%.4f   (Birge %.4f, inflate-only: a ratio "
        "below 1 never narrows the band)"
        % (max(1.0, e.eff_birge), e.eff_birge),
    ]
    if rw is None or not len(rw):
        lines.append("Radware            : did not converge")
    else:
        # The best fit -- the curve the eff_rw column holds.  This used to be
        # the mean of the MC parameter sets, which is not a fit to anything.
        lines.append("Radware params     : %s   (fitted to k*eps, k = %.12g)"
                     % (", ".join("%.12g" % v for v in e.radware_popt),
                        e.radware_scale))
    lines += [
        "Monte Carlo        : KRF %d accepted, Radware %d accepted, "
        "%d samples rejected" % (e.mc_krf_ok, e.mc_rw_ok, e.mc_bad),
        "MC bias check      : KRF max|z| %s, Radware max|z| %s   (z = (MC "
        "median - best fit) / MC sigma at the calibration lines; > 1 means "
        "deff is unreliable)" % (_fmt(getattr(e, "krf_bias_z", None)),
                                 _fmt(getattr(e, "rw_bias_z", None))),
        "energy calibration : Calibration(kind='linear', a=%r, b=%r, c=0.0)"
        % (a_cal, b_cal),
        "source             : %s" % source_name,
        "written by         : CalEnEff %s" % _VERSION_STR,
    ]
    lines += list(extra_notes)
    lines += ["", "columns: %s" % columns]
    return "".join("# %s\n" % l if l else "#\n" for l in lines)


def write_files(engine, stem, channels, a_cal, b_cal):
    """Write the three export files. Returns the paths written."""
    e = engine
    source = os.path.basename(e.filepath)
    written = []

    # 1. energy coefficients: bare numbers, one per line
    cal_path = stem + "_EnergyCal.txt"
    with open(cal_path, "w", encoding="utf-8") as fh:
        fh.write("%.12g\n%.12g\n" % (a_cal, b_cal))
    written.append(cal_path)

    # 2. per-channel curve
    ch = np.arange(int(channels), dtype=float)
    E_ch = a_cal + b_cal * ch
    bins, norm = relative_efficiency_curves(e, E_ch)
    inside = (E_ch >= float(e.E.min())) & (E_ch <= float(e.E.max()))
    ch_in = np.flatnonzero(inside)
    extrap_note = (
        "extrapolated rows  : channels outside %d..%d (E outside the fitted "
        "range) are model extrapolation, not calibration" % (ch_in[0], ch_in[-1])
        if len(ch_in) else
        "extrapolated rows  : ALL - no channel falls inside the fitted range")
    bins_path = stem + "_bins.txt"
    with open(bins_path, "w", encoding="utf-8") as fh:
        fh.write(header(
            e, source, norm, float(e.E.min()), float(e.E.max()), int(e.n),
            a_cal, b_cal, "E  eff_krf  deff_krf  eff_rw  deff_rw",
            extra_notes=[
                "",
                "one row per channel, evaluated through the energy "
                "calibration above",
                "curves interpolated from at most %d knots" % EXPORT_KNOTS,
                extrap_note,
            ]))
        for E_i, row in zip(E_ch, bins):
            fh.write("%14.6f %15.8g %15.8g %15.8g %15.8g\n"
                     % (E_i, row[0], row[1], row[2], row[3]))
    written.append(bins_path)

    # 3. the same curve at the calibration lines
    peaks, _ = relative_efficiency_curves(e, np.asarray(e.E, dtype=float))
    peaks_path = stem + "_peaks.txt"
    dE = getattr(e, "dE", None)
    with open(peaks_path, "w", encoding="utf-8") as fh:
        fh.write(header(
            e, source, norm, float(e.E.min()), float(e.E.max()), int(e.n),
            a_cal, b_cal, "E  dE  eff_krf  deff_krf  eff_rw  deff_rw"))
        for i, (E_i, row) in enumerate(zip(np.asarray(e.E, dtype=float),
                                           peaks)):
            d = float(dE[i]) if dE is not None else 0.0
            fh.write("%14.6f %12.6f %15.8g %15.8g %15.8g %15.8g\n"
                     % (E_i, d, row[0], row[1], row[2], row[3]))
    written.append(peaks_path)
    return written
