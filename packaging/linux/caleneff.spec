# Version is supplied by build_rpm.sh via --define "version X.Y", which reads
# it from Ra226_Calibration.iss so the whole project has one source of truth.
# The fallback below only applies when rpmbuild is invoked by hand.
%{!?version: %define version 4.0}

Name:           caleneff
Version:        %{version}
Release:        1%{?dist}
Summary:        Gamma-ray energy and efficiency calibration tool
License:        MIT
URL:            https://github.com/grainovski/CalEnEff
BuildArch:      noarch

# Build on AlmaLinux 10, NOT 8 — on 8 the python3-matplotlib package links
# against a libqhull.so.7 that is not in the repos, so the GUI cannot start.
Requires:       python3 >= 3.9
Requires:       python3-numpy
Requires:       python3-scipy
Requires:       python3-matplotlib
Requires:       python3-tkinter

%description
CalEnEff is a desktop application for gamma-ray energy and efficiency
calibration using a Ra-226 reference source. It performs weighted
polynomial fitting for energy calibration and fits a four-parameter
semi-empirical efficiency model (KFR) with Monte Carlo uncertainty
propagation (10 000 trials).

Key features:
  - Linear and quadratic energy calibration with Birge-ratio diagnostics
  - Four-parameter efficiency model with MC uncertainty propagation
  - Built-in browser-based help (HowTo, Knowledge Database, About)
  - Pre-loaded Ra-226 reference data covering 46–2448 keV

NOTE: the EPEL repository must be enabled before installing this package.
python3-matplotlib is not in the stock BaseOS, AppStream, CRB or Extras
repositories on AlmaLinux/RHEL 10; without EPEL the install fails with
"nothing provides python3-matplotlib".  Run "dnf install -y epel-release"
first.

%install
# License (packaged via %license so `rpm -qL caleneff` finds it)
install -d %{buildroot}/usr/share/licenses/caleneff
install -m 644 %{_sourcedir}/LICENSE %{buildroot}/usr/share/licenses/caleneff/

# Application files
install -d %{buildroot}/usr/share/caleneff
install -m 644 %{_sourcedir}/ra226_gui.py       %{buildroot}/usr/share/caleneff/
install -m 644 %{_sourcedir}/help_content.py    %{buildroot}/usr/share/caleneff/
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
gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
update-desktop-database 2>/dev/null || true

%changelog
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
