# Ra-226 Calibration — Linux / macOS / WSL Source Distribution

Run from source on any Unix-like OS with Python ≥ 3.9.

## Prerequisites

### Linux (Debian / Ubuntu / Mint)

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-tk
```

### Linux (Fedora / RHEL / Rocky)

```bash
sudo dnf install -y python3 python3-pip python3-tkinter
```

### Linux (Arch / Manjaro)

```bash
sudo pacman -S --needed python python-pip tk
```

### macOS

Install Python from <https://www.python.org/downloads/macos/> *or* via
Homebrew:

```bash
brew install python-tk@3.12     # adjust to your installed Python
```

The system Python on macOS does **not** include a working Tk — use the
python.org installer or Homebrew.

### Windows (Git-Bash / MSYS2 / WSL)

Use the WinBat distribution instead, or install Python 3.9+ inside WSL
following the Debian instructions above.

## Install

In this folder:

```bash
python3 -m pip install --user -r requirements.txt
```

Use `--user` if you do not want to touch the system site-packages
(recommended for desktop installs).  For a clean isolated environment
use a virtualenv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
chmod +x run.sh         # only the first time
./run.sh
```

`run.sh` probes for dependencies and prints a clear error if anything
is missing.  Override the interpreter via:

```bash
PYTHON=/path/to/python3 ./run.sh
```

## Build a stand-alone binary (optional)

```bash
chmod +x build.sh
./build.sh
```

On Linux this produces `dist/LinuxExe/Ra226_Calibration` (≈ 200 MB).
Cross-building a Windows `.exe` from Linux is not supported by
PyInstaller — use `build.bat` from the `WinBat` distribution under
Windows for that.

## Contents

| File                       | Purpose                                     |
|---------------------------|---------------------------------------------|
| `ra226_gui.py`            | Application source (single file)            |
| `Ra226_Calibration.spec`  | PyInstaller recipe                          |
| `Ra226_Calibration.ico`   | App icon (used by `make_icon.py`)           |
| `make_icon.py`            | Regenerate the icon from scratch            |
| `requirements.txt`        | Python dependencies                         |
| `226Ra_En_Area.txt`       | Sample dataset — 23 Ra-226 peaks            |
| `demo1.txt`               | Sample dataset — 9 Ba-133 peaks             |
| `demo2.txt`               | Sample dataset — 19 Eu-152 peaks            |
| `run.sh`                  | Launcher (checks deps, then runs the GUI)   |
| `build.sh`                | PyInstaller wrapper → `dist/LinuxExe/`      |

## Data file format

7 whitespace-separated columns, no header, one row per gamma peak:

```
ch   Δch   N   ΔN   E[keV]   I[%]   ΔI[%]
```

## Workflow

1.  *Read calibration data* → pick a 7-column `.txt`.
2.  *Make calibration* → energy + efficiency Monte-Carlo fits.
3.  *Calculate Energy* → ch ± Δch  ⇒  E ± δE.
4.  *Get Efficiency* → E (keV)  ⇒  ε ± δε  (KFR + Radware 5-parameter).
5.  *a.u. → %* → toggle the efficiency display.

## Troubleshooting

* **`ModuleNotFoundError: No module named 'tkinter'`** — install the
  system Tk package (see *Prerequisites* above).
* **`Missing dependencies`** from `run.sh` — install with `pip` per
  the *Install* section.
* **Tk window doesn't open under WSL** — install an X server such as
  VcXsrv on Windows and set `export DISPLAY=:0` before running.
* **macOS: window opens but is blank** — the system Python's Tk is
  broken; install python.org or Homebrew Python instead.
