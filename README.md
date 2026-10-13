# Silicon Control

Control of the processor on Linux — power limits, boost frequency, temperature limit, undervolt and fans — with
automatic per-chip calibration and protection after a crash: a GTK4 application with a small root helper, packaged
for Fedora, Debian/Ubuntu and Arch. The successor of [Ryzen Control](https://github.com/SenseiKiritof/Ryzen-Control).

- **AMD Ryzen**: per-core Curve Optimizer (the undervolt), power limits PPT/TDC/EDC (fast/slow PPT on the APUs),
  maximum boost frequency and temperature limit, through the processor's SMU.
- **Intel Core**: power limits PL1/PL2, temperature limit, turbo and maximum frequency, through the kernel's own
  interfaces (simulated hardware only so far); no undervolt.
- **Every other processor**: maximum frequency, boost, power profile, temperature and package power, where the kernel
  has them.
- **Fans** on motherboards with a Nuvoton nct67xx chip: how fast each fan follows the BIOS curve, and the curve
  itself; the AIO pump stays protected.
- **Modes** in one click — Default (BIOS), Quiet, Performance, and Eco, Auto, Boost calibrated on your processor with
  load tests (AMD processors with the Curve Optimizer) — or your own values; applied at every boot, never again after
  a crash.

> **Warning.** Experimental software that talks directly to the processor. Developed and tested on a single system
> (Ryzen 7 9800X3D, ASUS ROG STRIX X870E-H, Fedora 44). A Curve Optimizer that is too negative can reboot the system
> (no damage, but unsaved work is lost): read [Safety](#safety) before using it.

![Modes page: presets on the left, calibrated modes on the right](docs/screenshots/modes.png)

How it works — every processor family, the command line, the calibration, the safety rules, building and
development: [docs/TECHNICAL.md](docs/TECHNICAL.md).

## Processors

| Processors | Status |
|---|---|
| AMD Ryzen 7 9800X3D | **verified** |
| Other AMD Ryzen desktop: 9000, 7000, 5000, 3000, 2000, 1000 | expected |
| AMD Ryzen APUs: desktop 4000G/5000G/8000G; mini PCs and laptops with Ryzen 4000 … 8040, AI 300, AI Max | expected |
| Intel Core, desktops and laptops (Haswell … Arrow Lake, Core Ultra) | expected (simulated hardware only) |
| Every other processor: older AMD APUs, Steam Deck, AMD HX laptops, Threadripper, EPYC, ARM … | generic: frequency, boost, power profile, sensors |

**Verified**: a hardware check passed on a real machine. **Expected**: the same guarantees (never above the BIOS
values, every write read back, the crash protection), but nobody has tried it yet. What each family can do:
[Processors in detail](docs/TECHNICAL.md#processors). The fans depend on the motherboard, not on the processor.

### Adding your processor

While your processor is *expected*, or on the generic backend, the Monitor says so and offers **Check this CPU**
(also in Preferences → Hardware check). One check on your machine is enough to add or verify it:

1. Save your work: the check writes each function slightly away from its stock value for a moment, reads it back and
   restores it (where the Curve Optimizer is available, it lowers it by 3 steps on the last core); it takes a
   few seconds.
2. Run the check. On an AMD CPU whose PM table is not mapped yet you can include the table: it is read through the
   driver (an SMU command), so only if you agree.
3. In the report that opens, click **Open issue on GitHub**: the issue comes filled in, review it and submit it (a
   GitHub account is needed; otherwise **Save** the report and send it another way).

From the terminal: `sudo siliconctl hwtest`, then `sudo siliconctl report` (`report pm` adds the PM table where it is
offered). The report holds the CPU and its interfaces (versions, kernel, distribution, board and BIOS model, the last
hwtest), never the host name, the user or a serial number. After a successful check the Monitor says "Verified on this
machine"; the family becomes *verified* for everyone in a later release.

## Installation

Download the package for your distribution from the
[latest release](https://github.com/SenseiKiritof/Silicon-Control/releases/latest).

### Fedora

```sh
sudo dnf install ./silicon-control-*.noarch.rpm
```

A single package that does everything by itself: it builds the `ryzen_smu` module via DKMS for
every installed kernel (`dkms.service` rebuilds it at every update) and starts the service,
which loads the module and reads the baseline (no profile is applied).

**Secure Boot**: the module must be signed with a key enrolled in MOK. If the akmods key is
already enrolled on the system (typical with RPM Fusion's NVIDIA drivers), DKMS reuses it
automatically: no manual step. Otherwise the package says so at the end of the installation
and a one-time enrollment is needed — it is a Secure Boot limitation (it requires physical
confirmation at reboot), not something software can work around:

```sh
sudo mokutil --import /var/lib/dkms/mok.pub      # asks for a temporary password
sudo reboot                                       # MOK Manager: Enroll MOK → Continue → password
```

Check (all automatic, reversible, a couple of seconds):

```sh
sudo siliconctl status                        # BIOS values, "Baseline of this boot"
sudo siliconctl hwtest                        # writes and reads back every command close to the baseline, then restores it
```

### Debian / Ubuntu

Debian 13 or Ubuntu 24.04 and newer (libadwaita ≥ 1.5):

```sh
sudo apt install ./silicon-control_*_all.deb
```

DKMS builds `ryzen_smu` for the installed kernels — install the kernel headers (`linux-headers-amd64` on Debian,
`linux-headers-generic` on Ubuntu) — and the services are enabled, `siliconctl.service` started. Secure Boot: Ubuntu
signs DKMS modules with its own MOK key and asks to enroll it; on Debian `sudo mokutil --import /var/lib/dkms/mok.pub`
and a reboot, as on Fedora.

### Arch Linux

```sh
sudo pacman -U silicon-control-*.pkg.tar.zst
sudo systemctl enable --now siliconctl.service siliconctl-resume.service siliconctl-reapply.timer
```

The DKMS pacman hook builds the module: install `linux-headers` (or the headers of your kernel).

The deb and Arch packages are built, checked, installed and run in Debian 13, Ubuntu 24.04 and Arch containers; they
have not been used on real Debian, Ubuntu or Arch hardware yet. Other distributions, and building the packages
yourself: [Building](docs/TECHNICAL.md#building).

### Coming from Ryzen Control

Silicon Control replaces Ryzen Control (frozen at 0.8.x): its packages remove `ryzen-control`, and the first start of
`siliconctl.service` imports, once, its settings, profiles, calibrations, crash-guard markers and the "Stop asking for
the password" rule from `/etc/ryzenctl` and `/var/lib/ryzenctl`. Installed in the boot in which Ryzen Control ran (the
RPM and the deb start the service at once; on Arch `systemctl enable --now`), the run state of this boot comes too: the
profile already applied stays and is read back, no new baseline is taken over it. The GUI takes over the login entry
and its preferences when it first starts. `ryzenctl.off` still works as the escape hatch. Ryzen Control's directories
stay where they are: delete them by hand once everything works.

Before installing, quit Ryzen Control (window and tray icon) and do not run a calibration. The `ryzen_smu` module is
rebuilt once (about a minute).

## Usage

Open **Silicon Control** from the application menu (or run `silicon-control`). The first action that
needs root asks for the administrator password once per session; "Stop asking for the password"
in Preferences removes even that one. The screenshots below come from the fake backend
(`make screenshots`), so the values are illustrative.

**Monitor** — the CPU family and its active cores on top (with a note and **Check this CPU** when
the family has not been verified on hardware yet: see [Adding your processor](#adding-your-processor)), Tctl and per-core temperature, PPT and TDC against their limits,
MHz, voltage and Curve Optimizer per core, a 60 s graph of Tctl (blue, °C) and PPT (orange, W, its
limit dashed), fan speeds and power mode. Every per-core view lists only the active cores.

![Monitor page](docs/screenshots/monitor.png)

**Modes** — one click switches between stock values (Default), the fixed presets (Quiet,
Performance), the modes calibrated on this CPU (Eco, Auto, Boost) and your own values (Custom).
Every profile lists its values, fans included: green is more conservative than stock, red more
aggressive, grey unchanged. Boost needs "Allow beyond the stock values" (Preferences): until then
it is shown dimmed, and hovering it says why.

**Calibration** — "Calibrate…" on Auto or Boost measures this CPU: the Curve Optimizer limit of
every core under load, a final pass on all cores, then the performance/watt knee (Auto) or the
gain over stock (Boost), with the remaining time and the real voltage measured per core. Eco
reuses the undervolt that Auto or Boost validated, so it is usually ready at once. At the end you
choose: discard, save, or save and apply. Save your work first: an unstable level can reboot the
PC (see "Safety").

![An Auto calibration on the fake backend, sped up](docs/screenshots/calibration.gif)

**CPU** and **Curves** — the same values by hand: PPT/TDC/EDC, FMax, Tjmax and power mode, then
the Curve Optimizer for all cores or one by one. "Apply now" writes them (each value is read
back), "Save to profile…" keeps them.

![CPU page](docs/screenshots/cpu.png)

![Curves page](docs/screenshots/curve.png)

**Fans** — the BIOS SmartFan stays in charge: you only change how fast each fan follows its
curve (rise/fall) and the curve points, with the estimated rpm. Pumps and non-controllable
channels are protected; the pump can only be left to the BIOS (recommended), capped, or set to a
fixed speed (never below 50 %). Channels with an unknown role are grouped in a collapsed
"Unknown channels" section at the end of the page (listed in Monitor only while it is open); its
state is remembered.

![Fans page](docs/screenshots/fans.png)

**Preferences** — "Apply at startup" re-applies the selected profile at every boot and resume,
never after a crash; choosing Default leaves it on (nothing is applied until you pick another mode), the
crash warning's "Stay on Default" turns it off; "Start Silicon Control at login" opens the window at every login; "Stop asking
for the password" writes the polkit rule described in "Safety"; "Allow beyond the stock values"
raises the PPT/TDC/EDC and FMax ceilings (unlock); "Hardware check" writes and reads back one
value per command, restores the baseline, then shows the CPU report to send.

![Preferences page](docs/screenshots/preferences.png)

**System tray** — Preferences → "Icon in the system tray" (or `silicon-control --tray`): an icon in
the panel, bottom right (KDE Plasma natively; on GNOME it needs the AppIndicator extension). Left
click opens the window; the right-click menu has the modes (the active one ticked; a calibrated mode
not calibrated yet, or Boost without the unlock, greyed out), the custom calibrations, "Apply at
startup", "Open Silicon Control" and "Quit"; after a crash the choice Reactivate / Stay on Default
comes first and the icon asks for attention. The tooltip shows Tctl (read without root) and, once
`siliconctl serve` runs anyway, the PPT. With the tray on, closing the window keeps the icon, and
"Start minimized to the tray icon" (on by default) decides what "Start Silicon Control at login" opens:
only the icon — no password until you pick something from the menu, then once per session as for
the window — or the window as well.

### Command line

The same functions with `sudo siliconctl` (the full reference, with profiles, fans and calibrations:
[Command line](docs/TECHNICAL.md#command-line)):

```sh
sudo siliconctl status                 # current state and the BIOS values (the baseline)
sudo siliconctl preset quiet           # creates the Quiet mode's profile from the BIOS values (also performance)
sudo siliconctl apply quiet            # applies a profile now
sudo siliconctl use quiet && sudo siliconctl autostart on   # applies it at every boot and after resume
sudo siliconctl default                # everything back to the BIOS values, no mode selected
sudo siliconctl hwtest                 # reversible test of every function
sudo siliconctl report                 # the CPU report to send (see Adding your processor)
```

### Laptops

In a laptop the firmware owns the power limits, with its own values for AC and for battery. Silicon Control writes
the processor's values only on the power source the laptop booted on and, with "Apply at startup", writes the limits
again when the firmware changes them, until the firmware keeps overriding them. On AMD laptops only the APUs get the
AMD backend (the HX models get the generic one). Nobody has tried it on a real laptop yet: [Laptops](docs/TECHNICAL.md#laptops).

## Safety

- No voltage command, ever: every value is a limit the firmware keeps enforcing, never above the BIOS values read at
  boot (beyond them only power limits and boost frequency, and only after "Allow beyond the stock values"), and every
  write is read back.
- After a crash with a profile active, the profile is not applied again at boot: a notification at login asks whether
  to reactivate it or stay on the BIOS values.
- During a calibration the motherboard's watchdog, where there is one, resets a frozen PC by itself, and the
  calibration resumes with that step marked unstable.
- Escape hatches, for one boot (in GRUB press `e` and add it to the kernel line): `siliconctl.off` (nothing starts,
  the driver is not loaded) or `siliconctl.generic` (only the kernel's interfaces, never the SMU).
- "Stop asking for the password" lets every program run as your user change limits, Curve Optimizer and fans
  without authentication (within the same ceilings); `sudo siliconctl trust off` removes it.
- Nothing is permanent: every value lasts until the next reboot, which brings back the BIOS values (then "Apply at
  startup" applies your mode again, never after a crash).

The complete rules: [Safety in detail](docs/TECHNICAL.md#safety).

## Language

The UI follows the system locale (gettext), Italian included. To add a translation, create
`po/<domain>/<lang>.po` for the domains `siliconctl` (helper/CLI) and `silicon-control` (GUI);
the catalogs are compiled at install by `make`.

## License

GPL-3.0-or-later. The vendored driver in `ryzen_smu/` stays GPL-2.0 (included in the same
package, RPM license `GPL-3.0-or-later AND GPL-2.0-only`); see `ryzen_smu/UPSTREAM.md`.
Technical references: ryzen_smu (amkillam), ZenStates-Core (irusanov), gnr-smu (Kyworn,
measurements on the 9800X3D).
