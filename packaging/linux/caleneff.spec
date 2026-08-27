Name:           caleneff
Version:        3.0
Release:        1%{?dist}
Summary:        Gamma-ray energy and efficiency calibration tool
License:        MIT
URL:            https://github.com/grainovski/CalEnEff
BuildArch:      noarch

# AlmaLinux 8: scipy/matplotlib are in EPEL
# The %check section verifies runtime imports after install
Requires:       python3 >= 3.6
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

%install
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
/usr/share/caleneff/
/usr/bin/caleneff
/usr/share/applications/caleneff.desktop
/usr/share/icons/hicolor/128x128/apps/caleneff.png

%post
gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
update-desktop-database 2>/dev/null || true

%changelog
* Thu Aug 27 2026 grainovski <grainovski@googlemail.com> - 3.0-1
- Initial RPM release
- Help section with HowTo, Knowledge Database (canvas curves, 13 sources), About
- PowerShell build system; Windows-installer-only distribution replaced by RPM+DEB
