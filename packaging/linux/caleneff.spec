# Version is supplied by build_rpm.sh via --define "version X.Y", which reads
# it from Ra226_Calibration.iss so the whole project has one source of truth.
# The fallback below only applies when rpmbuild is invoked by hand.
%{!?version: %define version 4.8}

Name:           caleneff
Version:        %{version}
Release:        1%{?dist}
Summary:        Gamma-ray energy and efficiency calibration tool
License:        MIT
URL:            https://github.com/grainovski/CalEnEff
BuildArch:      noarch

# Build on AlmaLinux 10, NOT 8 — on 8 the python3-matplotlib package links
# against a libqhull.so.7 that is not in the repos, so the GUI cannot start.
#
# These three are in AppStream on a stock AlmaLinux/RHEL 10.
Requires:       python3 >= 3.9
Requires:       python3-numpy
Requires:       python3-scipy
Requires:       python3-tkinter

# python3-matplotlib is the awkward one: on EL10 it exists only in EPEL.
#
# Requiring it outright is what made 4.0/4.1 uninstallable on a stock system —
# dnf resolves the whole transaction against the repos enabled *before* the
# transaction starts, so it cannot see an EPEL package while epel-release is
# still only a pending install in that same transaction.  Verified on dnf
# 4.20.0: even "dnf install epel-release python3-matplotlib" fails outright
# with "No match for argument: python3-matplotlib".  So no combination of hard
# Requires can make a one-command install work on a box without EPEL.
#
# Instead:
#   epel-release       hard dep, and satisfiable — it lives in "extras", which
#                      is enabled by default.  Installing us therefore always
#                      leaves EPEL configured for the next transaction.
#   python3-matplotlib weak dep, so a stock-system install is never blocked.
#                      dnf pulls it automatically on any system where EPEL
#                      metadata is already loaded, and on the next transaction
#                      otherwise.  The launcher checks for it and prints the
#                      exact command to run if it is genuinely absent.
Requires:       epel-release
Recommends:     python3-matplotlib

%description
CalEnEff is a desktop application for gamma-ray energy and efficiency
calibration using a Ra-226 reference source. It performs weighted
polynomial fitting for energy calibration and fits a four-parameter
semi-empirical efficiency model (KRF) with Monte Carlo uncertainty
propagation (10 000 trials).

Key features:
  - Linear and quadratic energy calibration with Birge-ratio diagnostics
  - Four-parameter efficiency model with MC uncertainty propagation
  - Built-in browser-based help (HowTo, Knowledge Database, About)
  - Pre-loaded Ra-226 reference data covering 46–2448 keV

NOTE on matplotlib: on AlmaLinux/RHEL 10 python3-matplotlib ships only in
EPEL, not in BaseOS, AppStream, CRB or Extras.  This package installs on a
stock system regardless: it pulls in epel-release (which is in the default
Extras repository), and treats matplotlib as a weak dependency so the install
is never blocked.  dnf installs matplotlib automatically when EPEL metadata is
already loaded.  If it was not, one more command finishes the job:

    dnf install -y python3-matplotlib

The caleneff launcher checks for matplotlib at startup and prints that exact
command if it is missing, rather than failing with a Python traceback.

%install
# License (packaged via %license so `rpm -qL caleneff` finds it)
install -d %{buildroot}/usr/share/licenses/caleneff
install -m 644 %{_sourcedir}/LICENSE %{buildroot}/usr/share/licenses/caleneff/

# Application files
install -d %{buildroot}/usr/share/caleneff
install -m 644 %{_sourcedir}/ra226_gui.py       %{buildroot}/usr/share/caleneff/
install -m 644 %{_sourcedir}/help_content.py    %{buildroot}/usr/share/caleneff/
install -m 644 %{_sourcedir}/spectratools_export.py %{buildroot}/usr/share/caleneff/
install -m 644 %{_sourcedir}/build_info.py      %{buildroot}/usr/share/caleneff/
install -m 644 %{_sourcedir}/226Ra_En_Area.txt  %{buildroot}/usr/share/caleneff/
install -m 644 %{_sourcedir}/demo1.txt          %{buildroot}/usr/share/caleneff/
install -m 644 %{_sourcedir}/demo2.txt          %{buildroot}/usr/share/caleneff/
install -m 644 %{_sourcedir}/caleneff.png       %{buildroot}/usr/share/caleneff/

# Launcher
install -d %{buildroot}/usr/bin
install -m 755 %{_sourcedir}/caleneff.sh        %{buildroot}/usr/bin/caleneff

# Desktop entry
install -d %{buildroot}/usr/share/applications
install -m 644 %{_sourcedir}/caleneff.desktop   %{buildroot}/usr/share/applications/

# System icon (128x128 PNG)
install -d %{buildroot}/usr/share/icons/hicolor/128x128/apps
install -m 644 %{_sourcedir}/caleneff.png \
               %{buildroot}/usr/share/icons/hicolor/128x128/apps/caleneff.png

%files
%license /usr/share/licenses/caleneff/LICENSE
/usr/share/caleneff/
/usr/bin/caleneff
/usr/share/applications/caleneff.desktop
/usr/share/icons/hicolor/128x128/apps/caleneff.png

%post
# Drop any bytecode left by a previous version, then recompile.
#
# This is not belt-and-braces.  CPython decides a cached .pyc is still valid
# from the (mtime, size) pair of the source recorded in the .pyc header, and
# rpm normalises every installed file's mtime to midnight UTC of the BUILD
# DATE -- identical for every package built on the same day.  So for any .py
# whose size did not change, that pair is byte-identical between two same-day
# builds and the OLD bytecode is silently reused.  build_info.py is the
# guaranteed case (VERSION = "4.6" and VERSION = "4.7" are the same length):
# 4.6 installed cleanly over 4.4 and still reported 4.4.  A code fix that
# happens to leave a file's size unchanged would likewise not take effect.
#
# The path is written out literally rather than built from a variable: an
# empty expansion in an rm -rf is not a risk worth taking for brevity.
rm -rf /usr/share/caleneff/__pycache__
/usr/bin/python3 -m compileall -q /usr/share/caleneff >/dev/null 2>&1 || true

gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
update-desktop-database 2>/dev/null || true

# matplotlib is a weak dependency (see the Recommends above), so it can be
# absent after a successful install on a system that did not have EPEL loaded.
# Say so here rather than letting the user discover it when the GUI fails.
if ! /usr/bin/python3 -c 'import matplotlib' >/dev/null 2>&1; then
    cat <<'EOM'

  CalEnEff is installed, but python3-matplotlib is not present yet.
  EPEL has just been configured for you; one more command finishes the setup:

      sudo dnf install -y python3-matplotlib

EOM
fi

%postun
# $1 is the number of versions left: 0 on erase, 1 during an upgrade.  Only
# the erase case should clean up, and only bytecode we generated in %post --
# it belongs to no package, so rpm will not remove it for us.
if [ "$1" = "0" ]; then
    rm -rf /usr/share/caleneff/__pycache__
    rmdir /usr/share/caleneff 2>/dev/null || true
fi

%changelog
* Fri Sep 25 2026 grainovski <grainovski@googlemail.com> - 4.8-1
- Query results carry the Birge scaling the plotted bands always had; they
  used to report the unscaled Monte Carlo spread. For an energy query only the
  calibration's share is scaled, never the user's own channel uncertainty.
- Relative efficiency is normalised to the KRF peak inside the fitted range,
  one number shared by the %% display and the SpectraTools export. Both used
  extrapolated maxima before and disagreed with each other by 2.1%%.
- Queries outside the fitted range are flagged in the status bar and marked
  EXTRAPOLATED in the query log; energy queries log the fit's RMS residual.
- New example dataset: a real Ra-226 measurement with its own peak-fit
  uncertainties, and emission probabilities from the IAEA recommended
  standards. The previous file mixed evaluations (up to 16%% wrong) and had
  uncertainties far below their physical minimums.
- Knowledge Database corrected line by line (58 values, 4 non-existent lines
  removed); Ra-226 caveats on radon equilibrium, Pb-210 and coincidence
  summing; the help now describes the methods the app actually uses.

* Thu Sep 24 2026 grainovski <grainovski@googlemail.com> - 4.7-1
- Clear stale bytecode on install and upgrade. Neither package removed
  /usr/share/caleneff/__pycache__, and rpm normalises every installed file's
  mtime to midnight UTC of the build date, identical for all packages built on
  the same day. CPython validates a cached .pyc from the recorded (mtime, size)
  of its source, so for any .py whose size did not change that pair matched and
  the OLD bytecode was reused: 4.6 installed cleanly over 4.4 and still
  reported 4.4 in the About box and in the SpectraTools export header. A code
  fix that happened to leave a file's size unchanged would equally not have
  taken effect. postun now also removes bytecode it generated, which belongs to
  no package and was previously orphaned on erase.
- The Windows executable carries a version resource at last: version,
  publisher and copyright were blank in its Explorer Details tab, although the
  installer had carried all three since 4.4. No Linux effect; recorded here so
  the three packages keep one changelog.

* Wed Sep 24 2026 grainovski <grainovski@googlemail.com> - 4.6-1
- Internal only, no behaviour change: the SpectraTools export moved out of the
  GUI class into its own module, spectratools_export.py, so it can be imported
  and tested without creating a window. The module is now named explicitly in
  this spec, in build_rpm.sh and in build_deb.sh -- all three install a fixed
  file list, so a module missing from them ships a package that cannot import
  it while the Windows build works fine.

* Wed Sep 24 2026 grainovski <grainovski@googlemail.com> - 4.5-1
- An uncertainty band is never narrowed by a Birge ratio below 1. All four
  plotted 1-sigma bands scaled unconditionally, so a ratio under 1 reported an
  interval TIGHTER than the Monte Carlo spread it came from, understating the
  uncertainty. Reachable by relaxing the quoted dN/dI, which come from
  intensity tables: at x3 the efficiency Birge falls to 0.83 and the band was
  narrowed to 83%%. Bands now inflate only.
- The band legends report the factor actually applied rather than the raw
  ratio, which would otherwise read "B=0.83" beside an unscaled band.
- Correct f_radware's docstring: the formula is dominated by max(f1, f2), the
  less negative branch, not the more negative one it claimed. Code unchanged.

* Wed Sep 24 2026 grainovski <grainovski@googlemail.com> - 4.4-1
- Nothing is written beside the executable any more. An installed copy sits
  under a directory a standard user cannot write to, so a calibration on the
  bundled sample could not write its results file at all; dialogs and results
  now default to the user's Documents folder.
- Rename the four-parameter model KFR to KRF throughout, matching
  SpectraTools, which renamed the same model at 6.1.1.
- New File -> Export for SpectraTools, writing the energy coefficients and
  the relative efficiency curve in the formats SpectraTools 6.1.1 reads.
- Copyright to Georgi Rainovski.

* Tue Sep 23 2026 grainovski <grainovski@googlemail.com> - 4.3-1
- Add a File menu (Open / Save / Save as / Exit) in the top-left corner.
  There was previously no way to save results explicitly, and no way to
  write them anywhere other than the automatic {basename}_Res.txt.
- Save as copies the results file rather than regenerating it, so query
  results already appended to it are preserved.

* Sun Aug 30 2026 grainovski <grainovski@googlemail.com> - 4.2-1
- The package now INSTALLS on a stock AlmaLinux/RHEL 10. 4.0 and 4.1 could not:
  they required python3-matplotlib outright, which exists only in EPEL, so dnf
  stopped with "nothing provides python3-matplotlib".
- python3-matplotlib is now a weak dependency (Recommends) and epel-release a
  hard one. epel-release is in the default Extras repository, so installing
  CalEnEff configures EPEL as a side effect; dnf then pulls matplotlib
  automatically on any system where EPEL metadata is loaded.
- %post reports it when matplotlib is still absent, and the launcher checks at
  startup and prints the one command that fixes it instead of dying with an
  ImportError traceback.

* Sun Aug 30 2026 grainovski <grainovski@googlemail.com> - 4.1-1
- Documentation only; no change to the application.
- Record that the EPEL repository must be enabled before installing:
  python3-matplotlib is not in the stock BaseOS, AppStream, CRB or Extras
  repositories on AlmaLinux/RHEL 10, so without EPEL the install fails with
  "nothing provides python3-matplotlib".

* Thu Aug 27 2026 grainovski <grainovski@googlemail.com> - 4.0-1
- Correctness: seeded energy-query MC so repeated queries reproduce; cancellation-free
  quadratic inversion that stays finite as the curvature term approaches zero;
  validation of the input data file with actionable error messages
- Stability: mouse-wheel scrolling now works on X11; window stays responsive during
  calibration; failed Monte Carlo fits are reported instead of crashing
- Performance: vectorised efficiency confidence bands, roughly 7x faster redraw

* Thu Aug 27 2026 grainovski <grainovski@googlemail.com> - 3.0-1
- Initial RPM release
- Help section with HowTo, Knowledge Database (canvas curves, 13 sources), About
- PowerShell build system; Windows-installer-only distribution replaced by RPM+DEB
