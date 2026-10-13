Name:           silicon-control
# DKMS module version: changes only with the source in ryzen_smu/ (= DRV_VERSION in the Makefile);
# this way an app release does not rebuild the module.
%global drv_version 0.4.1
Version:        0.4.1
Release:        1%{?dist}
Summary:        Power limits, boost, undervolt and fans of the CPU, calibrated per chip
# App GPL-3.0-or-later; bundled ryzen_smu driver (ryzen_smu/) GPL-2.0-only.
License:        GPL-3.0-or-later AND GPL-2.0-only
URL:            https://github.com/SenseiKiritof/Silicon-Control
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
# Takeover of Ryzen Control (frozen at 0.8.x): dnf replaces it and `siliconctl boot` imports its state. Never both
# installed: two helpers would write the same CPU.
Obsoletes:      ryzen-control < 0.9
Conflicts:      ryzen-control
%{?systemd_requires}

%description
Control of the processor on Linux, successor of Ryzen Control. Supported
so far: AMD Ryzen (Ryzen 9000 desktop verified, Ryzen 1000-7000 desktop and
the APUs of desktops, mini PCs and laptops expected), with per-core Curve
Optimizer and Curve Shaper, PPT/TDC/EDC limits, boost frequency and maximum
temperature, power profile and motherboard fans.
Profiles applied at boot with protection after a crash: the profile is
not reapplied until the user decides.

A single package: the silicon-control GUI, the privileged helper siliconctl (CLI), the systemd
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
%find_lang siliconctl
%find_lang silicon-control
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
    echo "silicon-control: Secure Boot enabled and DKMS key not enrolled. Once only:"
    echo "  sudo mokutil --import /var/lib/dkms/mok.pub   (then reboot, MOK Manager -> Enroll MOK)"
    echo "Until then the ryzen_smu module cannot be loaded."
fi
# 2. Services: the preset enables them; start now (loads the module, captures the baseline, no
#    profile applied; the reapply timer does nothing without a laptop profile).
%systemd_post siliconctl.service siliconctl-resume.service siliconctl-reapply.timer
if [ -d /run/systemd/system ]; then
    systemctl start siliconctl.service siliconctl-reapply.timer >/dev/null 2>&1 || :
fi

%preun
%systemd_preun siliconctl.service siliconctl-resume.service siliconctl-reapply.timer siliconctl-reapply.service
dkms remove -m ryzen_smu -v %{drv_version} -q --all --rpm_safe_upgrade || :

%postun
%systemd_postun siliconctl.service siliconctl-resume.service siliconctl-reapply.timer siliconctl-reapply.service

%files -f siliconctl.lang -f silicon-control.lang
%license LICENSE ryzen_smu/LICENSE
%doc README.md docs/TECHNICAL.md ryzen_smu/UPSTREAM.md
%{_bindir}/siliconctl
%{_bindir}/silicon-control
%{_datadir}/applications/io.github.senseikiritof.SiliconControl.desktop
%{_datadir}/icons/hicolor/scalable/apps/io.github.senseikiritof.SiliconControl.svg
%{_metainfodir}/io.github.senseikiritof.SiliconControl.metainfo.xml
%{_unitdir}/siliconctl.service
%{_unitdir}/siliconctl-resume.service
%{_unitdir}/siliconctl-reapply.service
%{_unitdir}/siliconctl-reapply.timer
%{_presetdir}/80-silicon-control.preset
%{_udevrulesdir}/60-silicon-control.rules
%{_modprobedir}/silicon-control.conf
%{_datadir}/polkit-1/actions/io.github.senseikiritof.SiliconControl.policy
%config(noreplace) %{_sysconfdir}/xdg/autostart/siliconctl-notify.desktop
%dir %{_sysconfdir}/siliconctl
%dir %{_sysconfdir}/siliconctl/profiles
%dir %{_sharedstatedir}/siliconctl
%{_usrsrc}/ryzen_smu-%{drv_version}/
%ghost %config(noreplace) %{_sysconfdir}/dkms/framework.conf.d/ryzen-smu-akmods.conf

%changelog
* Tue Oct 13 2026 senseikiritof <tonifede98@gmail.com> - 0.4.1-1
- Documentation: the README for users (features, processors, installing from the release packages, usage, safety),
  the technical details in docs/TECHNICAL.md, also installed with the documentation

* Tue Oct 13 2026 senseikiritof <tonifede98@gmail.com> - 0.4.0-1
- The CPU check: on a CPU not verified yet (or on the generic backend) the Monitor offers "Check this CPU" (also
  in Preferences): hwtest, then a report of the CPU and its interfaces to send as a prefilled GitHub issue, copy
  or save; never the host name, the user or a serial number. On an AMD CPU whose PM table is not mapped the
  report can include it, only with the user's consent
- siliconctl report [pm]; a successful hwtest marks this machine as verified (the record follows the CPU)
- README: processors by vendor, adding a processor through the check

* Tue Oct 13 2026 senseikiritof <tonifede98@gmail.com> - 0.3.0-1
- Intel backend (expected: tested on simulated hardware only): PL1/PL2 through powercap (the MSR zone and
  its MMIO mirror), the temperature limit through the TCC offset, turbo through intel_pstate; warnings for
  a running thermald and for Raptor Lake without the 0x12B microcode; on laptops the limits the firmware
  rewrites are written again. No undervolt on Intel (set it in the BIOS)
- The stock value is always within the GUI's ranges (no phantom change on a 100 degC stock limit)

* Tue Oct 13 2026 senseikiritof <tonifede98@gmail.com> - 0.2.0-1
- Generic backend where the AMD one does not apply (Intel, ARM, the AMD families not in the table, HX laptops)
  or with the kernel parameter siliconctl.generic: FMax through cpufreq, boost, power profile, fans, the CPU
  temperature and the package power where the kernel has them; never an SMU command
- The GUI shows what the CPU reports (tiles, per-core columns, the Curves page); the Monitor shows its values
  as soon as it opens
- make check runs pyflakes

* Tue Oct 13 2026 senseikiritof <tonifede98@gmail.com> - 0.1.0-1
- Silicon Control: Ryzen Control 0.8.0 under the new name (helper siliconctl, GUI silicon-control,
  app id io.github.senseikiritof.SiliconControl); AMD Ryzen only so far
- Takes over from Ryzen Control: replaces the ryzen-control package and imports its settings, profiles,
  calibrations, crash-guard markers and trust rule (the run state too when it ran in the same boot); the
  login entry and GUI preferences at the first start of the GUI; ryzenctl.off still honoured
