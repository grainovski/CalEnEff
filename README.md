# CalEnEff — Energy & Efficiency Calibration GUI

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

Released binaries are published on the
[Releases page](https://github.com/grainovski/CalEnEff/releases) — they are
not kept in the repository.

| Package                          | Platform                | Built by                        |
|----------------------------------|-------------------------|---------------------------------|
| `CalEnEff_Setup.exe`             | Windows 10/11 (x64)     | `build.ps1` (PyInstaller + Inno Setup 6) |
| `caleneff_<ver>_all.deb`         | Ubuntu / Debian         | `packaging/linux/build_deb.sh`  |
| `caleneff-<ver>-1.el10.noarch.rpm` | AlmaLinux / RHEL 10   | `packaging/linux/build_rpm.sh`  |

The Windows installer bundles its own Python runtime — nothing else to
install.  The Linux packages depend on the distribution's `python3-numpy`,
`python3-scipy`, `python3-matplotlib` and `python3-tk` (named
`python3-tkinter` on RHEL-family distributions).

**AlmaLinux / RHEL 10 and matplotlib.**  Of those four, only
`python3-matplotlib` is missing from the stock repositories (BaseOS,
AppStream, CRB, Extras) — `numpy`, `scipy` and `tkinter` are all in
AppStream.

Since **4.2** the RPM installs on a stock system anyway: it requires
`epel-release` (which *is* in the default Extras repo) and treats
matplotlib as a weak dependency, so dnf never blocks the install.  On a box
that already has EPEL loaded, matplotlib comes in automatically; otherwise
one more command finishes the job, and both `%post` and the launcher tell you
so:

```bash
sudo dnf install -y python3-matplotlib
```

*Why not just require it?*  dnf resolves a transaction against the repos
enabled **before** that transaction starts, so it cannot see an EPEL package
while `epel-release` is merely queued for installation in the same
transaction.  Verified on dnf 4.20.0 — even
`dnf install epel-release python3-matplotlib` fails with
`No match for argument: python3-matplotlib`.  4.0 and 4.1 required it
outright and so could not be installed on a stock system at all:

```
Error: Problem: conflicting requests
  - nothing provides python3-matplotlib needed by caleneff-4.1-1.el10.noarch
```

Ubuntu and Debian need nothing extra; all four are in their default
archives, so there matplotlib remains a hard `Depends`.

---

## Quick start

### Windows (installer)

Run `CalEnEff_Setup.exe` and launch **CalEnEff** from the Start menu.

### Linux

```bash
# Ubuntu / Debian
sudo apt install ./caleneff_4.2_all.deb

# AlmaLinux / RHEL — installs on a stock system; pulls in epel-release itself
sudo dnf install ./caleneff-4.2-1.el10.noarch.rpm
# then, only if it reports matplotlib is still missing:
sudo dnf install -y python3-matplotlib

caleneff
```

### From source (any platform)

```bash
python -m pip install -r requirements.txt
python ra226_gui.py
```

On Windows `run.bat` does the same with a dependency pre-check.

---

## Building

The version string in `Ra226_Calibration.iss` (`#define AppVersion`) is the
single source of truth — `build.ps1` and both Linux scripts read it, so a
release bump touches exactly one file.

```powershell
powershell -File build.ps1        # Windows installer → dist\WinInstaller\
```

```bash
# Linux packages — each runs as root inside its own WSL distro
wsl -d Ubuntu-24.04  -u root bash packaging/linux/build_deb.sh
wsl -d AlmaLinux-10  -u root bash packaging/linux/build_rpm.sh
```

Build the RPM on **AlmaLinux-10, not 8** — on 8 the `python3-matplotlib`
package links against a `libqhull.so.7` that is absent from the repos.

**Never smoke-test the RPM on the machine that built it.** `build_rpm.sh`
enables EPEL there, so the package always installs; that is how a
stock-system install defect shipped in both 4.0 and 4.1. Use a throwaway
instance: `wsl --install AlmaLinux-10 --name AlmaStock --no-launch`.

---

## Tests

```bash
python verify/verify_v4.py     # 28 checks — engine, headless
python verify/verify_gui.py    # 24 checks — real Tk widgets, needs a display, ~90 s
```

Both exit non-zero on failure and locate the repo from their own path, so
they run unedited from any checkout.

**Count the PASS lines, not the verdict.** Fewer than 28 and 24 means an
incomplete environment rather than a healthy project — a suite that silently
collects fewer checks looks identical to success.

Two things worth knowing:

* If your console is not UTF-8, prefix with `PYTHONIOENCODING=utf-8
  PYTHONUTF8=1`. The scripts print `Δ`, `ε`, `χ²`, and on cp1252 they die
  partway through with `UnicodeEncodeError`.
* `verify_gui.py` **overwrites `226Ra_En_Area_Res.txt`** — every calibration
  rewrites that file from scratch, so any query log in it is lost.

A full calibration takes ~14 s. If it takes ~70 s, the `OptimizeWarning`
filter near the top of `ra226_gui.py` is missing — one line, worth a 3–5×
difference.

`build.ps1` exiting 0 does **not** prove the frozen executable runs. Launch it
after building; this project's historical first-run crash was an MKL/Tk
interaction invisible when running from source.

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

| File                        | Purpose                                       |
|-----------------------------|-----------------------------------------------|
| `ra226_gui.py`              | Main application — the only file to edit for app changes |
| `help_content.py`           | HowTo / Knowledge Database / About pages (opened in the browser) |
| `Ra226_Calibration.spec`    | PyInstaller build recipe                      |
| `Ra226_Calibration.iss`     | Inno Setup script — **defines the version**   |
| `build.ps1`                 | Windows build: stamp `build_info.py` → PyInstaller → ISCC |
| `packaging/linux/`          | DEB and RPM build scripts, spec, desktop entry |
| `CalEnEff.ico`              | Multi-resolution app icon (16…256 px)         |
| `make_icon.py`              | Regenerate the icon from scratch              |
| `226Ra_En_Area.txt`         | Sample dataset (23 Ra-226 peaks)              |
| `demo1.txt` / `demo2.txt`   | Extra samples (Ba-133, Eu-152)                |
| `verify/`                   | Test suite — `verify_v4.py` (engine) and `verify_gui.py` (widgets) |
| `requirements.txt`          | Python runtime + build dependencies           |
| `run.bat`                   | Source launcher for Windows                   |
| `versions/v01…v03/`         | Source snapshots of earlier releases          |

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
* **Channel → energy inversion** uses the cancellation-free (Citardauq)
  form of the quadratic root, so Monte-Carlo samples whose curvature term
  drifts near zero stay finite instead of diverging.

---

## What's new in 4.0

**Correctness**

* Energy queries are seeded and therefore reproducible — repeating a query
  now yields identical numbers in the results log.
* Quadratic channel→energy inversion is numerically stable when the
  curvature coefficient approaches zero (previously it could return `inf`
  and poison the reported mean).
* Input files are validated on load with specific, row-numbered messages
  instead of failing later inside NumPy or SciPy.

**Stability**

* Mouse-wheel scrolling works on X11 (Linux) and macOS, not just Windows.
* The window stays responsive during calibration, and the close button is
  ignored mid-run rather than tearing down widgets under a running fit.
* A calibration in which Monte-Carlo fits fail now reports how many
  succeeded instead of presenting a weak result as a strong one.
* Loading a bad file can no longer leave the status bar describing one file
  while a different one is loaded.

**Performance**

* Calibration is roughly **5× faster** (~73 s → ~14 s): SciPy raised an
  `OptimizeWarning` on most Radware Monte-Carlo fits, and Python's warning
  machinery dominated the loop.
* Efficiency confidence bands are computed with vectorised NumPy over a
  capped sample count instead of a 10 000-iteration Python loop.

**Packaging**

* `MIT LICENSE` added (the About page already linked to it).
* The version is single-sourced from `Ra226_Calibration.iss`; the DEB and
  RPM scripts read it instead of hardcoding their own.
* UPX packing disabled — it risked the same DLL corruption as lzma2 and is
  a common antivirus false positive.

---

## License

MIT — see [LICENSE](LICENSE).
