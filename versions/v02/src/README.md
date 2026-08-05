# Ra-226 Energy & Efficiency Calibration GUI

Interactive Tk/matplotlib tool that turns raw channel/peak data into

* **Energy calibration** — channel ↔ energy with linear *and* quadratic
  models (weighted least squares + 10 000-sample Monte-Carlo error
  propagation, Birge-scaled).
* **Relative efficiency ε(E)** — fitted simultaneously with two
  independent models:
  * **KFR** — 4-parameter `ε(E) = (a·E + b/E) · exp(c·E + d/E)`
  * **Radware (5-parameter)** — following Radford's `effit.c`
    procedure (C and G held fixed; Levenberg-Marquardt + parset-style
    seed re-drawn for every Monte-Carlo iteration).
* **a.u. ⇄ %** toggle — display the efficiency in arbitrary units or
  in percent, normalized to the KFR curve peak (the underlying fits
  stay unchanged; χ² is scale-invariant).

All predictions ship with Birge-corrected 1 σ uncertainty bands.

---

## Input file format

7 columns, whitespace-separated, no header — one row per gamma peak:

```
ch   Δch   N   ΔN   E[keV]   I[%]   ΔI[%]
```

`226Ra_En_Area.txt` (23 Ra-226 peaks) auto-loads when found beside the
executable.  Two extra sample sets, `demo1.txt` (Ba-133, 9 peaks) and
`demo2.txt` (Eu-152, 19 peaks), are bundled with every distribution.

---

## Distributions

Three turn-key packages live under `dist/`:

| Distribution    | What you get                                         | When to use                            |
|-----------------|------------------------------------------------------|----------------------------------------|
| `dist/WinExe/`  | Pre-built `Ra226_Calibration.exe` (≈ 200 MB)         | Windows users with no Python install  |
| `dist/WinBat/`  | Python source + `run.bat` / `build.bat`              | Windows users with Python              |
| `dist/Linux/`   | Python source + `run.sh` / `build.sh`                | Linux, macOS, WSL                      |

Each folder ships its own `README_install.md` with platform-specific
prerequisites, install commands, and troubleshooting tips.

---

## Quick start

### Windows binary

```text
cd dist\WinExe
Ra226_Calibration.exe
```

### Windows source

```bat
cd dist\WinBat
python -m pip install -r requirements.txt
run.bat
```

### Linux / macOS

```bash
cd dist/Linux
python3 -m pip install --user -r requirements.txt
chmod +x run.sh
./run.sh
```

---

## Workflow

1.  **Read calibration data** → select your `.txt` file (auto-loads
    `226Ra_En_Area.txt` if found next to the executable).
2.  **Make calibration** → ~10–20 s on a modern CPU (energy +
    efficiency Monte-Carlo, 10 000 resamples each).
3.  **Calculate Energy** → enter ch ± Δch, get E ± δE for linear and
    quadratic models.
4.  **Get Efficiency** → enter E (keV), get ε ± δε for KFR and Radware.
5.  **a.u. → %** → toggle between arbitrary units and percent of the
    KFR peak.
6.  Right-click any sub-plot → save just that panel.
    Right-click the figure margin → save the full figure.
7.  ☀ / 🌙 (top-right) → switch between light and dark theme.

A timestamped result file is written next to the data file after every
calibration and every query.

---

## Source layout

| File                       | Purpose                                   |
|---------------------------|-------------------------------------------|
| `ra226_gui.py`            | Main application (single file, ≈ 2 200 lines) |
| `Ra226_Calibration.spec`  | PyInstaller build recipe                  |
| `Ra226_Calibration.ico`   | Multi-resolution app icon (16…256 px)     |
| `make_icon.py`            | Regenerate the icon from scratch          |
| `226Ra_En_Area.txt`       | Sample dataset (23 peaks)                 |
| `requirements.txt`        | Python runtime + build dependencies       |
| `run.sh` / `run.bat`      | Source-distribution launchers             |
| `build.sh` / `build.bat`  | PyInstaller wrappers → `dist/WinExe/` (or `dist/LinuxExe/`) |
| `dist/WinExe/`            | Pre-built Windows binary                  |
| `dist/WinBat/`            | Windows-source distribution package       |
| `dist/Linux/`             | Unix-source distribution package          |
| `versions/v01/`           | Archive: original 4-param KFR only        |
| `versions/v02/`           | Archive: this version (KFR + Radword 5-p) |

---

## Math at a glance

* **Linear / quadratic energy fits** — weighted least squares against
  Δch.  10 000 batched MC fits give the parameter covariance and
  the propagated δE.
* **KFR efficiency** —
  `ε(E) = (a·E + b/E)·exp(c·E + d/E)`.
  Multi-start `curve_fit` (TRF, bounded) + MC warm-started from the
  best-fit popt.
* **Radware 5-parameter efficiency** — Radford's `effit.c` form with
  `C = 0` and `G = 15` fixed, leaving `a₁, a₂, a₄, a₅, a₆` free.
  Levenberg–Marquardt (Bevington CURFIT), `parset()` seed re-drawn
  from every Monte-Carlo sample — exactly the Radford procedure.
* **Birge ratio** `B = √(χ²/ndf)` is reported and used to scale the
  reported 1 σ band when the data scatter exceeds the stated σ
  ([reference](https://arxiv.org/html/2406.08293v3)).
