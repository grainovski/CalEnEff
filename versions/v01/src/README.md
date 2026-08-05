# Ra-226 Energy & Efficiency Calibration GUI

Interactive Tk/matplotlib tool for converting raw Ra-226 channel/peak data
into ch ↔ E calibration curves (linear + quadratic) **and** relative
detector efficiency ε(E) using two independent models:

- **KFR** — 4-parameter `ε(E) = (aE + b/E)·exp(cE + d/E)`
- **Radware** — 7-parameter `ln ε = [(a₁+a₂x+a₃x²)⁻ᵍ + (a₄+a₅y+a₆y²)⁻ᵍ]⁻¹⸍ᵍ`

Both are fitted with Monte-Carlo error propagation (10 000 resamples each)
and a Birge-scaled 1 σ uncertainty band is shown for every prediction.

---

## Input file format

7 columns, whitespace-separated, no header — one row per gamma peak:

```
ch  Δch  N  ΔN  E[keV]  I[%]  ΔI[%]
```

A sample file (`226Ra_En_Area.txt`, 23 peaks) is bundled with both
distributions.

---

## Distributions

### 1.  Bash / source distribution  (any OS with Python ≥ 3.9)

```bash
python -m pip install -r requirements.txt
./run.sh                 # Linux / macOS / WSL / Git-Bash
run.bat                  # Windows cmd.exe / PowerShell
```

### 2.  Stand-alone Windows executable

A single `Ra226_Calibration.exe` (~200 MB, contains Python, NumPy, SciPy,
matplotlib, Tk).  No installation required — just double-click.

Pre-built copy: `dist/Ra226_Calibration.exe`.
Rebuild from source: `./build.sh` (bash) or `build.bat` (Windows).

---

## Workflow

1. **Read calibration data** → select your `.txt` file (auto-loads
   `226Ra_En_Area.txt` if found next to the executable).
2. **Make calibration** → ~55 s on a modern CPU (energy + efficiency MC).
3. **Calculate Energy** → enter ch ± Δch, get E ± δE for linear and
   quadratic models.
4. **Get Efficiency** → enter E (keV), get ε ± δε for KFR and Radware.
5. Right-click any subplot → save just that panel.  Right-click margin →
   save the full figure.  ☀ / 🌙 → light / dark theme.

All results are also written to a timestamped `.txt` next to the data file.

---

## Files

| File | Purpose |
|---|---|
| `ra226_gui.py` | Main application (single file, ~1700 lines) |
| `Ra226_Calibration.spec` | PyInstaller build recipe |
| `Ra226_Calibration.ico` | Multi-size app icon (16…256 px) |
| `make_icon.py` | Generates the icon from scratch |
| `226Ra_En_Area.txt` | Bundled sample dataset (23 peaks) |
| `requirements.txt` | Python dependencies |
| `run.sh` / `run.bat` | Source-distribution launchers |
| `build.sh` / `build.bat` | Build the .exe via PyInstaller |
| `dist/Ra226_Calibration.exe` | Pre-built Windows executable |
