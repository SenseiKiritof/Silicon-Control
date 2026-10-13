# Plan: "Ryzen Control" — Ryzen Master-style control on Linux (9800X3D)

Copy in the project: `~/Documenti/Progetti/Personali/Ryzen Control/docs/plans/2026-10-09-ryzen-control.md`
Revision 2 (2026-10-09): installation via packages (RPM + cross-distro base), no `install.sh`.
Revision 3 (2026-10-09): Auto mode; personal git repo, step-by-step development with verification and commit.
Revision 4 (2026-10-09): safety review (crash-guard rewritten, what is never touched, pump
protection); fans before the GUI.
Revision 5 (2026-10-09): zero manual steps where possible — the `%post` of the -dkms package
reuses the akmods key if already enrolled in MOK (dkms drop-in created only in that case,
`%ghost`), forced rebuild, `ryzen-control` starts the service at installation; `ryzenctl
hwtest` automates the reversible verification on hardware. Only what Secure Boot imposes stays
manual (MOK enrollment at reboot, if no key is already enrolled) plus the crash test.
In phase 2 `ryzenctl fan enable` will set the kernel parameter by itself (grubby / /etc/default/grub)
with explicit confirmation, reversible with `fan disable`.
Revision 9 (2026-10-10): **Boost** becomes calibrated (pushed CO, limits and FMax at the ceilings, measured
gain), the static factory + power at maximum one is called **Performance**; the CO limit search
is single and shared (−40, saved in `co_limits.json`, reused), each mode applies its own margin
(Eco +5, Auto/Boost +3); immediate interruption (`serve` with a separate reader, flag +
stress-ng terminated); per-core voltage sampled at every level (mV per step measured).
Revision 10 (2026-10-10): phases 5 and 6 swapped — the tray icon (phase 5, tag v0.5.0) precedes the deb/Arch packages (phase 6, tag v0.6.0).
Revision 11 (2026-10-10): new phase 5 — support for all Ryzen processors (FAMILIES table, per-family gate, dynamic cores); tray → phase 6 (v0.6.0), deb/Arch → phase 7 (v0.7.0).
Revision 12 (2026-10-10): project documentation, source comments and UI strings switched to English; UI localized with gettext (Italian catalog).
Revision 20 (2026-10-13): phase 8, APUs and laptops, after a research agent (RyzenAdj, ZenStates-Core, UXTU, amd-pmf). First finding, fixed at once: the driver reports the HX laptop CPUs (Dragon Range, Fire Range) as Raphael and Granite Ridge, so a system battery (not a device battery such as a wireless mouse) now refuses every family not marked mobile. Step 25: desktop APUs and mini PCs — fast/slow PPT (MP1 0x15/0x16), Tctl (0x19), TDC/EDC (0x1A/0x1C) where the table is mapped, read back from the PM table at RyzenAdj's offsets for explicit versions; STAPM read only; no CO (no verified readback on any APU), no FMax; Quiet 60 % of fast/slow with boost off, Performance. Step 26: laptops — the power source recorded with the baseline and writes only on that source, `power` applied before the limits (amd-pmf rewrites them on profile changes), `ryzenctl reapply` from a udev rule on power-supply changes, the resume unit and a timer while a mobile profile is active, giving up after repeated firmware overrides.
Revision 21 (2026-10-13): step 26 implemented by an agent and reviewed. Departures from rev. 20: the udev rule uses `RUN+="systemctl --no-block start"` (SYSTEMD_WANTS acts only when a device first appears); the timer (every 10 s, its service skipped by `ConditionPathExists` on `/run/ryzenctl/reapply-wanted` and quiet in the journal) runs on every machine, the flag exists only on a laptop with Apply at startup and a profile changing a limit; a limit set by hand, or a save of the selected profile, removes it until the next apply (so `reapply` never reverts manual values nor writes a profile that was only saved); the give-up is 3 corrections within 120 s; Default on the other power source writes only fans, power profile and boost. Fixes in the review: the save rule above, a `%triggerun` that presets the new timer on RPM upgrades from < 0.8.0, and the watchdog selftest feeding `serve` one request at a time (an abort read early raced `autotune start`, which clears its flag: a flaky test, not a bug, the abort request itself still runs in order). Version 0.8.0.
Revision 22 (2026-10-13): user request — Default chosen by hand no longer turns "Apply at startup" off (with no profile the boot applies nothing; the next mode chosen is applied at startup again without switching it back on); the crash warning's "Stay on Default" (window and tray) still turns it off explicitly, and the tray lets it be turned off while on Default.
Revision 19 (2026-10-13): phase 7. The deb and Arch packages are thin wrappers of `make install`, and they are tested after all: podman is on the development machine, so `packaging/build-deb.sh` and `build-arch.sh` build and check them in containers (`make deb`, `make arch`, two jobs of the release workflow that attach them to the GitHub release); the install test (dependencies, maintainer scripts, DKMS registration, selftest of the installed package, removal) ran in Debian 13, Ubuntu 24.04 and Arch containers. Real hardware on those distributions: untested.
Revision 18 (2026-10-13): phase 6, the tray icon (step 22). As planned, with three choices: the custom calibrations are listed in the menu with the modes; the icon asks for attention only after a crash (a Tctl above the Eco target is normal under load and would keep it lit); the `ryzenctl-notify` autostart stays (the tray is optional), the crash choice is also the first menu entry.
Revision 17 (2026-10-13): custom calibrations (user request: keep the working Auto while trying other parameters): `autotune start eco|auto|boost name=<profile>` calibrates from a base mode and saves the result under its own name, never over eco/auto/boost (their names refused), and its own CO search is never written over the shared `co_limits.json` the three modes reuse; listed in `settings.json` (`calibrated`: base mode, time), Boost's unlock rule for those based on Boost, `profile delete` forgets them. GUI: a "Custom" row in the Calibrated column (Calibrate… = base + name + the usual dialog; one sub-row per saved custom calibration: apply, Verify…, delete). Steps 21c (single-core phase, watchdog, verify) merged.
Revision 16 (2026-10-13): three research agents (Ryzen 5000; Ryzen 1000–3000 without CO; Windows tools). (1) Vermeer added as expected: CO MP1 0x35 / readback MP1 0x48 (used on real 5800X3D/5600X by svenlange2 ruv.py and linux-corecycler; ZenStates' RSMU 0x7C stays out, "Not sure"), range −30..+30 (per-family `co_range`), PPT/TDC/EDC/Tjmax RSMU 0x53–0x56 (Ryzen Master's), limits read back from the header of the four PM tables 0x3808xx/0x3809xx (ryzen_monitor, explicit `pm_versions`), Zen 3 CCD fuses (enabled = not down, ZenStates CcdMapFromDown) always read: an 8-core part can sit on the second CCD. No FMax command on Zen 3: FMax optional everywhere (Auto knee on the PPT alone). (2) Matisse expected with the limits only (RSMU, PM tables 0x240803/0x240903); Summit/Pinnacle Ridge with no SMU command (no PM table in ryzen_smu); new `boost on|off` (cpufreq, read back) in profiles and baseline, Quiet turns it off on CPUs without CO; Tdie instead of Tctl where k10temp has it (X parts with an offset); P-state VID undervolting excluded (voltage write). (3) Board-limit guard: baseline limits above the unlock ceilings are the motherboard's (PBO "Enabled") → Quiet/Eco on AMD's 65 W Eco mode values, Auto refused. (4) From CoreCycler/Ryzen Master: single-core phase in the final pass (user choice, default on), hardware watchdog armed during a calibration under `serve`, `autotune verify` (hours of per-core tests on a saved profile, only failing cores raised). Bugs found by the research and fixed: the second-CCD presence bit in the fuse map (a 9600X saw a phantom CCD), per-core PM table values read by logical index instead of physical slot.
Revision 15 (2026-10-12): CPUs with disabled cores get the per-core CO back: the enabled slots of each CCD come from the CCD and core fuses (ZenStates-Core GetTopologyFuses addresses for Zen 4/5), read with the driver's `smn` file — read only (4-byte write = read), only at those addresses, used only if they match the sysfs topology; complete CCDs need no read (the 9800X3D path is unchanged). The GUI shows and uses only the active cores (step 20).
Revision 14 (2026-10-12): phase 5 step 19 after reading ZenStates-Core. (1) The SMU core mask addresses the physical core slot of the CCD, which ZenStates-Core reads from the fuses; Linux numbers only the enabled cores, so on CCDs with disabled cores (9600X, 9900X, 7600X…) a per-core CO could reach another core and the readback would not notice: the per-core CO is refused there (`co_support`), until the fuse map is read. (2) Raphael added with the Zen4Settings IDs (the same Zen 5 inherits, verified here): CO and FMax; PPT/TDC/EDC/Tjmax refused because ZenStates-Core has no map of the limits in the PM table (only clocks and voltages). (3) Vermeer and Matisse not added: no reliable CO readback on Zen 3 (0x7C "Not sure"), no FMax set on Zen 2/3, no CO on Zen 2, no PM map; they need another verified source (e.g. ryzen_monitor's PM tables) and a `hwtest`.
Revision 13 (2026-10-11): user feedback on hardware. Eco no longer has its own calibration (FMax sweep for a Tctl target): it is the Eco preset (limits ×0.55/0.63/0.83, FMax −400, Tjmax 80, quiet fans) with the CO validated by Auto/Boost — successful final passes are recorded (`final_passed`) and a covering one makes Eco instant, otherwise the final pass, on a fresh install the full search; the three calibrated modes use the same margin (+3). Boost only with the explicit unlock (ceilings 230 W / 160 A / 230 A, FMax +200). A profile is the baseline plus its own lines (`with_stock`): every mode shows and applies its fans, switching never leaves another mode's curve. Fan level "moderate" = BIOS curve +10 % with full speed at 100 °C (Auto and Boost default). GUI: Preferences tab, readable Monitor graph, unknown fan channels in a collapsed section, calibration window with the progress pinned on top; README screenshots and GIF from `make screenshots`.
Revision 8 (2026-10-09): new **Eco** mode (Quiet stays as a preset) with a calibrated conservative undervolt; calibrations as a
step machine in ryzenctl (`autotune`), the GUI drives it with progress and resume after crash.
Revision 7 (2026-10-09): fan curve per mode (Eco from the target, Auto moderate step).
Revision 6 (2026-10-09): phase 1 verified on hardware and tagged `v0.1.0`; a single installation
package (DKMS driver inside `ryzen-control`); new phase 6: system tray icon with quick commands.

## Context

User goal: manage from Linux Curve Optimizer, Curve Shaper, PBO limits, FMax/Tjmax and fans
with a complete GUI, Default/Eco/Auto/Boost modes, automatic calibration and CO auto-tuning.
Main need: a quieter AIO (today Tctl jumps up suddenly and the fans go to maximum). Explicit
requirements:
- after a crash the profile does NOT reapply by itself: the user decides;
- Default = return to the base values read from the CPU (baseline);
- limits ≤ stock; beyond stock only with explicit unlock and warning;
- GTK4/libadwaita, compatible with other distros;
- Auto mode = efficiency/performance optimised automatically; Boost = raw power only;
  Eco = silence; Default = factory values;
- installation with a classic package (RPM) and a viable path for every distro;
- nothing that can damage the hardware; fans before the GUI.

Detected system:
- Ryzen 7 9800X3D (Granite Ridge, fam 0x1A mod 0x44), 1 CCD, 8 cores; `cpuN`/`cpuN+8` = physical
  core N; best cores (prefcore 196) 1 and 2, worst 7.
- ASUS ROG STRIX X870E-H GAMING WIFI7 **HATSUNE MIKU EDITION**, BIOS 0405, root complex `1022:14d8`.
- Fedora 44, kernel 7.2.8, **Secure Boot enabled**; akmods MOK key already enrolled (NVIDIA).
  `dkms` 3.4.3 installed, `dkms.service` enabled; `rpm-build` + `rpmdevtools` present.
- Root filesystem btrfs (commit every 30 s: the crash-guard markers must be `fsync`-ed).
- Sleep `deep` (S3). Active power profile `performance`.
- Fans: no hwmon fan/pwm. `nct6775` does not list the board and the DMI name with the
  "HATSUNE MIKU EDITION" suffix makes `asus-ec-sensors` fail too. No USB AIO → pump/fans on the
  board headers (Nuvoton Super I/O, SmartFan IV curves programmed by the BIOS).
- RAPL available: `/sys/class/powercap/intel-rapl:0` (`package-0`, `core`), root-only read.
- Installed: Python 3.14, PyGObject 3.56, GTK 4.22, libadwaita 1.9. Not installed: stress-ng.

Research done (sources in the scratchpad): `ryzen_smu` driver (amkillam, supports Granite Ridge,
kernel 7.2+ fix in d298366); ZenStates-Core `Zen4Settings.cs`/`Zen5Settings.cs` (reference SMU
command IDs); gnr-smu (PM table 0x620105 map measured on a 9800X3D, dangerous MP1 IDs);
RyzenSMUDebug-LINUX (FMax 0x6E/0x70 tested on Granite Ridge). No existing tool covers
persistence + crash-guard + limits + Curve Shaper + fans: a small app is written, only the
measured data is reused.

## Safety review (rev. 4)

Question: can it damage the hardware? No, by construction:
- Real damage on AM5 comes from fixed voltages (SoC/VDDIO/VDDG, manual VID in OC mode).
  This program **sends no voltage command** and never enters OC mode: RSMU 0x5D `EnableOcMode`,
  0x61 `SetOverclockCpuVid`, 0x5B `SetPBOScalar`, the CLDO/SoC ones and the `smn` file stay out
  of the allowlist. It does not touch FCLK/UCLK/memory.
- Everything it writes is a *limit* that the firmware keeps enforcing: PPT/TDC/EDC and Tjmax
  only ≤ baseline (above stock only with explicit unlock, ceilings 230 W/160 A/230 A and Tjmax
  ≤ baseline anyway → the thermal protection always stays active), FMax ≤ baseline (+200 MHz
  with unlock, like the BIOS "Boost Override"), CO/Shaper −50..+30 (negative CO = undervolt:
  can only cause instability; positive stays within the firmware's voltage limits).
- Possible errors: crash/reboot for a CO that is too negative (handled by the crash-guard), SMU
  refusing (0xFD/0xFE, no effect), SMU freeze for a wrong ID (excluded by the allowlist; it
  would only require a reboot).

Problems found in rev. 3 and fixed here:
1. **Possible boot loop**: `dirty` was created *after* the apply; a crash during the apply at
   boot left no trace → reapplied at every boot. Now the markers precede every write and are
   `fsync`-ed (btrfs).
2. **Incomplete escape hatch**: the driver autoloads via PCI ID even with `ryzenctl.off`.
   Now the package blacklists the autoload and only the service loads the module.
3. **Corrupted baseline** by `systemctl restart` with an active profile. Now captured only once
   per boot and never if `active` exists.
4. **AIO pump**: a slowed-down pump channel is the only real risk on the fan side. Linux only
   sees `pwm1..N` without names and RPM alone does not tell them apart (pumps 2000–3500, fans
   500–3000). Now the role is assigned by an automatic physical test (`fan autodetect`, see
   "Fans"), the user can only demote a channel, never promote it to "ventola" (fan); everything
   that is not "ventola" is read-only.
5. **Failed readback**: now one retry, then restore of the baseline value of that parameter,
   then error (protects against races with other SMU tools).
6. **PM table absent** (new AGESA): baseline of the limits impossible → PPT/TDC/EDC/Tjmax
   refused (fail closed), CO/FMax/Shaper ok (readback via RSMU).
7. Atomic state-file writes (`tmp` + `os.replace` + fsync): a crash leaves no corrupted
   JSON/profiles; an unreadable profile is not applied.
8. Auto-tuning: added a low-load phase (CO instabilities show up mostly at idle), combined
   final pass, stress-ng run as the user, "save everything" warning.

## Architecture (3 code files + vendored driver + packages)

```
ryzen-control (GTK4/Adw GUI, user) ──pkexec──▶ ryzenctl serve (root, validates EVERYTHING)
                                                 ├─ /sys/kernel/ryzen_smu_drv/*  (SMU)
CLI: sudo ryzenctl …  ───────────────────────────┤─ /sys/class/hwmon/nct67xx/*   (fans)
systemd: ryzenctl.service (boot/stop), -resume ──┘─ /etc/ryzenctl, /var/lib/ryzenctl
```

- `ryzenctl` (Python stdlib, ~400 lines): the only privileged point = trust boundary.
  Same command grammar for CLI, profile files and the `serve` protocol (one JSON-array line per
  request → one JSON line as reply, over a pipe: only the parent process can talk to it).
- `ryzen-control` (Python + PyGObject GTK4/libadwaita ≥1.5, ~700 lines): runs as the user,
  starts `pkexec ryzenctl serve` only once (one password prompt per session). Reads directly
  (read-only) `crashed`, `settings.json`, profiles, baseline; uses `serve` for writes and
  SMU/RAPL reads. stress-ng is launched by the GUI as the user; `serve` runs it only inside
  `fan autodetect`, with fixed arguments.
- `ryzen_smu/`: vendored upstream driver (`git subtree`, commit d298366) + one local change in
  `smu.c`: PM table sizes 0x621101/0x621102 (0x724) and 0x621201/0x621202 (0x994) from
  ZenStates-Core `PowerTable.cs`, for more recent AGESA.
- No test framework: `ryzenctl selftest` with a fake SMU backend (monkeypatch of 2 functions,
  root path from the env `RYZENCTL_ROOT`) covers encodings, validation, profiles, baseline,
  crash-guard. `--mock` in the GUI uses the same backend.

### Packaging

`Makefile` = the only source of the layout (`install`/`uninstall`/`dkms`, honours `DESTDIR`/`PREFIX`;
variable `APPID=org.ryzencontrol.RyzenControl`). Every package format is a thin wrapper that
calls `make install DESTDIR=…`.

Installed layout:
```
/usr/bin/ryzenctl, /usr/bin/ryzen-control
/usr/lib/systemd/system/ryzenctl.service, ryzenctl-resume.service
/usr/lib/modprobe.d/ryzen-control.conf              (blacklist ryzen_smu: no autoload, the service loads it)
/usr/share/polkit-1/actions/<APPID>.policy          (auth_admin_keep, exec.path=/usr/bin/ryzenctl)
/usr/share/applications/<APPID>.desktop
/usr/share/icons/hicolor/scalable/apps/<APPID>.svg
/usr/share/metainfo/<APPID>.metainfo.xml            (AppStream: visible in Discover/GNOME Software)
/etc/xdg/autostart/ryzenctl-notify.desktop          (crash notification at login)
/etc/ryzenctl/                                      (config, %config(noreplace))
/var/lib/ryzenctl/                                  (state: baseline, dirty, active, crashed)
/usr/src/ryzen_smu-<ver>/                           (driver source + dkms.conf, -dkms package)
```

1. **RPM — `packaging/ryzen-control.spec`** (Fedora/RHEL/openSUSE), `BuildArch: noarch`,
   one tarball from the repo, **a single package** `ryzen-control` (rev. 6, user request;
   `License: GPL-3.0-or-later AND GPL-2.0-only` for the included driver; `Obsoletes/Provides:
   ryzen-smu-dkms` for those who installed 0.1.0-1…4):
   - app: `Requires: python3 ≥ 3.9, python3-gobject, gtk4, libadwaita ≥ 1.5, polkit, systemd`;
     `Recommends: stress-ng, libnotify`. The systemd preset enables the services (they apply
     nothing without autostart); `%post` starts the service.
   - driver: copies `ryzen_smu/*.c *.h Makefile dkms.conf` into `%{_usrsrc}/ryzen_smu-%{version}`
     replacing `@VERSION@`/`@CFLGS@`; `Requires: dkms, kernel-devel, gcc, make`; `%post`:
     akmods key drop-in if enrolled, `dkms add/build/install --force --rpm_safe_upgrade`
     (non-fatal), Secure Boot warning only if no key is enrolled; `%preun`: `dkms
     remove --all`.
   - Build: `make rpm` locally or COPR (COPR-ready spec: noarch, no network at build time
     thanks to the vendored driver).
2. **Debian/Ubuntu — `packaging/debian/`**: `control` (1 binary), `rules` (`dh $@ --with
   dkms`), `ryzen-control.dkms`, `install`, `changelog`, `copyright`.
3. **Arch — `packaging/PKGBUILD`**: a single `package()`, dkms via pacman hook.
4. **Any other distro**: `sudo make install && sudo make dkms` (last resort documented in the
   README).

deb and PKGBUILD cannot be tested on this machine: minimal wrappers marked "untested".

Secure Boot with DKMS 3.4.3: signs by default with `/var/lib/dkms/mok.key`/`mok.pub` (created if
missing). A single enrollment: `mokutil --import /var/lib/dkms/mok.pub` + reboot.
Alternative on this machine (zero new MOKs): drop-in `/etc/dkms/framework.conf.d/akmods.conf`
pointing to the akmods key — documented, not set by the package.

### SMU commands (strict allowlist, nothing else can be sent)

| Function | Mailbox | ID | Argument | Verification (readback) |
|---|---|---|---|---|
| Per-core CO | MP1 | 0x35 | `core<<20 \| (m & 0xFFFF)` | RSMU 0xD5 arg0=`core<<20`, low16 signed |
| PPT / TDC / EDC | MP1 | 0x3E / 0x3C / 0x3D | W·1000 / A·1000 | PM d[2] / d[8] / d[63] |
| FMax | RSMU | 0x70 set, 0x6E get | MHz | 0x6E |
| Tjmax | RSMU | 0x59 | °C | PM d[10] |
| Curve Shaper | RSMU | 0xA6 set, 0x84 get | `hi<<24\|med<<16\|lo<<8\|0x80\|tier` | 0x84 (5 args = 5 tiers) |
| PM table | (driver) | — | `pm_table` file | — |

Sources: CO 0x35 validated with readback on a 9950X3D (same family); PPT/TDC/EDC validated with
readback on the 9800X3D itself; FMax/Tjmax/Shaper from ZenStates-Core (Shaper never tried on
Linux: only the 0x84 readback confirms it). MP1 0x58–0x6F freezes the SMU on the 9800X3D and MP1
0x10 turns off the display: they are never sent. RSMU 0x59/0x6E are ZenStates production
commands on Zen 4/5 (the "forbidden" range concerns MP1 only).

Transaction rules:
- Gate: `codename` = Granite Ridge, otherwise total refusal (phase 5: codename in `FAMILIES`,
  each family with its own allowlist; outside the table total refusal). Never writes to `smn`.
- Every transaction under `flock(/run/ryzenctl.lock)`: the driver's `smu_args` is global.
  Documented: do not use other SMU tools (gnr-smu, ryzen_monitor) at the same time.
- Every write → readback. Mismatch → one retry → if still different, rewrites the baseline
  value of that parameter → error. Reply 0xFD (prerequisite) → suggests PBO = Advanced in the
  BIOS.
- PM values read only if `pm_table_version>>16 == 0x62` (`# ponytail:` family heuristic,
  full map only for 0x620105). PM table absent → PPT/TDC/EDC/Tjmax refused (no baseline for
  them), CO/FMax/Shaper ok.
- If CO via MP1 0x35 does not come back at readback → RSMU 0x6 (ZenStates) is considered, no
  automatic fallback.
- Applying a profile: stops at the first error (the lines already applied are individually
  within the limits), reports the failed line.

### Validation (constants at the top = calibration knobs)

- CO and Shaper −50..+30. FMax 3000..baseline (+200 if unlocked). Tjmax 60..baseline (max 95).
- PPT ≥45 W, TDC ≥30 A, EDC ≥45 A (never 0: PPT 0 locks at 606 MHz). Ceiling = baseline (stock);
  with unlock 230 W / 160 A / 230 A. Writing exactly the baseline value is always allowed.
- Without a fresh baseline of this boot: no CPU write (fail closed).
- Unlock: `ryzenctl unlock on` prints a warning; in the GUI switch + `Adw.AlertDialog`.
- Fans: a channel can be modified only if `fan autodetect` classified it "ventola" (fan) in
  `settings.json` ("pompa", "non controllabile", "sconosciuto" → refusal; by hand one can only
  demote); step up/down 0..60000 ms; curve with increasing temperatures, non-decreasing pwm,
  minimum pwm ≥ 77 (30 %), last point pwm 255 at ≤90 °C; `pwmN_enable` never changed, except
  in the two tests (`autodetect`, `identify`) which restore it in `finally`.
- Profile names only `[a-z0-9_-]`. State files written atomically.

### Profiles, baseline, modes

- Profile = file of command lines: `/etc/ryzenctl/profiles/<name>.conf` (`co -15 -10 …`,
  `fmax 4800`, `ppt 88`, `power balanced`, `fan 2 step 10000 5000`, `fan 2 curve 40:60 …`).
  `apply` = run every line. Saving from the GUI: every line validated (dry-run) first.
- `/etc/ryzenctl/settings.json`: active profile, autostart, unlock, fan channel role/name.
- Baseline `/var/lib/ryzenctl/baseline.conf` in the same format: captured **once per boot,
  before applying** (SMU = BIOS values), never if `active` exists; guard
  `/run/ryzenctl/baseline-done`. Contains CO, FMax, PPT/TDC/EDC/THM, Shaper, power profile,
  fan settings. Follows any BIOS changes.
- Modes (all static: the dynamic behaviour is already done by PBO in the SMU, no daemon):
  - **Default**: `apply baseline`, removes `active`, disables autostart.
  - **Eco** (formerly Eco): conservative CO, FMax, limits and fans from the Eco calibration (see
    below); until calibrated, preset ×0.55/0.63/0.83, FMax −400, Tjmax 80, fans 10 s /
    5 s. Goal: silence and temperatures with a prudent undervolt.
  - **Auto**: PPT/TDC/EDC and FMax from the Auto calibration (performance/W knee point of
    *this* CPU), CO from auto-tuning, Tjmax baseline, `power balanced`. Until calibrated:
    AMD 105 W eco preset (142/110/170), FMax baseline. Goal: performance per watt.
  - **Performance** (fixed preset, rev. 9): factory limits, FMax and Tjmax, `power performance`,
    BIOS fans.
  - **Boost** (calibrated, rev. 9): CO = measured limit + 3, limits and FMax at the allowed
    ceilings (factory or unlock), `power performance`, BIOS fans; at the end of the calibration
    measures the MT/ST gain against the factory. Goal: raw power.
  - **Custom**: values set by hand in the pages.
- `power`: power profile via D-Bus `net.hadess.PowerProfiles` (`busctl`, works with
  power-profiles-daemon and tuned-ppd); if absent, EPP write in sysfs.

### Crash-guard (explicit requirement) — state machine

Markers in `/var/lib/ryzenctl/`, each written with `fsync` of file and directory:
- `dirty`: "this boot has not yet ended cleanly".
- `active`: "in this boot a CPU state different from the baseline was written".
- `crashed`: `{time, profile}` — the previous boot ended badly with an active profile.

```
ryzenctl boot   (ryzenctl.service, oneshot RemainAfterExit, After=dkms.service,
                 ExecStartPre=-/sbin/modprobe ryzen_smu, ConditionKernelCommandLine=!ryzenctl.off)
  1. if dirty ∧ active            → writes crashed {time, profile}
  2. rm active
  3. writes dirty                 (BEFORE any SMU write)
  4. baseline: only if /run/ryzenctl/baseline-done is missing; failed → no CPU writes
  5. fans: applies the fan part of the profile if autostart (they cannot cause crashes)
  6. CPU: only if autostart ∧ ¬crashed; every non-baseline line writes active (fsync) and THEN the SMU

ryzenctl shutdown (ExecStop, clean shutdown/reboot)            → rm dirty
runtime write (CLI or serve) of a non-baseline value           → active before the SMU
ryzenctl-resume.service (After=/WantedBy= of the sleep targets) → reapplies if autostart ∧ ¬crashed
Default                                                        → apply baseline, rm active, no profile (rev. 22: autostart kept)
GUI "Reactivate"                                               → rm crashed, autostart on, apply
GUI "Stay on Default"                                          → rm crashed, Default, autostart off
```

Scenarios verified on the state machine:
- Crash at steady state with an active profile → dirty ∧ active → `crashed`, no apply,
  notification at login (`ryzenctl notify` from XDG autostart), `Adw.Banner` in the GUI with
  **Reactivate** / **Stay on Default**.
- Crash *during* the apply at boot (CO unstable at startup) → dirty already written → at the
  next boot `crashed`. No loop: every new attempt requires a click on "Reactivate".
- Crash in a boot where nothing was applied (profile disabled, or `crashed` already present)
  → `active` absent → not reported as our fault; the previous `crashed` stays until the user
  decides.
- Crash before the service starts (other cause) → dirty from the previous boot → false
  positive in the safe direction (profile not applied, one click to reactivate).
- Shutdown with the power / reset button → treated as a crash → safe direction.
- Suspend: with S3 the SMU settings return to the BIOS ones → `-resume` reapplies; failed
  resume → reset → dirty ∧ active → `crashed`.
- `systemctl restart ryzenctl` with an active profile → baseline not recaptured (/run guard +
  `active`), no corruption of the ceiling.
- Total escape hatch: in GRUB `e` + `ryzenctl.off` → the service does not start and, thanks to
  the blacklist, the module is not loaded at all. The leftover `dirty` triggers `crashed` at the
  next normal boot.
- Crash during auto-tuning: the value under test is written (fsync) in the GUI state before
  the SMU; `active` is set → `crashed`; the GUI cross-checks `crashed.time` with its own
  state and marks the step as unstable.
- Driver that does not build for a new kernel → `boot` skips the CPU part with a message, the
  fans are applied anyway; it does not fail.
- Single warning in the auto-tuning and unlock windows: possible sudden reboots, save your
  work (data loss, not damage).

### GUI `ryzen-control` (Adw.ViewStack, 5 pages)

1. **Monitor** (1 s polling, `telemetry` command): Tctl/Tccd1 (k10temp) + 60 s graph
   (cairo), PPT/TDC value vs limit (LevelBar), MHz and CO per core, temperature per core (only
   0x620105), fan RPM.
2. **Modes**: Default/Eco/Auto/Boost/Custom, "Apply at boot" switch, unlock switch,
   crash banner, buttons **Calibrate Eco**, **Calibrate Auto** (max loss % slider) and
   **CO auto-tuning** with progress, log and results table.
3. **CPU**: PPT/TDC/EDC, FMax, Tjmax, power profile (Adw.SpinRow limited to the ceilings).
4. **Curves**: per-core CO (8 SpinRow + "all"), Curve Shaper 5 tiers × 3 temperatures.
5. **Fans**: **Detect roles** button (autodetect, with progress and reason per channel: ΔT,
   RPM), channels with RPM, role and name, step up/down, curve points (spin + preview) only on
   "ventola" channels, Identify; if nct6775 is absent → instructions with ready-made commands
   (kernel parameter + `ryzenctl fan enable`).
Every page: **Apply now** (runtime) and **Save to profile** (profiles menu).

### Fans from Linux (user choice; phase 2, before the GUI)

- Feasibility before touching the boot: `sudo modprobe nct6775; sudo dmesg | grep -i nct`
  (expected: chip found + ACPI resource conflict).
- If the chip is there: kernel parameter `acpi_enforce_resources=lax` (manual step: Fedora
  `grubby --update-kernel=ALL --args=…`, other distros `GRUB_CMDLINE_LINUX_DEFAULT`) +
  `ryzenctl fan enable` (writes `/etc/modules-load.d/nct6775.conf`, loads the module).
  Risk: concurrent accesses to the Super I/O with ACPI; minimal writes, only at apply.
- First thing after detection: `ryzenctl fan autodetect` assigns the roles with a physical
  test, without human intervention. Under moderate and stable load (`stress-ng --cpu 4`, fixed
  arguments), for every channel with RPM > 0: median of Tctl and RPM over 5 s → channel at
  40 % for 20 s → new median → restore. Classification:
  - RPM varies < 5 % → **non controllabile** (not controllable: 3-pin fan or pump at fixed 12 V) → protected;
  - Tctl rises ≥ 2 °C **or** RPM at 40 % still ≥ 1500 → **pompa** (pump) → protected;
  - Tctl rises < 1 °C and RPM drops → **ventola** (fan) → writable;
  - otherwise **sconosciuto** (unknown) → protected.
  Physical basis: less flow in the block raises Tctl by degrees in a few seconds; less air on
  the radiator warms ~400 g of liquid slowly (~0.5 °C in 20 s): separation ≥ 5×. Guards:
  abort and immediate restore if Tctl > 80 °C or ΔT > 8 °C, 20 s per channel at most, restore
  in `finally`, Tjmax always active. Thresholds = constants at the top of the file
  (`# ponytail:` tuned on a 360 AIO; adjust if a small radiator gets close to them).
  Without stress-ng or without the test run: no writable channel (fail closed).
  `ryzenctl fan role N pompa|sconosciuto` only serves to demote; "ventola" by hand does not exist.
  `ryzenctl fan identify N` (100 % for 5 s) remains as a help to physically recognise which
  case fan is which, it does not assign roles.
- Control = SmartFan IV hardware curve already programmed by the BIOS: only
  `pwmN_step_up_time`/`step_down_time` are changed (ignores short spikes: the real cause of the
  noise) and, if requested, `pwmN_auto_point*`. No daemon: if the app dies, the chip carries on
  by itself. The CPU stays protected by Tjmax whatever the fans do.

### Calibrations (phase 4) — step machine in `ryzenctl`, GUI as the driver

> Rev. 13: the Eco calibration described below (CO margin +5, FMax sweep for a Tctl target) was
> replaced: Eco reuses the CO validated by Auto/Boost (same margin +3) with the Eco preset, see
> the revision list at the top. The rest of the section is the original design.

User request (rev. 8): **Eco** = not only slow fans, also a **conservative undervolt based on
the real capabilities of the hardware**. The calibrations run in `ryzenctl` as a step
machine, so they survive a crash and `serve` stays responsive:
`autotune start eco|auto [target=70] [colimit=-25] [margin=5] [step=90]`,
`autotune step` (runs ONE test and returns: the GUI calls it in a loop showing the progress),
`autotune status`, `autotune abort`. State in `/var/lib/ryzenctl/autotune.json` (atomic,
fsync before every SMU write). The load (`stress-ng`, fixed arguments) is launched by
`ryzenctl` for the current step only. Every step writes `active` → a crash produces
`crashed`; at reboot `autotune status` shows the interrupted step and the GUI offers to
resume marking it unstable. Warning before starting: possible reboots, save everything.

**Eco** (`autotune start eco`), in order:
1. *Conservative undervolt*: for every core 0..7, the others at baseline, CO from 0 in steps of
   −5 down to `colimit` (default −25); every step `step` seconds (default 90) in three phases:
   full load `stress-ng --cpu 1 --taskset c --cpu-method all --verify`, 50 % load
   (`--cpu-load 50`), 10 % load (CO instabilities emerge mostly at low load). Failure = exit ≠ 0
   or new MCE errors in the kernel log. Core result = last stable + `margin` (default +5:
   conservative, not the limit). Final pass of 5 min with all cores at the values found, three
   phases; if it fails, +3 to all and repeat.
2. *FMax for silence*: with the CO found, from the baseline FMax in steps of −100 MHz (minimum
   4000): 12 bursts `stress-ng --cpu 2 -t 2s` + 3 s pause, Tctl sampled at 20 Hz (never PM
   reads during the measurement: they heat the die), p95 of the peaks; first FMax with p95 ≤
   `target` (default 70 °C). `# ponytail:` heuristic, the liquid temperature drifts.
3. *Limits and fans*: PPT/TDC/EDC ×0.55/0.63/0.83 of the baseline (≈ AMD eco 65 W), Tjmax
   min(baseline, 80), `power balanced`; on the "ventola" channels: step 10 s / 5 s and curve
   from the target (minimum pwm of the BIOS curve up to `target − 10 °C`, 100 % at
   `Tjmax − 5 °C`).
Result: `eco` profile rewritten (replaces the preset), with the measurements table
(per-core CO, chosen FMax, p95) shown in the GUI. Duration ~25–40 min.

**Auto** (`autotune start auto`): same CO search but pushed (`colimit` −40, `margin` +3,
reuses the Eco results as a starting point if they exist); then the performance/W knee:
PPT sweep (multi-thread, −10 % per step down to 50 %, TDC/EDC scaled) and FMax
(single-thread, −100 MHz down to −800) with bogo-ops/s from `stress-ng --metrics -Y` and RAPL
power (`intel-rapl:0/energy_uj`, fallback PM d[3]); choice = lowest value with performance
≥ (100 − loss) % of the maximum, `loss` slider (default 10 %). Fans: BIOS curve, step
3 s / 2 s; `power balanced`. **Boost** = baseline + Auto's CO + `power performance` +
BIOS fans. Default and presets stay as today.

Pump never touched; every produced value still goes through the normal validation (≤ baseline
unless unlocked). The fake backend simulates per-core stability (per-core CO threshold, e.g.
core 7 unstable below −15) and the thermal response to FMax, so the selftest covers the step
machine, the resume after crash and the generated profile.

## Files (in `~/Documenti/Progetti/Personali/Ryzen Control/`)

- `ryzenctl` — root helper/CLI + selftest
- `ryzen-control` — GTK4/libadwaita GUI
- `Makefile` — install/uninstall/dkms (DESTDIR/PREFIX/APPID)
- `data/` — systemd units, modprobe.d, polkit policy, .desktop, SVG icon, metainfo, autostart
- `ryzen_smu/` — vendored driver (subtree d298366 + PM table 0x6211xx patch)
- `packaging/ryzen-control.spec`, `packaging/debian/`, `packaging/PKGBUILD`
- `README.md` — installation per distro, Secure Boot (dkms MOK or akmods drop-in), fans,
  warnings
- `CLAUDE.md` — to be aligned with this revision at the start of the implementation (phase
  order, module blacklist, marker order, FMax +200 with unlock, fan roles)

## Git and workflow

- Personal git repo in `~/Documenti/Progetti/Personali/Ryzen Control` (`git init`, branch
  `main`, no remote until you name one). Upstream driver with `git subtree add
  --prefix ryzen_smu https://github.com/amkillam/ryzen_smu d298366 --squash`.
- One commit per step **only after its verification**: the checks that can run without root
  (selftest, driver build, `make install DESTDIR`, `rpmbuild`, `systemd-analyze
  verify`, `desktop-file-validate`, GUI in `--mock`) I run before the commit; those on
  hardware/root you run (`! command` in the prompt) and I commit after your result. Failed
  verification → fix it, no commit.
- Messages in English prose (rev. 12; Italian before), conventional prefix
  (`feat/fix/build/docs/chore/test`), with the `Co-Authored-By` line required by the
  environment. Tags `v0.1.0`, `v0.2.0`… at the end of every phase verified on hardware; the tag
  version is the one of the RPM spec.

## Phases and commits (every phase verified on hardware before the next one)

### Phase 1 — foundations and RPM package → tag `v0.1.0`
| # | Commit | Verification before the commit |
|---|---|---|
| 1 | `chore: init repo, plan, README stub` | — |
| 2 | `build: vendor ryzen_smu d298366 (subtree)` + `fix(driver): PM table 0x6211xx sizes` | `make -C ryzen_smu` builds with the kernel 7.2.8 headers |
| 3 | `feat(ryzenctl): SMU transport, lock, status` | `ryzenctl selftest` (fake backend) |
| 4 | `feat(ryzenctl): co/ppt/tdc/edc/fmax/tjmax/shaper + validation, readback, unlock` | selftest: encodings, ranges, ceilings, restore on failed readback |
| 5 | `feat(ryzenctl): profiles, baseline, boot/shutdown, crash-guard, serve` | selftest: all the scenarios of the state machine |
| 6 | `build: Makefile, systemd units, modprobe.d, polkit policy, desktop, metainfo, icon` | `make install DESTDIR=/tmp/x` = expected layout; `systemd-analyze verify`; `desktop-file-validate`; `appstreamcli validate` if present |
| 7 | `build(rpm): ryzen-control + ryzen-smu-dkms spec` | clean `rpmbuild -ba` |
| 8 | `docs: Fedora installation, Secure Boot, hardware verification` | **you**: `dnf install`, `mokutil --import`, reboot, `dkms status`, `lsmod` without the service = module not loaded, `ryzenctl status`, reversible writes, crash test (Verification 2-5) |

### Phase 2 — fans (CLI) → `v0.2.0`
| # | Commit | Verification |
|---|---|---|
| 9 | `feat(ryzenctl): fan status/autodetect/identify/role/step/curve/enable` | selftest on a fake hwmon (classifier with synthetic Tctl/RPM series, abort); **you**: `modprobe nct6775` + `dmesg`, kernel parameter, `sensors`, `fan autodetect` finds the pump |
| 10 | `feat(ryzenctl): fan part in the profile and at boot` | **you**: Verification 7 (step up 10 s: a 2 s spike does not raise the RPM; pump unchanged) |

### Phase 3 — GUI → `v0.3.0`
| # | Commit | Verification |
|---|---|---|
| 11 | `feat(gui): Adw skeleton, pkexec/serve client, --mock` | start in `--mock`, a single pkexec prompt on hardware |
| 12 | `feat(gui): Monitor page` | values consistent with `sensors`/`ryzenctl status` |
| 13 | `feat(gui): CPU, Curves, Fans pages` | Apply/Save → `ryzenctl status` and the profile file change |
| 14 | `feat(gui): Modes page (Default/Auto/Boost/Custom, unlock, crash banner)` | **you**: banner after the crash test, Reactivate/Stay |

### Phase 4 — calibrations → `v0.4.0`
| # | Commit | Verification |
|---|---|---|
| 15 | `feat(ryzenctl): autotune — step machine, per-core CO, resume after crash` | selftest with simulated stability; **you**: test on 1 core with `step=30` |
| 16 | `feat(ryzenctl): autotune eco — FMax from the Tctl target, limits, fans; eco profile` | **you**: p95 below the target, eco profile generated |
| 17 | `feat(ryzenctl): autotune auto — PPT/FMax knee with RAPL; GUI with progress` | **you**: monotonic table, choice ≤ slider |

### Phase 5 — all Ryzen processors (desktop AM4/AM5, then mobile) → `v0.5.0`
Today everything is tailored to the 9800X3D: gate `codename == 23`, `CORES = 8`, a single set of
SMU IDs, PM table offsets of 0x620105, `core<<20` in the CO. Goal: the same `ryzenctl` on every
desktop Ryzen, with the same guarantees (strict allowlist, readback, fail closed), without
rewriting anything that works.

**Scope.** First wave (desktop, PM table and mailboxes known to ryzen_smu): Granite Ridge
(9000, codename 23, already verified), Raphael (7000, 20), Vermeer (5000, 12), Matisse (3000, 4).
Second wave (APU/mobile, STAPM/fast/slow limits and often without RSMU): Cezanne (14),
Rembrandt (11), Phoenix (21), Hawk Point (24), Strix (22). Excluded: Threadripper/Epyc (HSMP,
different sockets, no hardware to test them). Data sources: ZenStates-Core
(`Zen5Settings.cs`, `Zen4Settings.cs`, `Zen3Settings.cs`, `Zen2Settings.cs` for the MP1/RSMU IDs
and the CO encoding; `PowerTable.cs` for the PM table offsets), ryzen_smu `smu.c`
(codename index, mailboxes, PM table versions and sizes), RyzenAdj for the APUs.

**What changes in the code (minimum).**
- A `FAMILIES` table at the top of `ryzenctl`, indexed by the driver's codename, which
  absorbs the constants scattered today (`GRANITE_RIDGE`, `CORES`, `PM_FAMILY`, `PM`, `PM_CORE_*`,
  `CMD`): per family name, SMU IDs (`co_set`, `co_get`, `ppt/tdc/edc_set`, `fmax_set/get`,
  `tjmax_set`, `shaper_set/get`) with the mailbox of each, PM table offsets (`ppt_limit`,
  `ppt`, `tdc_limit`, `tdc`, `edc_limit`, `edc`, `thm_limit`, `tctl`, voltage/MHz/temperature
  per core), allowed PM table versions (prefix `>>16`: 0x62 Granite Ridge, 0x54 Raphael,
  0x38 Vermeer, 0x24 Matisse), maximum Tjmax (95 Granite Ridge/Raphael/Matisse, 90 Vermeer and
  Zen 3 X3D; to be confirmed per family), unlock ceilings. An entry can omit a key:
  function disabled for that family (Curve Shaper only on Zen 5; Tjmax and CO readback where
  ZenStates has no ID). The rest of the code keeps calling `smu("co_set", …)` and
  `PM["ppt_limit"]`: only what fills `CMD` and `PM` changes (from the entry chosen by `check_cpu`).
- Gate: `check_cpu` looks up the codename in `FAMILIES`; absent → total refusal as today (fail
  closed). An ID outside the family's entry is never sent: the allowlist stays strict, there is
  just one per family.
- Dynamic `CORES`: number of physical cores and CCDs read from sysfs (`topology/core_id`,
  `thread_siblings_list`, `topology/die_id`), no longer the constant 8. Logical → physical
  core map for the CO: today `core << 20` (right only with 1 CCD/1 CCX); ZenStates builds the
  mask as `((ccd << 8) | (ccx << 4) | core) << 20`, so on 2 CCDs core 8 is
  `(1 << 8) << 20`, not `8 << 20` — **to be verified with the 0xD5 readback** (the only proof
  that counts: the set answers OK even with the wrong mask). Fused-off cores (7600X3D: 6 of 8)
  → the map skips the indices absent from sysfs. `core_cpus`/`best_core`/`co_test` use the
  map, not `c % CORES`.
- Parametrised fake backend: `Fake.DEFAULT` takes the family from `RYZENCTL_FAKE_FAMILY`
  (default Granite Ridge); the selftest runs the same suite on 2-3 fake families, including an
  APU without PM table (PPT/TDC/EDC/Tjmax refused, CO/FMax ok) and a 16-core CPU (CO on
  16 lines, profiles and baseline with 16 values, CCD mask in the fake that refuses `8 << 20`).
- GUI: rows of the Curves page and columns of the Monitor from `status.cores`; family and
  codename shown in the status; functions disabled per family with the reason ("Curve Shaper:
  only Ryzen 9000"), neither hidden nor in error.
- `hwtest` remains the reversible verification on real hardware: writes and reads back every
  function of the family, restores the baseline. **No family is "supported" until someone
  has an ok `hwtest`** on that CPU: in the README a table "Processors: verified /
  expected / not supported" with CPU, codename, SMU, PM table and who verified it. The
  families from ZenStates without `hwtest` stay "expected" and the GUI says so.

**Risks and invariants.**
- The dangerous IDs change per family: MP1 0x58–0x6F freezes the 9800X3D and MP1 0x10 turns
  off the display, but on Vermeer/Raphael the MP1 numbering is different; the list of what is
  not sent must be redone per family from the sources, never assumed by analogy. Forbidden
  everywhere: voltage/VID, OC mode, PBO scalar, `smn`, FCLK/memory.
- PM table absent or version outside the family's list → PPT/TDC/EDC/Tjmax refused
  (fail closed), as today. Different PM table offsets per version within the same
  family (0x540xxx vs 0x5401xx): the entry lists only the versions with a verified map.
- Baseline and profiles with a core count different from the boot's (CPU change, update):
  `co` lines with length ≠ `CORES` ignored like the lines no longer allowed are today
  (`profile_lines("baseline")`).
- Mobile: STAPM/fast/slow PPT limits (RyzenAdj), no RSMU on many APUs, Tjmax 100: outside the
  scope of the first wave, the table admits them only when a `hwtest` confirms them.
- The phase cannot be verified in full on this hardware (Granite Ridge only): the tag
  `v0.5.0` certifies the refactor (multi-family selftest + `hwtest` ok on the 9800X3D, no
  regression), not the support of the other families, which comes with third-party `hwtest`.

| # | Commit | Verification |
|---|---|---|
| 18 | `refactor(ryzenctl): FAMILIES table, dynamic CORES, per-family gate` | selftest on the fake Granite Ridge identical to before + suite repeated on a fake 16-core CPU and on a fake APU without PM table; **you**: `hwtest` on the 9800X3D unchanged, `status` shows family and cores |
| 19 | `feat(ryzenctl): Raphael/Vermeer/Matisse from ZenStates-Core` — done as rev. 14: Raphael (CO, FMax), per-core CO refused on CCDs with disabled cores, Vermeer/Matisse left out for lack of sources | selftest with the three fake entries (IDs, CO encoding with CCD, PM offsets); `hwtest` on third-party real hardware, one family at a time → goes from "expected" to "verified" |
| 20 | `feat(gui): dynamic cores, family shown, disabled functions explained` | `--mock` with `RYZENCTL_FAKE_FAMILY` = Granite Ridge / 16 cores / APU: Curves table with 8/16 rows, Shaper disabled with reason, no error |
| 21 | `docs: processors table in the README` — done: README "Processors" (verified: Granite Ridge on the 9800X3D; expected: the other Ryzen 9000, Raphael; not supported: Zen 1–3 desktop, APUs/laptops, HEDT) and "Adding your processor" | `make check`; README with the verified/expected/not supported table and the `hwtest` procedure for whoever wants to add their CPU |
| 21b | `feat: Vermeer, Matisse, Zen/Zen+; FMax optional, per-family CO range, boost switch, board-limit guard` (rev. 16) | selftest on fake 5900X, 5800X on CCD1, 3700X, 2700X and a board with 1000 W limits; GUI smoke on each; `hwtest` by owners of those CPUs |
| 21c | `feat(autotune): single-core phase, watchdog during calibration, autotune verify` (rev. 16) | selftest with a fake single-thread weakness and a fake watchdog; **you**: a calibration with the watchdog armed |
| 21d | `feat: custom calibrations saved under their own name` (rev. 17) | selftest: Auto profile and shared measurement unchanged after a custom run, Boost rule, delete; GUI smoke with a custom calibration |

### Phase 6 — system tray icon (bottom right, Telegram style) → `v0.6.0`
User request (rev. 6). `StatusNotifierItem` icon (KDE Plasma's native protocol, on GNOME the
AppIndicator extension is needed) with a `com.canonical.dbusmenu` menu, implemented directly on
D-Bus with PyGObject's `Gio`: no new dependency, works on Wayland (GTK4 no longer has the
StatusIcon). It is the same `ryzen-control` process started with `--tray` by the autostart at
login (hidden window, a single process: the `ryzenctl-notify` autostart is absorbed, the crash
banner becomes a menu entry).
- Quick menu: modes **Default / Quiet / Performance / Eco / Auto / Boost** (check mark on the active one),
  **Apply at boot** on/off, **Open Ryzen Control**, **Quit**; after a crash, at the top, the entry
  "Profile disabled after a crash: Reactivate / Stay on Default".
- Tooltip and status icon: current Tctl and PPT updated every 2 s (normal icon / warning if
  Tctl > Eco target); no SMU polling without an active `serve`: until a privileged action is
  done only k10temp is read.
- First privileged action of the session → a single pkexec prompt (like the GUI).
| # | Commit | Verification |
|---|---|---|
| 22 | `feat(tray): StatusNotifierItem + dbusmenu via Gio, --tray, autostart` — done (rev. 18): the custom calibrations in the menu too; the tooltip without the Tctl warning icon (attention only after a crash) | `--mock --tray`: icon in Plasma, menu, mode check mark; **you**: mode change from the menu → `ryzenctl status` changes; pkexec prompt only once |

### Phase 7 — other distros → `v0.7.0`
| # | Commit | Verification |
|---|---|---|
| 23 | `build(deb): packaging/debian` — done (rev. 19) | built, lintian-clean, installed and removed in Debian 13 and Ubuntu 24.04 containers |
| 24 | `build(arch): PKGBUILD` — done (rev. 19) | makepkg + namcap, installed and removed in an Arch container |

### Phase 8 — APUs and laptops → `v0.8.0`
| # | Commit | Verification |
|---|---|---|
| 25 | `feat: desktop APUs and mini PCs (fast/slow PPT, Tctl, TDC/EDC)` | selftest on fake Cezanne/Phoenix, GUI smoke; `hwtest` by owners (expected) |
| 26 | `feat: laptops (power source, re-apply, give-up on firmware fights)` | selftest with fake power supplies and firmware resets; owners' `hwtest` |

Phase 8 is tested on fake hardware only (no APU here): the tag `v0.8.0` follows the regression check on the 9800X3D (`hwtest`, a mode applied and Default, the reapply timer installed and idle); APU and laptop owners' `hwtest` moves the families to verified.

## Verification

1. `python3 ryzenctl selftest` (without hardware): CO/Shaper encodings, validation and ceilings,
   profile parsing, baseline/Default, failed readback → restore, crash-guard state machine
   (all the scenarios listed), marker order (dirty and active before the fake SMU write).
2. Packages: clean `rpmbuild -ba packaging/ryzen-control.spec`; `sudo dnf install` of the two
   RPMs → `dkms status` = `ryzen_smu/<ver>, <kernel>: installed`; `modinfo -F signer` = dkms
   key (or akmods with drop-in); after `mokutil --import` + reboot: `lsmod | grep ryzen_smu`
   empty until the service starts (blacklist), `systemctl start ryzenctl` → module
   loaded, `/sys/kernel/ryzen_smu_drv/codename` = 23; `dnf remove` removes everything.
3. `sudo ryzenctl status` = BIOS values (CO, FMax ~5200, PPT/TDC/EDC 162/120/180 or board PBO).
4. Minimal reversible writes with readback: `co 7 -3`→`co 7 0`; `ppt 150`→baseline;
   `fmax 5000` (under load ≤5000 MHz)→baseline; `tjmax 85`→baseline; `shaper 4 -2 -2 -2`→0.
5. Crash-guard: harmless profile (e.g. `ppt 150`) with autostart; `sync; echo b >
   /proc/sysrq-trigger` → at boot `crashed` present, `ryzenctl status` = baseline, notification
   at login; `systemctl restart ryzenctl` → baseline unchanged; clean reboot → normal apply;
   suspend/resume → status = profile; boot with `ryzenctl.off` → module not loaded,
   nothing applied; kernel update → `dkms.service` rebuilds, the service starts afterwards.
6. GUI: start from the menu (entry in Discover thanks to the metainfo), a single pkexec prompt,
   monitor updated, Apply/Save work, crash banner with Reactivate/Stay.
7. Fans: `sensors` shows nct67xx; `fan autodetect` classifies the pump as "pompa"
   (ΔT reported) and the radiator fans as "ventola"; `fan role N ventola` does not exist;
   pump channel refused on write; step up 10 s → a 2 s load spike does not raise the
   RPM; pump at unchanged RPM for the whole test.
8. Calibration: Eco lowers the p95 of the Tctl peaks below the target; Auto produces a
   monotonic table (W ↓ ⇒ ops/s ↓) and chooses PPT/FMax with loss ≤ slider, ops/W of the chosen
   point > ops/W of Boost; auto-tuning on 1 core with 1 min steps for a quick test.
