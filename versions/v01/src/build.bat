@echo off
REM ----------------------------------------------------------------------------
REM build.bat -- build the self-contained Ra-226 Calibration .exe with
REM PyInstaller (regenerates the icon first).
REM Output: dist\Ra226_Calibration.exe
REM ----------------------------------------------------------------------------
setlocal
pushd "%~dp0"

if not defined PYTHON set "PYTHON=python"
where %PYTHON% >nul 2>&1 || (
    echo Error: %PYTHON% not found on PATH.
    popd & exit /b 1
)

echo Using interpreter:
%PYTHON% -c "import sys; print('  '+sys.executable)"

echo Regenerating icon...
%PYTHON% make_icon.py || (popd & exit /b 1)

echo Running PyInstaller...
%PYTHON% -m PyInstaller --noconfirm Ra226_Calibration.spec || (popd & exit /b 1)

if exist "dist\Ra226_Calibration.exe" (
    for %%I in ("dist\Ra226_Calibration.exe") do echo Built  %%~fI  %%~zI bytes
) else (
    echo Build did not produce dist\Ra226_Calibration.exe
    popd ^& exit /b 2
)
popd
endlocal
