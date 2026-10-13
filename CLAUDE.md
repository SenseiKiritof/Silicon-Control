# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

"Ryzen Control": Ryzen Master-style control (Curve Optimizer, Curve Shaper, PBO, FMax/Tjmax,
fans) for a Ryzen 7 9800X3D on Linux, GTK4/libadwaita GUI + root helper, RPM/deb/Arch packages.

The source of truth is the plan `docs/plans/2026-10-09-ryzen-control.md` (rev. 4): architecture,
SMU command table, validation ranges, profile format, crash-guard, planned phases and commits.
Read it before touching anything; this file only summarises the essentials. Future plans go in
the same folder (`docs/plans/YYYY-MM-DD-<topic>.md`). Language: source code, comments, README,
plans and commit messages are in English; user-facing strings go through gettext (domains
`ryzenctl` and `ryzen-control`, catalogs in `po/<domain>/<lang>.po`, Italian maintained);
protocol keys and stored values keep their historical Italian names (`canale`, `modo`, `curva`,
`ventola`, `pompa`, `instabile`, …) — renaming them is a coordinated change of ryzenctl +
ryzen-control + selftest.

Done: **phase 1** (`ryzenctl` complete for the CPU part, systemd units, vendored driver, RPM
spec, README). Verified on hardware (9800X3D, SMU 98.81.0, PM table 0x620105): driver signed
automatically with the akmods key, `hwtest` ok for CO, FMax, PPT, TDC, EDC, Tjmax.
**Curve Shaper not verifiable**: RSMU 0xA6 answers OK but 0x84 returns zeros (or arg0 itself)
→ `shaper` is experimental, out of profiles/baseline/hwtest, the setter always fails at readback
(safe by construction). Crash-guard verified on hardware (sysrq crash → profile disabled +
notification, reactivate, restart, clean boot, resume). Tag `v0.1.0` on `main`.
**Phase 2 (fans) verified on hardware** (NCT6799D, no ACPI conflict, no kernel parameter):
`fan enable/status/autodetect/step/curve/identify` ok; autodetect gave pwm2 pompa (pump)
(2125→1898 rpm at 21 %), pwm5/pwm6 ventola (fan), pwm7 (100 %, no tachometer) not testable and
protected; step 10 s/5 s on the fan channels removes the jumps on spikes (3 s of full load, rpm
steady). The chip rounds the steps to ~200 ms. Tag `v0.2.0`.
**Phase 3 (GUI) and phase 4 (calibrations)** written and used on hardware: `ryzen-control`
(pages Monitor, Modes with Quiet/Performance presets and calibrated Eco/Auto/Boost, CPU, Curves, Fans,
Preferences;
values coloured against the factory ones; resizable calibration window with the progress pinned on
top, duration estimates, measured voltage per core and mV per step; immediate interruption).
`autotune` in ryzenctl is a step machine (`start/step/status/abort/estimate`, state in
`/var/lib/ryzenctl/autotune.json`, resume after crash, parallel by default). Auto verified on
hardware (fft search: per-core limit −35, final pass −29 stable, PPT 114 W, FMax 4850, ≈ 3.4
mV/step); Eco reuses Auto's validated CO with the Eco preset (instant when a recorded final pass
covers it); Boost only with unlock (unlock ceilings); pump with cap or fixed speed; choice at the
end of the calibration (Cancel / Save / Save and apply); `trust`, start at login, clickable
notification; Preferences tab; unknown fan channels in a collapsed section. Tag `v0.4.5` (VERSION
0.4.5), DKMS module `DRV_VERSION` 0.4.1. **Phase 5** (all Ryzen CPUs) in progress: step 18 committed
(multi-variant selftest and read-only check on the real sysfs; `hwtest` on the 9800X3D pending) —
`FAMILIES` table by codename, `TOPO`/`CORES` from the sysfs topology, CO mask with the CCD
(`co_mask`), selftest repeated on fake variants (`Fake(variant)`, `RYZENCTL_FAKE_FAMILY`: 16 cores on
2 CCDs, no PM table, 2×6 cores, Raphael). Step 19: Raphael (Zen 4, `verified: False`: CO and FMax,
no PM map → limits refused); CCDs with disabled cores: the physical slots come from the core fuses
(SMN reads, ZenStates-Core addresses; `core_map`), refused only if unreadable or inconsistent;
Vermeer/Matisse left out for lack of reliable IDs/maps. Step 20: the GUI shows and uses only the
active cores (rows from `status.cores`/telemetry), the family and core count on the Monitor, a note
for families not verified; Auto refused where the PM limits are unknown (its knee needs the PPT). Step 21:
README "Processors" table (verified / expected / not supported) and the `hwtest` procedure for
third-party CPUs; `hwtest` ok on the 9800X3D after the refactor (2026-10-12). Rev. 16, from three
research agents (Ryzen 5000, older CPUs, Windows tools): Vermeer expected (CO MP1 0x35/0x48 in
−30..+30, limits RSMU 0x53–0x56, PM tables 0x3808xx/0x3809xx, Zen 3 fuses always read), Matisse
expected (limits only), Summit/Pinnacle Ridge (no SMU command: boost, power, fans); FMax optional
everywhere, per-family CO range, `boost on|off` (cpufreq, no SMU), Tdie on the X parts with an
offset, board-limit guard (motherboard limits in the BIOS: Quiet/Eco on AMD's Eco mode values, Auto
refused); calibration ideas from CoreCycler: single-core phase in the final pass (user choice,
default on), hardware watchdog during a calibration, `autotune verify` — done by an agent and merged:
`single` (SINGLE_SEC per core, one thread, a core that fails alone is raised alone, `core_margin`),
`Watchdog` in `serve` only, `autotune verify <profile> [minutes=]` / `finish`. Rev. 17 (user request):
custom calibrations, `autotune start <mode> name=<profile>`: saved under their own name, never over
eco/auto/boost, and their CO search never written over the shared `co_limits.json`; listed in
`settings.calibrated` (status `calibrated`) with the base mode; GUI "Custom" row in the Calibrated
column; `retry=1` (custom only) ignores the reused measurement's crash margin and recorded failures.
**Phase 5 closed, tag `v0.5.0`** (2026-10-13), on the 9800X3D: `hwtest` ok, watchdog armed and
disarmed by `serve`; forced reset proven (2026-10-13: `serve` killed with SIGKILL during a verify →
the board reset by itself on the SP5100 TCO timer; with systemd driving it, 0.5.0-5, a killed `serve`
no longer resets the PC and the next ryzenctl released it, while a kernel crash, sysrq c, during a
verify was reset by the systemd-driven watchdog), a custom calibration from Auto with the single-core test passed at −29 on every core
(PPT 114 W, FMax 4750). Tag `v0.5.1` (2026-10-13): the calibration watchdog driven by systemd, verified
(freeze and kernel crash reset the PC, a dead ryzenctl does not), clearer custom-retry text.
**Phase 6** (tray, step 22): `Tray` in `ryzen-control`, a StatusNotifierItem + com.canonical.dbusmenu exported
with Gio (`register_object_with_closures2`, the old name before GLib 2.84); `--tray` starts only the icon
(`App.hold`), Preferences "Icon in the system tray" (ui.json `tray`) and "Start minimized to the tray icon"
(`tray_minimized`, default on: the login entry then runs `--tray`, otherwise the window opens too);
menu and tooltip from `local_state()` (settings.json, crashed, profile names: world-readable) and k10temp,
no root until a menu entry needs it, then the app's single `ryzenctl serve` (`App.get_helper`, shared with
the window, kept when the window closes while the tray is on); PPT in the tooltip only when serve runs
anyway. Verified on the mock over D-Bus in Plasma (registered, layout, click → mode applied, Quit) and by
the user on the installed package. **Phase 6 closed, tag `v0.6.0`** (2026-10-13).
**Phase 7** (steps 23–24): `packaging/debian/` (debhelper 13, `dh_dkms` on the dkms.conf that make install
generated, `dh_installsystemd`: ryzenctl.service started, the resume unit only enabled; lintian overrides for
the sleep targets and the missing man pages) and `packaging/PKGBUILD` (+ `.install`: services to enable by
hand, the dkms pacman hook builds the module). Both through the same `make install`; built and checked in
containers by `packaging/build-deb.sh` / `build-arch.sh` (`make deb`, `make arch` with podman, and two jobs
of the release workflow): lintian clean, namcap warnings expected (empty state dirs, the python3 shebang,
runtime-only deps); installed, selftest and removed in Debian 13, Ubuntu 24.04 and Arch containers; not used
on real Debian/Ubuntu/Arch hardware. `make check` fails if VERSION differs in the spec, debian/changelog or
PKGBUILD. **Phase 8** (APUs and laptops, rev. 20–21), all expected, tested on fake hardware only: step 25
desktop APUs and mini PCs — fast/slow/Tctl/TDC/EDC, Quiet/Performance presets; step 26 laptops (done by an
agent, reviewed): the APU entries are `mobile`, the baseline records the power source (`# source`,
`power_source`: Mains/USB online = AC), `load_baseline(strict)` refuses CPU writes on the other source
(`source_mismatch`), Default there writes only fan/power/boost; `apply_lines` runs `power`/`boost` first
(amd-pmf rewrites the limits on a platform profile change); `ryzenctl reapply` (ryzenctl-reapply.timer every
10 s, udev rule `60-ryzen-control.rules` on AC changes, both gated by the flag `/run/ryzenctl/reapply-wanted`
that `reapply_mark` keeps only on a laptop with autostart and a profile changing a limit) writes back the
drifted limits and gives up after `REAPPLY_MAX` corrections in `REAPPLY_WINDOW` s (state `/run/ryzenctl/reapply.json`,
read by the Monitor and the tray); a limit set by hand (`limit_setter` outside a profile) or a save of the
selected profile stops it until the next apply. **Phase 8 closed, tag `v0.8.0`** (2026-10-13) after the regression
check on the 9800X3D: `hwtest` ok, a mode and Default applied, the timer enabled by the RPM's `%triggerun` on the
upgrade from 0.7.1, firing every 10 s and silent in the journal (no flag on a desktop).
The repository's GitHub releases are immutable (no asset can be added after publishing): the
workflow builds the three packages in parallel as artifacts and one `release` job publishes them together
(v0.7.0 has the RPM only; v0.7.1 is the first with all three).

Lessons from the hardware: the PM table reflects a new limit after tens of ms → readback with
a wait (`READBACK_WAIT`); the baseline is recaptured only at boot, so after an update that
changes the format the lines no longer allowed must be ignored (`profile_lines("baseline")`);
the fake backend must never have real effects (e.g. `notify-send`) because the selftest runs in
the user's session. Calibration: `--cpu-method all` for 5 min is not enough, fft at 16 threads
froze the system at −37 (per-core limit −40) → the final pass starts from the heaviest method
(`FINAL_HEAVY_SEC`); a stress-ng that exits early or with code ≠ 0 is instability
(`Unstable`), never a low metric; every phase with the final CO applied has the `in_progress`
marker (`post`) so a crash is attributed to the combination (+3, final pass repeated); failed
combinations stay in `co_limits.json` (`final_failures`) and are not retried; the crash
attribution (`at_attribute_crash`, no SMU) already happens in `boot`; the heavy method is also
the first phase of the search (`co_limits` files without `method` are not reused). The nct6775
driver does not write back a 0 ms step (minimum register 1 = 400 ms): `FAN_STEP_MIN_MS`,
otherwise `default` failed on the baseline's fan lines. The BIOS fan curves reach 100 % only at
125 °C: under load the fans hardly react, so the "moderate" level (Auto, Boost) is the BIOS curve
+10 % with full speed at 100 °C and 3 s / 2 s steps (tuned by the user); generated curves always
start from the baseline's BIOS curve (`bios_curve`), never from the chip's current one. A freeze followed by a reboot from the
button can wipe the files written in the last seconds (btrfs): even freshly created git objects.
A separate Eco calibration (FMax sweep for a Tctl target, margin +5) turned out redundant with
Auto's undervolt: Eco now reuses the validated CO and the FMax sweep is gone.

## Layout

- `ryzenctl` — Python stdlib, the only privileged entry point (CLI, `serve`, `selftest`).
- `ryzen-control` — Python/PyGObject GUI (GTK4, libadwaita ≥ 1.5), runs as the user; a single
  `pkexec ryzenctl serve` process per session (Helper with reader + FIFO: requests are sent
  without waiting for the previous ones, replies arrive in order); `--mock` uses the fake backend
  with a separate app id (`…Mock`) so as not to activate the installed instance.
- `ryzen_smu/` — upstream driver (amkillam/ryzen_smu, commit d298366) **copied**, not a subtree
  (git-subtree is not installed): origin, excluded files, local change to `smu.c` (PM table
  0x6211xx/0x6212xx) and update procedure in `ryzen_smu/UPSTREAM.md`.
- `Makefile` — the only source of the installed layout (`install` = `install-cli` + `install-gui`
  if present + `install-dkms-src`; `DESTDIR`, `PREFIX`; `APPID` is only used for the file names in
  `data/`, the id `org.ryzencontrol.RyzenControl` is written inside the files). Every package is
  a wrapper that calls the Makefile, never a duplicated layout.
- `data/` — systemd units (`ryzenctl.service`, `ryzenctl-resume.service`, `ryzenctl-reapply.service` +
  `.timer`), udev rule (laptops' AC changes), preset, modprobe blacklist, polkit policy, .desktop, icon,
  metainfo, notify autostart.
- `packaging/ryzen-control.spec` (RPM: **a single package** `ryzen-control`, noarch, with the
  driver's DKMS source inside; `Obsoletes: ryzen-smu-dkms` for releases 1-4). The `%post`
  rebuilds the module only if it is missing for the running kernel or the key changes: **when
  the source in `ryzen_smu/` changes, `DRV_VERSION`** (Makefile) **= `%drv_version`** (spec)
  **must be bumped**, otherwise dkms keeps the old module; `VERSION` (app) does not touch the
  module, so a release does not rebuild it. `packaging/debian/` and `packaging/PKGBUILD` (phase 7)
  are wrappers of the same make install; bump `debian/changelog` and `pkgver` with VERSION (make check
  enforces it).

Compatibility constraints: Python ≥ 3.9 syntax (no newer feature), libadwaita ≥ 1.5, no Python
dependency beyond PyGObject, no test framework.

## Commands

Without hardware or root (run before every commit):

```sh
python3 ryzenctl selftest       # fake backend; encodings, validation, ceilings, profiles, baseline, crash-guard, serve
make check                      # selftest + layout in a temporary root + systemd-analyze verify + desktop-file-validate + appstreamcli
make driver-check               # builds the driver in a copy outside the repo (kbuild does NOT accept spaces in the path: `make -C ryzen_smu` fails here)
make rpm                        # tarball from HEAD (only what is committed) + RPM in dist/; rpmlint NOT installed
make deb / make arch            # the same tarball, .deb / Arch package built and checked in a podman container
RYZENCTL_ROOT=/tmp/fake python3 ryzenctl boot   # CLI on the fake backend (state in $ROOT/fake_smu.json)
python3 ryzen-control --mock    # GUI without driver or pkexec (phase 3)
make screenshots                # docs/screenshots/*.png from a fresh fake backend (regenerate after visible UI changes)
```

On hardware (the user runs them, with `! command`; commit after their result): checklist in
README "Hardware verification".

Not on this machine: `dpkg-buildpackage`, `lintian`, `namcap` (run in containers: `make deb`, `make arch`),
`stress-ng`. The deb/Arch packages are container-tested only: the README says so.

## Architecture

```
ryzen-control (GUI, user) ──pkexec──▶ ryzenctl serve (root, validates EVERYTHING)
                                        ├─ /sys/kernel/ryzen_smu_drv/*   (SMU)
CLI: sudo ryzenctl …  ──────────────────┤─ /sys/class/hwmon/nct67xx/*    (fans, phase 2)
systemd: ryzenctl.service, -resume ─────┘─ /etc/ryzenctl, /var/lib/ryzenctl, /run/ryzenctl
```

- **A profile = baseline + its own lines** (`with_stock` in `profile_lines`): the stock values of
  what it does not set (CPU keys, fan `step`/`curve` of "ventola" channels; never the pump) come first,
  so `profile show`, `apply` and the boot always see and write a complete state.
- **A single command grammar** (`co 7 -3`, `ppt 88`, `fmax 4800`, `shaper 4 -5 -5 0`,
  `power balanced`, …) used identically by the CLI, profile file lines and the `serve` protocol
  (one JSON-array line per request, one `{"ok":…}` line as reply; `boot/shutdown/resume/serve`
  denied via serve). A new command = a `cmd_*` function + an entry in `COMMANDS` (+ in
  `PROFILE_CMDS` if allowed in profiles) + a case in the selftest.
- **`ryzenctl` is the trust boundary**: the GUI validates nothing definitive, it sends and shows
  the errors. `serve` is started once per session (a single pkexec prompt; `trust on` writes a
  polkit rule in `/etc/polkit-1/rules.d/` for the calling user, `PKEXEC_UID`/`SUDO_USER`, and the
  prompt disappears).
- **Fake backend** (`class Fake`, active with `RYZENCTL_ROOT`): simulates SMU, PM table, k10temp,
  power profile; `drop` ignores the next writes (readback proof), `log` records which markers
  existed at every write (ordering proof). New logic = a case in the selftest.
- **Baseline** (`/var/lib/ryzenctl/baseline.conf`, same format as profiles): captured by `boot`
  once per boot (`/run/ryzenctl/booted`), never if `active` exists. Ceiling of every value;
  without a baseline of this boot (`/run/ryzenctl/baseline-done`) no CPU write. Tjmax ≤ baseline
  always; PPT/TDC/EDC ≤ baseline and FMax ≤ baseline unless `unlock on` (ceilings 230 W / 160 A /
  230 A, FMax +200 MHz, warning printed).
- **Crash-guard** (explicit user requirement), markers in `/var/lib/ryzenctl` with fsync:
  `boot` → if `dirty` ∧ `active` writes `crashed {time, profile}`; removes `active`; writes
  `dirty`; captures the baseline; applies fans; applies CPU only if autostart ∧ ¬crashed. `active`
  is written by `write_verify` **before** the SMU write of a value ≠ baseline. `shutdown`
  (ExecStop) removes `dirty`. A restart in the same boot (`booted` present) only puts `dirty`
  back. `boot` never raises exceptions (the unit must stay active so that ExecStop runs). Escape
  hatch: kernel parameter `ryzenctl.off` + blacklisted module (only the service loads it with an
  explicit modprobe).
- **Modes** are static (no daemon, the dynamic behaviour is done by PBO): Default / Quiet (preset) /
  Eco (calibrated) / Auto (calibrated) / Performance (preset) / Boost (calibrated) / Custom.
  The three calibrated modes share one CO measurement and one margin (+3): Auto adds the
  PPT/FMax knee, Boost the unlock ceilings and a gain bench (`check_boost`: preset/autotune
  start/use/apply refused without `unlock on`, `unlock off` refused while Boost is selected), Eco
  is the Eco preset with that CO — every successful final pass is recorded in `co_limits.json`
  (`final_passed`) and a covering one makes `autotune start eco` return `done` at once
  (`at_reused`, `eco_from` in the estimate); without it the final pass, from scratch the search.
  `preset <name>` generates the profiles from the baseline (ratios in `PRESETS`); `autotune`
  replaces them with measurements, but only on `autotune save [apply]`: at `phase == done` the
  CPU is at baseline and the profile is proposed in `profile_lines` (the GUI asks Cancel / Save /
  Save and apply; `abort` discards). `serve` executes the requests in order on one thread and
  reads on another: `autotune abort` raises the flag `/run/ryzenctl/autotune-abort` and
  terminates the stress-ng processes registered in `_children`.
- **Fans** (phase 2): no daemon; only `pwmN_step_up_time`/`step_down_time` (and curve points if
  requested) of the SmartFan already programmed by the BIOS are changed. Roles assigned by
  `fan autodetect` (physical test: channel at 40 % for 20 s under load, ΔTctl tells the pump
  apart); by hand one can only demote, never promote to "ventola" (fan). `pwmN_enable` is never
  touched outside the tests (restored in `finally`), with a single explicit exception for the
  pump: `fan N pump max <50-100>` (BIOS curve with the points above the cap reduced; the BIOS
  curve is stored in `settings.fans[N].bios_curve` and `pump_max` is reset at every boot because
  the BIOS reprograms it), `fan N pump <50-100>` (fixed speed, manual mode) and `fan N pump auto`
  (restores); never curves or steps on the pump by hand (the BIOS drove it to 100 % under load
  and it hummed). The kernel parameter `acpi_enforce_resources=lax` is set by `ryzenctl fan
  enable` (explicit user action, grubby), never by the package. The fake backend simulates the
  hwmon with real files under `$ROOT/sys/class/hwmon/hwmon0` and the physics in
  `Fake.after_fan_write`.

## Hardware invariants (non-negotiable)

- SMN: reads only, only the family's fuse addresses (`smn_read`); no SMN write, ever.
- Strict SMU allowlist per family (`FAMILIES[codename]["cmd"]` at the top of `ryzenctl`; `smu()` never
  sends a name missing from the entry). Granite Ridge: CO MP1 0x35, PPT/TDC/EDC MP1
  0x3E/0x3C/0x3D, FMax RSMU 0x70/0x6E, Tjmax RSMU 0x59, Shaper RSMU 0xA6/0x84, CO get RSMU
  0xD5. Vermeer: CO MP1 0x35 / get MP1 0x48, PPT/TDC/EDC/Tjmax RSMU 0x53/0x54/0x55/0x56. Matisse:
  RSMU 0x53–0x56 only (never MP1 on Zen 2). Summit/Pinnacle Ridge: none. No other ID is sent. The
  same number means different things per family (MP1 0x3E: PPT on Zen 4/5, Tjmax on Zen 3): never
  by analogy. Never MP1 0x58–0x6F (freezes the SMU on the 9800X3D) nor MP1
  0x10 (turns off the display); on Zen 2/3 never RSMU 0x58 (PBO scalar), 0x5A–0x5D (OC mode,
  PROCHOT, OC frequency), 0x61 (OC VID). Never voltage commands, OC mode (RSMU 0x5D), fixed VID (0x61),
  PBO scalar (0x5B), `smn` writes, FCLK/memory.
- APUs (`APU_CMD`/`APU_PM`, codenames 2, 17, 14, 11, 21, 24, 22, 26): fast/slow PPT MP1 0x15/0x16, Tctl MP1
  0x19, TDC/EDC MP1 0x1A/0x1C where mapped, read back from the PM table (explicit `pm_versions`: codename 22
  has two table families); STAPM read only; no CO, no FMax, no unlock (`cap_of`: the stock value is the ceiling).
  Writing exactly the stock value is always allowed back (an APU Tctl limit can be 100 °C > TJMAX_ABS_MAX).
- Laptops: a system battery (`system_battery`, power_supply type Battery whose scope is not Device: a wireless
  mouse does not count) refuses every family not marked `mobile` (only the APUs) — the driver reports Dragon
  Range and Fire Range (HX laptops) as Raphael and Granite Ridge. On a laptop CPU writes only on the baseline's
  power source; `reapply` writes only the limit lines of the selected profile (stock ones included) that drifted,
  through the setters (readback, markers),
  never while crashed, during a calibration or after the give-up.
- Gate: the driver's `codename` must be a key of `FAMILIES` (23 Granite Ridge verified; 20 Raphael,
  12 Vermeer, 4 Matisse, 10 Pinnacle Ridge, 9 Summit Ridge not verified), otherwise total refusal
  (`family()`); no readable CPU topology → refusal too. `boost` and `power` are kernel switches
  (cpufreq/EPP, no SMU) read back from sysfs.
- Per-core CO only where the physical core slot is certain (`core_map`/`co_support`): complete CCDs
  (8 cores) map in order with no register read (Zen 4/5 only: on Zen 3, `map_from_down`, the fuses
  are always read, an 8-core part can sit on the second CCD); CCDs with disabled cores take the enabled slots from
  the core fuses, read through the driver's `smn` file (4-byte write = read; **never** the 8-byte
  write) only at the fuse addresses of the family entry, and only if they match the sysfs topology;
  otherwise CO, calibrations and the CO step of `hwtest` are refused/skipped.
- Hardware watchdog (`Watchdog`): handed to systemd (`RuntimeWatchdogUSec` via busctl, `WD_SEC`) only by
  `serve` while a calibration/verification runs, never with `nowayout`, when systemd already drives it,
  when another program holds it, or with `watchdog=0`; released (property back to 0) at done, abort,
  error, end of input. A `serve` that dies leaves it with systemd (PID 1 keeps pinging: no reset); the
  next ryzenctl releases it (`wd_cleanup`, owner pid in `/run/ryzenctl/watchdog`) and the step of a dead
  process counts as a crash (`in_progress` carries the pid; same boot → baseline CPU applied first).
- Every SMU transaction under `flock(/run/ryzenctl/lock)` (the driver's `smu_args` is global).
- Every write is followed by a readback; mismatch → one retry → restore of the baseline value →
  error. No automatic fallback to other IDs.
- Floors: PPT ≥ 45 W, TDC ≥ 30 A, EDC ≥ 45 A (PPT 0 locks the CPU at 606 MHz). CO/Shaper −50..+30
  (CO per family: `co_range`, −30..+30 on Zen 3),
  FMax 3000..baseline(+200 unlocked), Tjmax 60..min(baseline, 95). The constants live at the top
  of `ryzenctl` and are calibration knobs, not to be scattered around.
- PM table values read only if `pm_table_version>>16` is the family's `pm_prefix` (0x62) or the
  version is in its `pm_versions` (Vermeer, Matisse: the versions with a checked map), per-core
  arrays (by physical slot, through `core_map`) only for a version in its `pm_cores` (0x620105); PM
  table absent → PPT/TDC/EDC/Tjmax refused (fail closed), CO/FMax/Shaper ok. A family without
  `fmax_set` (Zen 3 and older) has no FMax anywhere (baseline, presets, Auto knee, hwtest).
- Baseline limits above the unlock ceilings are the motherboard's (`board_limits`): ratios of them
  are refused (Auto) or replaced by the family's `eco_limits` (Quiet/Eco).
- Profile names only `[a-z0-9_-]{1,32}`, `baseline` reserved. State files written atomically
  (`write_atomic`).

## Workflow

- Local git repo, branches `main` (init only) and `dev` (development), no remote until the user
  names one.
- Step-by-step development following the plan's "Phases and commits" table: one commit per step,
  **only after verifying** the step (`make check` at least). Failed verification → fix it, no commit.
- Conventional prefix (`feat/fix/build/docs/chore/test`), message in English prose,
  `Co-Authored-By` line required by the environment.
- Tags `v0.1.0`, `v0.2.0`, … at the end of every phase verified on hardware; the tag version is
  the one of `VERSION` in the Makefile and of the RPM spec (keep them aligned).
- Deliberate simplifications with a known ceiling are marked with a `# ponytail:` comment.
