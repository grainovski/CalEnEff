@echo off
REM ----------------------------------------------------------------------------
REM run.bat -- launch the Ra-226 Energy & Efficiency Calibration GUI from source
REM on Windows (cmd.exe / PowerShell).  Override interpreter with: set PYTHON=...
REM ----------------------------------------------------------------------------
setlocal
pushd "%~dp0"

if not defined PYTHON set "PYTHON=python"
where %PYTHON% >nul 2>&1
if errorlevel 1 (
    echo Error: %PYTHON% not found on PATH.
    echo Install Python 3.9+ or set PYTHON=C:\path\to\python.exe
    popd & exit /b 1
)

%PYTHON% -c "import numpy, scipy, matplotlib, PIL, tkinter" >nul 2>&1
if errorlevel 1 (
    echo Missing dependencies. Install with:
    echo   %PYTHON% -m pip install -r requirements.txt
    popd & exit /b 1
)

%PYTHON% "%~dp0ra226_gui.py" %*
popd
endlocal
