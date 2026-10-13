Name:           ryzen-control
# DKMS module version: changes only with the source in ryzen_smu/ (= DRV_VERSION in the Makefile);
# this way an app release does not rebuild the module.
%global drv_version 0.4.1
Version:        0.8.0
Release:        1%{?dist}
Summary:        Curve Optimizer, PBO limits, boost and fans for AMD Ryzen CPUs
# App GPL-3.0-or-later; bundled ryzen_smu driver (ryzen_smu/) GPL-2.0-only.
License:        GPL-3.0-or-later AND GPL-2.0-only
URL:            https://github.com/SenseiKiritof/Ryzen-Control
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  make
BuildRequires:  systemd-rpm-macros
Requires:       python3 >= 3.9
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita >= 1.5
Requires:       polkit
Requires:       systemd
Requires:       dkms
Requires:       kernel-devel
Requires:       gcc
Requires:       make
Requires(post): dkms
Requires(preun): dkms
Recommends:     stress-ng
Recommends:     libnotify
# Up to 0.1.0-4 the driver was a separate subpackage.
Obsoletes:      ryzen-smu-dkms < 0.1.0-5
Provides:       ryzen-smu-dkms = %{version}-%{release}
%{?systemd_requires}

%description
Ryzen Master-style control for AMD Ryzen processors on Linux
(Ryzen 9000 desktop verified, Ryzen 1000-7000 desktop and the APUs of
desktops, mini PCs and laptops expected):
per-core Curve Optimizer and Curve Shaper, PPT/TDC/EDC limits, boost
frequency and maximum temperature, power profile and motherboard fans.
Profiles applied at boot with protection after a crash: the profile is
not reapplied until the user decides.

A single package: the ryzen-control GUI, the privileged helper ryzenctl (CLI), the systemd
services and the source of the ryzen_smu kernel module (amkillam/ryzen_smu, with
additional PM table sizes for Granite Ridge), built by DKMS for every installed
kernel. With Secure Boot enabled the module is signed with the akmods key
if it is already enrolled in MOK, otherwise with the DKMS key, to be
enrolled once: mokutil --import /var/lib/dkms/mok.pub

%prep
%autosetup

%build
# Nothing to build: Python scripts; the driver is built by DKMS on the system.

%install
make install DESTDIR=%{buildroot} PREFIX=%{_prefix}
# Translation catalogs (po/<domain>/<lang>.po, compiled by po/msgfmt.py during make install).
%find_lang ryzenctl
%find_lang ryzen-control
# Created by the %%post only when the akmods key is enrolled; here only to track it (%%ghost).
install -dm755 %{buildroot}%{_sysconfdir}/dkms/framework.conf.d
touch %{buildroot}%{_sysconfdir}/dkms/framework.conf.d/ryzen-smu-akmods.conf

%post
# 1. Driver. Secure Boot without manual steps: if the akmods key (NVIDIA etc.) exists and is
#    already enrolled in MOK, DKMS signs with it. The drop-in applies to every DKMS module.
AKMODS_KEY=/etc/pki/akmods/private/private_key.priv
AKMODS_CERT=/etc/pki/akmods/certs/public_key.der
DROPIN=%{_sysconfdir}/dkms/framework.conf.d/ryzen-smu-akmods.conf
FORCE=""
if [ ! -s "$DROPIN" ] && [ -f "$AKMODS_KEY" ] && [ -f "$AKMODS_CERT" ] \
   && mokutil --test-key "$AKMODS_CERT" 2>/dev/null | grep -q 'already enrolled'; then
    printf 'mok_signing_key=%%s\nmok_certificate=%%s\n' "$AKMODS_KEY" "$AKMODS_CERT" > "$DROPIN"
    FORCE="--force"   # new key: the module must be re-signed
fi
# `dkms add --rpm_safe_upgrade` ALWAYS: it creates the lock that cancels the `dkms remove` of the
# old package's %%preun in the same transaction (without it, the upgrade deletes the module).
dkms add -m ryzen_smu -v %{drv_version} -q --rpm_safe_upgrade || :
# Rebuild only if needed: a rebuild + dracut of all the initramfs costs about a minute.
# When the driver source changes, %%drv_version must be bumped (new /usr/src directory).
if [ -n "$FORCE" ] || ! dkms status -m ryzen_smu -v %{drv_version} -k "$(uname -r)" 2>/dev/null | grep -q ': installed'; then
    dkms build -m ryzen_smu -v %{drv_version} -q $FORCE || :
    dkms install -m ryzen_smu -v %{drv_version} -q $FORCE || :
fi
if [ ! -s "$DROPIN" ] && grep -qE '\[(integrity|confidentiality)\]' /sys/kernel/security/lockdown 2>/dev/null \
   && ! mokutil --test-key /var/lib/dkms/mok.pub 2>/dev/null | grep -q 'already enrolled'; then
    echo "ryzen-control: Secure Boot enabled and DKMS key not enrolled. Once only:"
    echo "  sudo mokutil --import /var/lib/dkms/mok.pub   (then reboot, MOK Manager -> Enroll MOK)"
    echo "Until then the ryzen_smu module cannot be loaded."
fi
# 2. Services: the preset enables them; start now (loads the module, captures the baseline, no
#    profile applied; the reapply timer does nothing without a laptop profile).
%systemd_post ryzenctl.service ryzenctl-resume.service ryzenctl-reapply.timer
if [ -d /run/systemd/system ]; then
    systemctl start ryzenctl.service ryzenctl-reapply.timer >/dev/null 2>&1 || :
fi

%preun
%systemd_preun ryzenctl.service ryzenctl-resume.service ryzenctl-reapply.timer ryzenctl-reapply.service
dkms remove -m ryzen_smu -v %{drv_version} -q --all --rpm_safe_upgrade || :

%postun
%systemd_postun ryzenctl.service ryzenctl-resume.service ryzenctl-reapply.timer ryzenctl-reapply.service

# The reapply timer is new in 0.8.0: %%systemd_post presets units on a fresh install only
%triggerun -- ryzen-control < 0.8.0
systemctl --no-reload preset ryzenctl-reapply.timer >/dev/null 2>&1 || :

%files -f ryzenctl.lang -f ryzen-control.lang
%license LICENSE ryzen_smu/LICENSE
%doc README.md ryzen_smu/UPSTREAM.md
%{_bindir}/ryzenctl
%{_bindir}/ryzen-control
%{_datadir}/applications/org.ryzencontrol.RyzenControl.desktop
%{_datadir}/icons/hicolor/scalable/apps/org.ryzencontrol.RyzenControl.svg
%{_metainfodir}/org.ryzencontrol.RyzenControl.metainfo.xml
%{_unitdir}/ryzenctl.service
%{_unitdir}/ryzenctl-resume.service
%{_unitdir}/ryzenctl-reapply.service
%{_unitdir}/ryzenctl-reapply.timer
%{_presetdir}/80-ryzen-control.preset
%{_udevrulesdir}/60-ryzen-control.rules
%{_modprobedir}/ryzen-control.conf
%{_datadir}/polkit-1/actions/org.ryzencontrol.RyzenControl.policy
%config(noreplace) %{_sysconfdir}/xdg/autostart/ryzenctl-notify.desktop
%dir %{_sysconfdir}/ryzenctl
%dir %{_sysconfdir}/ryzenctl/profiles
%dir %{_sharedstatedir}/ryzenctl
%{_usrsrc}/ryzen_smu-%{drv_version}/
%ghost %config(noreplace) %{_sysconfdir}/dkms/framework.conf.d/ryzen-smu-akmods.conf

%changelog
* Tue Oct 13 2026 senseikiritof <tonifede98@gmail.com> - 0.8.0-1
- APUs (Ryzen 4000G-8000G, mini PCs, laptops; expected): fast/slow PPT, Tctl, TDC/EDC read back from the
  PM table; Quiet and Performance
- Laptops: the baseline records the power source, CPU writes only on that source; the reapply timer and a
  udev rule write the profile's limits again after the firmware's rewrites, and stop after 3 corrections
  within 2 minutes
- Default chosen by hand keeps "Apply at startup" (after a crash, "Stay on Default" still turns it off)

* Tue Oct 13 2026 senseikiritof <tonifede98@gmail.com> - 0.7.1-1
- Release workflow: the GitHub release is created once with the RPM, the .deb and the Arch package
  (immutable releases); the Arch build no longer trips on the CI checkout's owner

* Tue Oct 13 2026 senseikiritof <tonifede98@gmail.com> - 0.7.0-1
- Debian/Ubuntu and Arch packages (packaging/debian, packaging/PKGBUILD) on the same make install

* Tue Oct 13 2026 senseikiritof <tonifede98@gmail.com> - 0.6.0-2
- "Start minimized to the tray icon": at login only the icon, or the window as well

* Tue Oct 13 2026 senseikiritof <tonifede98@gmail.com> - 0.6.0-1
- System tray icon (StatusNotifierItem): modes, custom calibrations, Apply at startup and the crash
  choice from its menu, Tctl/PPT in the tooltip; `ryzen-control --tray` and a Preferences switch, the
  login entry then starts only the icon (no password until the menu is used)

* Tue Oct 13 2026 senseikiritof <tonifede98@gmail.com> - 0.5.1-1
- The calibration watchdog is driven by systemd: a freeze or a kernel crash resets the PC, a Ryzen
  Control that dies does not (its interrupted step counts as a crash when it starts again)
- A custom calibration that ignores the crash of the measurement says so in its window

* Tue Oct 13 2026 senseikiritof <tonifede98@gmail.com> - 0.5.0-5
- The calibration watchdog is driven by systemd: a freeze still resets the PC, a Ryzen Control that
  dies does not; its interrupted step counts as a crash when it starts again

* Tue Oct 13 2026 senseikiritof <tonifede98@gmail.com> - 0.5.0-4
- A custom calibration that ignores the crash says so in its window; homepage URL in the metadata

* Tue Oct 13 2026 senseikiritof <tonifede98@gmail.com> - 0.5.0-3
- Custom calibrations can retry from the last stable value, ignoring the crash of the measurement
- The single-core test is chosen in the first calibration dialog, at every start

* Tue Oct 13 2026 senseikiritof <tonifede98@gmail.com> - 0.5.0-2
- Ryzen 5000 (Curve Optimizer -30..+30, limits), Ryzen 3000 (limits) and Ryzen 1000/2000 (boost,
  power, fans) recognised, not verified yet; FMax optional; boost on/off through the kernel; Tdie on
  the X parts with an offset; motherboard limits in the BIOS: Quiet/Eco on AMD's Eco mode values
- Calibration: each core alone in the final pass (choice, on by default), hardware watchdog while a
  calibration runs from the GUI, Verify of a saved profile, custom calibrations saved under their
  own name (Eco/Auto/Boost and their measurement untouched)
- Fixes: second-CCD presence bit in the fuse map, per-core PM table values by physical slot

* Mon Oct 12 2026 senseikiritof <tonifede98@gmail.com> - 0.5.0-1
- Other Ryzen CPUs: per-family SMU allowlist (Granite Ridge verified, other Ryzen 9000 and
  Raphael expected), cores from the system topology, core fuses for CCDs with disabled cores;
  README table of the processors and the hwtest procedure to verify a new one

* Mon Oct 12 2026 senseikiritof <tonifede98@gmail.com> - 0.4.5-3
- Per-core Curve Optimizer also on CPUs with disabled cores (physical positions from the core
  fuses, read-only); the GUI shows and uses only the active cores and the CPU family

* Mon Oct 12 2026 senseikiritof <tonifede98@gmail.com> - 0.4.5-2
- Raphael (Ryzen 7000) recognised, not verified yet: Curve Optimizer and FMax; per-core Curve
  Optimizer refused on CPUs with disabled cores (the physical core is not known)

* Mon Oct 12 2026 senseikiritof <tonifede98@gmail.com> - 0.4.5-1
- Groundwork for other Ryzen CPUs: per-family SMU allowlist and PM table, cores from the system
  topology, Curve Optimizer mask with the CCD; nothing changes on the 9800X3D

* Sun Oct 11 2026 senseikiritof <tonifede98@gmail.com> - 0.4.4-1
- Eco reuses the undervolt validated by Auto/Boost with the Eco preset (instant when a recorded
  final pass covers it); Boost only with "Allow beyond the stock values"; unknown fan channels in
  a collapsed section; calibration window with the progress pinned on top; README GIF

* Sun Oct 11 2026 senseikiritof <tonifede98@gmail.com> - 0.4.3-4
- Every mode shows and applies a complete state: the stock values of what a profile does not set
  (fan curve and steps, limits) are included, so switching mode never keeps another mode's fans

* Sun Oct 11 2026 senseikiritof <tonifede98@gmail.com> - 0.4.3-3
- Monitor graph with legend, coloured axes, PPT limit line and time hint; Preferences tab for
  startup and limits; fan rows of the profile tables aligned and Eco fan texts matching the curve;
  Fans page flag to show unknown channels (remembered)

* Sun Oct 11 2026 senseikiritof <tonifede98@gmail.com> - 0.4.3-2
- Moderate fan level (Auto and Boost default): BIOS curve +10 % with full speed at 100 °C instead
  of 125 °C, rise 3 s / fall 2 s

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.4.3-1
- Source, documentation and UI in English; UI and ryzenctl messages follow the system language
  (gettext, Italian catalog); CLI `unlock` crash fixed

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.4.2-4
- Calibration: fan level (BIOS / moderate / quiet) chosen in automatic mode too; Auto touches
  the fans with 5 s/3 s steps and a curve from the target

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.4.2-3
- Modes: "Startup and limits" below the presets, fan curves on two rows

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.4.2-2
- Preset and Calibrated columns always side by side

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.4.2-1
- Modes on two columns, profile values side by side, separate DKMS version (fast
  updates), GitHub Actions for the releases

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.4.1-3
- DKMS module version separated from the app's: releases no longer rebuild the module

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.4.1-2
- Modes on two columns (Preset / Calibrated), short profile values side by side

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.4.1-1
- Fixes after the freezes during calibration: attribution at boot, heavy method in the search,
  +3 margin after a crash and explanation in the GUI; default repaired; profiles in seconds and rpm

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.4.0-3
- After a freeze the GUI shows the CO of the crash and the value it restarts from

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.4.0-2
- +3 margin when the CO search ends with a system freeze

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.4.0-1
- Phases 3 (GUI) and 4 (calibrations) verified on hardware: version aligned with tag v0.4.0
  (the new DKMS source directory rebuilds the module once)

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-31
- Profile tables: fan steps in seconds, curve points with estimated rpm

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-30
- Crash during calibration attributed already at boot; heavy method in the CO search (earlier
  measurements not reused); Default no longer fails on the BIOS's 0 fan steps

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-29
- Calibration window: error on every state (empty table, steps stuck) fixed

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-28
- Remembered authorisation: ryzenctl trust and the "Don't ask for the password again" switch
  (polkit rule for the user, only for this application)

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-27
- Calibration: freeze or dead benchmark with the final CO applied = unstable combination
  (+3, final pass repeated); final pass with the heaviest method; failed combinations remembered;
  crash notification that opens the application

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-26
- End of calibration: Cancel / Save / Save and apply (autotune save [apply]); switch to start
  the GUI at login

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-25
- Pump: automatic (BIOS, recommended), maximum cap on the BIOS curve or fixed speed, from the
  CLI and from the Fans page

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-24
- cairo renderer (no fragments with NVIDIA), failed final passes explained, heavier load for
  the knee, test on both SMT threads, fan curve in °C → %%

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-23
- Calibration window with constant heights and full redraw: no fragments

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-22
- Immediate Stop: the step in progress terminates the loads and returns without recording anything

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-21
- Calibration window: centred content and grid that uses the available width

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-20
- Fan curves read back without the filler points

* Sat Oct 10 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-19
- Resizable calibration window, fixed-width columns (no artifacts)

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-18
- Calibration: factory CO, voltage measured per core and per level, mV per step; live voltage
  in the Monitor and in the Curves

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-17
- Parallel calibration (default) with duration estimates; mixed bursts for the Tctl p95 with the
  eco limits already applied; CO explained; compact Modes rows

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-16
- GUI: profile values coloured against the factory ones, automatic calibration or with parameters

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-15
- Separate Eco and Quiet modes; Eco/Auto autotune (per-core CO, FMax from the target, PPT/FMax
  knee) driven by the GUI with progress and resume after crash

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-14
- GUI: Quiet/Auto/Boost presets created on click, Ryzen Master-style slider+spin, dense monitor

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-13
- Mode shown from the selected profile; `default` clears the profile

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-12
- GUI: dialog with Retry if the pkexec authentication fails or is cancelled

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-11
- GTK4/libadwaita GUI ryzen-control (monitor, modes, CPU, curves, fans), menu entry

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-10
- dkms add --rpm_safe_upgrade always in the %%post: otherwise the %%preun of the previous
  package removes the module during the upgrade

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-9
- The %%post rebuilds the module only if it is missing for the running kernel or the signing key changes

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-8
- Fan curves: minimum pwm 51 (20 %%) like the BIOS curves

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-7
- Fan autodetect with a test pwm relative to the current value; curves with the last point up to 125 °C

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-6
- Fans: fan status/enable/autodetect/step/curve/identify/role/name, fan lines in profiles

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-5
- A single package: the DKMS driver goes into ryzen-control (obsoletes ryzen-smu-dkms)

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-4
- A baseline from a previous version with shaper lines is applied ignoring them;
  shaper probe with 0x84 per tier

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-3
- Readback of the limits with a wait (the PM table updates at the SMU's pace), experimental
  Curve Shaper out of profiles and hwtest, no unhandled exception (ABRT)

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-2
- Automatic signing with the akmods key if enrolled, forced rebuild, service started at
  installation, hwtest command

* Fri Oct 09 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-1
- First version: ryzenctl, systemd services, ryzen_smu driver via DKMS
