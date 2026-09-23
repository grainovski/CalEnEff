"""GUI test suite -- drives the real Tk widgets end to end.

24 checks: load (including rejection of a malformed file), a full calibration
through the button handler, energy and efficiency queries, the a.u./% toggle,
the theme switch, extrapolated queries that must not crash the plot, clear,
and the contents of the generated results file.

    python verify/verify_gui.py       # expect 24 PASS, "ALL GUI CHECKS PASSED"

Needs a display: it really does construct the App (withdrawn, so nothing
appears on screen).  Takes ~90 s -- it runs two real calibrations.

WARNING: this OVERWRITES 226Ra_En_Area_Res.txt, destroying any query log in
it, because every calibration rewrites that file from scratch.
"""
import sys, os, time
from pathlib import Path

# See verify_v4.py: the repo root is derived from this script's own location
# rather than hardcoded, so the scripts run unedited on any machine.
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import numpy as np
import ra226_gui as G

# _do_load() raises a modal error dialog on a malformed file.  That is what a
# real user should see, but this suite runs unattended against a withdrawn
# root, so the dialog is an orphan window that nothing ever dismisses and the
# run used to block here forever.  Capture the call instead; the bad-file
# check below asserts it happened, so suppressing it costs no coverage.
_dialogs = []
G.messagebox.showerror = lambda title, msg, **kw: _dialogs.append((title, msg))

DATA = str(REPO / "226Ra_En_Area.txt")
fails = []
def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {extra}", flush=True)
    if not cond: fails.append(name)

app = G.App()
app.withdraw()                      # keep it off-screen but fully functional
check("App constructed", app is not None)
check("_busy initialised False", app._busy is False)

# ── load ────────────────────────────────────────────────────────────────
app._do_load(DATA)
check("data loaded via UI", app.engine.data_loaded, f"n={app.engine.n}")
check("calibrate button enabled", str(app.btn_cal["state"]) == "normal")

# ── bad file is rejected without crashing the UI ────────────────────────
bad = np.loadtxt(DATA).copy(); bad[2, 1] = 0.0
bp = os.path.join(os.environ["TEMP"], "_v4gui_bad.txt")
np.savetxt(bp, bad)
app._do_load(bp)                    # raises a modal dialog - captured above
# Assert the user is warned AND the load was refused.  Folded into the existing
# check so the 24-check baseline is unchanged.
check("bad file rejected, app alive",
      not app.engine.data_loaded and len(_dialogs) == 1,
      f"{app.status_lbl['text'][:52]} | dialog={_dialogs[-1][0] if _dialogs else None}")
os.remove(bp)
app._do_load(DATA)                  # reload the good one

# ── full calibration through the button handler ─────────────────────────
t0 = time.time(); app._on_calibrate(); t_cal = time.time() - t0
check("calibration completed", app.engine.eff_ready, f"{t_cal:.1f}s")
check("_busy reset after run", app._busy is False)
check("status reports MC health", "MC ok" in app.status_lbl["text"],
      app.status_lbl["text"][:90])

# ── energy query ────────────────────────────────────────────────────────
app.ch_var.set("2000"); app.dch_var.set("0.5")
app._calculate()
e_first = app._lin_E_mc.get()
check("energy query filled", e_first != "—", f"E_lin={e_first}")
app._calculate()
check("energy query reproducible in UI", app._lin_E_mc.get() == e_first,
      f"{e_first} == {app._lin_E_mc.get()}")

# ── efficiency query ────────────────────────────────────────────────────
app.E_q_var.set("1000")
app._query_eff()
au_kfr = app._eff_val_mc.get()
check("efficiency query filled", au_kfr != "—", f"KFR={au_kfr} a.u.")

# ── a.u. <-> % toggle (the refactored shared path) ──────────────────────
t0 = time.time(); app._toggle_pct_mode(); t_tog = time.time() - t0
pct_kfr = app._eff_val_mc.get()
check("toggle to % changed value", pct_kfr != au_kfr, f"{au_kfr} -> {pct_kfr} %")
check("toggle button label flipped", "→ a.u." in app._pct_btn["text"],
      app._pct_btn["text"])
t0 = time.time(); app._toggle_pct_mode(); t_tog2 = time.time() - t0
check("toggle back restores a.u.", app._eff_val_mc.get() == au_kfr,
      f"{app._eff_val_mc.get()} == {au_kfr}")
print(f"\n  a.u./% toggle: {t_tog*1000:.0f} ms  and  {t_tog2*1000:.0f} ms "
      f"(full efficiency redraw each time)\n", flush=True)

# ── theme switch (retheme + both redraws) ───────────────────────────────
t0 = time.time(); app._toggle_theme(); t_th = time.time() - t0
check("theme switched to light", app._theme_name == "light", f"{t_th*1000:.0f} ms")
app._toggle_theme()
check("theme switched back to dark", app._theme_name == "dark")

# ── extrapolated query must not crash the plot ──────────────────────────
for Ev in ("1", "50000"):
    app.E_q_var.set(Ev)
    try:
        app._query_eff(); ok = True; msg = app.status_lbl["text"][:60]
    except Exception as ex:
        ok = False; msg = repr(ex)
    check(f"query E={Ev} keV no crash", ok, msg)

# ── clear ───────────────────────────────────────────────────────────────
app._clear_all()
check("clear resets energy labels", app._lin_E_mc.get() == "—")
check("clear resets efficiency labels", app._eff_val_mc.get() == "—")

# ── results file was written ────────────────────────────────────────────
check("results file written", app._res_file and os.path.isfile(app._res_file),
      os.path.basename(app._res_file or ""))
if app._res_file and os.path.isfile(app._res_file):
    txt = open(app._res_file, encoding="utf-8").read()
    check("results file has energy params", "ENERGY CALIBRATION PARAMETERS" in txt)
    check("results file has Radware block", "Radware (5-param" in txt)
    check("results file logged queries", txt.count("ENERGY QUERY") >= 1,
          f"{txt.count('ENERGY QUERY')} energy, {txt.count('EFFICIENCY QUERY')} eff")

app.destroy()
print("\n" + ("ALL GUI CHECKS PASSED" if not fails else f"FAILURES: {fails}"))
sys.exit(1 if fails else 0)
