# Ra-226 Calibration — Windows Source Distribution (WinBat)

Run from source on Windows using `python` + `cmd.exe` / PowerShell.
Lighter than the standalone `.exe` (no PyInstaller payload) and easy to
modify.

## Prerequisites

1.  **Python 3.9 or newer** for Windows
    *(<https://www.python.org/downloads/windows/>)*.
    During installation **tick "Add Python to PATH"**.
2.  Tkinter is bundled with the official Python.org installer — no extra
    step needed.

## Install

Open `cmd.exe` (or PowerShell) in this folder and run:

```bat
python -m pip install -r requirements.txt
```

This pulls `numpy`, `scipy`, `matplotlib`, `pillow`, and `pyinstaller`
(the last is only needed if you also want to build a `.exe`).

## Run

```bat
run.bat
```

`run.bat` probes for the dependencies and prints a clear error if
anything is missing.  Override the interpreter via:

```bat
set PYTHON=C:\path\to\python.exe
run.bat
```

## Build a stand-alone `.exe` (optional)

```bat
build.bat
```

The built binary lands in `dist\WinExe\Ra226_Calibration.exe`
(≈ 200 MB).  This requires `pyinstaller` to be installed.

## Contents

| File                       | Purpose                                     |
|---------------------------|---------------------------------------------|
| `ra226_gui.py`            | Application source (single file)            |
| `Ra226_Calibration.spec`  | PyInstaller recipe                          |
| `Ra226_Calibration.ico`   | App icon (multi-resolution)                 |
| `make_icon.py`            | Regenerate the icon from scratch            |
| `requirements.txt`        | Python dependencies                         |
| `226Ra_En_Area.txt`       | Sample dataset — 23 Ra-226 peaks            |
| `demo1.txt`               | Sample dataset — 9 Ba-133 peaks             |
| `demo2.txt`               | Sample dataset — 19 Eu-152 peaks            |
| `run.bat`                 | Launcher (checks deps then runs the GUI)    |
| `build.bat`               | PyInstaller wrapper → `dist\WinExe\`        |

## Data file format

7 whitespace-separated columns, no header, one row per gamma peak:

```
ch   Δch   N   ΔN   E[keV]   I[%]   ΔI[%]
```

## Workflow

See the in-app *Workflow* tooltip or `README.md` in the parent
repository.  Briefly:

1.  *Read calibration data* → pick a 7-column `.txt`.
2.  *Make calibration* → energy + efficiency Monte-Carlo fits.
3.  *Calculate Energy* → ch ± Δch  ⇒  E ± δE.
4.  *Get Efficiency* → E (keV)  ⇒  ε ± δε  (KFR + Radware 5-parameter).
5.  *a.u. → %* → toggle the efficiency display.

## Troubleshooting

* **`'python' is not recognized`** — Python is not on PATH.  Either
  reinstall Python with *Add to PATH* enabled, or set `PYTHON=` before
  calling `run.bat`.
* **`ModuleNotFoundError`** — install dependencies with the `pip` line
  above.
* **PyInstaller fails to find DLLs** — make sure you are using the
  exact Python interpreter that has the dependencies installed
  (`build.bat` always uses `%PYTHON%`).
