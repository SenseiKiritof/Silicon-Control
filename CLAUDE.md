# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"Silicon Control": Linux control of CPU power limits, boost frequency, temperature limit, undervolt and
fans for every CPU vendor, with automatic per-chip calibration and protection after a crash; GTK4/libadwaita
GUI + root helper, RPM/deb/Arch packages. It is the successor of "Ryzen Control" (AMD only, in
`../Ryzen Control`, last release v0.8.0, public on https://github.com/SenseiKiritof/Ryzen-Control).

The source of truth is the plan `docs/plans/2026-10-13-silicon-control.md`: goals, decisions (taken and still
to confirm), target architecture, safety rules for the new backends, phases and commits. Read it before
touching anything. The Ryzen Control plan `docs/plans/2026-10-09-ryzen-control.md` documents the inherited
code (SMU command tables, crash-guard, calibrations, revisions 1–22) and stays as reference. Future plans go
in the same folder (`docs/plans/YYYY-MM-DD-<topic>.md`).

## Status (2026-10-13)

- The first commit imported Ryzen Control v0.8.0 (commit 97152b0 of `../Ryzen Control`) unchanged: the code
  is AMD only and still uses the old names (`ryzenctl`, `ryzen-control`, `org.ryzencontrol.RyzenControl`,
  `/etc/ryzenctl`, `/var/lib/ryzenctl`, `/run/ryzenctl`, `ryzenctl.off`, gettext domains `ryzenctl` and
  `ryzen-control`). The sections "Inherited from Ryzen Control" below describe that code as it is.
- Its history is not in this repository: the commit messages that explain the code and its hardware lessons
  are in `../Ryzen Control` (`git -C "../Ryzen Control" log -S'<text>'` or `log -L` when the reason for a line
  is unclear; `../Ryzen Control/CLAUDE.md` has the phase-by-phase history).
- Nothing of the Silicon Control plan is done yet. Start by confirming the open decisions of the plan with the
  user, then phase 0, step 1 (the rename).
- No git remote yet: the user creates the GitHub repository when ready.

## Working with the user

These are the user's standing rules from the Ryzen Control sessions (that project's memory does not carry
over here, so they live in this file):

- Reply in Italian. Source code, comments, README, plans and commit messages in English; user-facing strings
  through gettext with the Italian catalogs kept complete (`po/<domain>/it.po`).
- The plugins ponytail and caveman are always on (global `~/.claude/CLAUDE.md`).
- Plans are written in `docs/plans/` (versioned with the project), also when plan mode is used.
- Step-by-step development: one commit per step of the plan, only after its verification (`make check` at
  least); failed verification → fix it, no commit. Commits on `dev` are authorized. Conventional prefix
  (`feat/fix/build/docs/chore/test/refactor`), English prose, the `Co-Authored-By` line required by the
  environment.
- Everything that needs root or the real hardware is run by the user (`! command` in the prompt) and reported
  back; commit after their result. Give them the exact commands, with absolute paths.
- While the user runs a calibration, a verification or a measurement on the machine ("sta facendo", "sto
  calibrando"), run nothing that loads the CPU (selftest, `make check`, GUI smoke, package builds,
  screenshots): only edit and commit what is already verified, list the checks that are pending and run
  them when the user says it finished. The calibrations measure stability and performance per watt on the
  same CPU: extra load skews them.
- Never push: the user pushes. Tags at the end of every phase verified on hardware; before the push the user
  may ask to move the tag and `main` ("sposta tag e main"); after the push never.
- Safety before features ("non voglio che mi esploda il computer"): see "Safety" in the plan and the
  hardware invariants below. In doubt, refuse the write (fail closed) and explain why.
- The user's machine is the only test hardware: AMD Ryzen 7 9800X3D (Granite Ridge), ASUS ROG STRIX X870E-H,
  Fedora 44, KDE Plasma Wayland, Secure Boot on (the akmods MOK key is enrolled), NCT6799D fan chip, AIO with
  the pump on pwm2. Ryzen Control 0.8.0 is installed and in use there, with calibrated profiles (custom
  `new-auto`): Silicon Control must take them over (plan, phase 0) and the two must never run together.
- Large independent work (research, a backend) can go to subagents in worktrees; review their commits with
  the safety rules first, then merge; README, CLAUDE.md and the plan are updated by the main session.

## Lessons from the hardware (inherited from Ryzen Control)

Measured on the 9800X3D; they apply to every backend that writes limits or runs calibrations.
The PM table reflects a new limit after tens of ms → readback with
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

## Inherited from Ryzen Control (the imported code, old names)

Accurate for the code as imported; update these sections as the plan's steps change it. Phase numbers in
them are Ryzen Control's, not this plan's.

### Layout

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

### Commands

Without hardware or root (run before every commit):

```sh
python3 ryzenctl selftest       # fake backend; encodings, validation, ceilings, profiles, baseline, crash-guard, serve (~3 s)
make check                      # VERSION match + Italian catalogs + selftest + layout in a temp root + units/udev/desktop/metainfo validation + GUI smoke en/it
make driver-check               # builds the driver in a copy outside the repo (kbuild does NOT accept spaces in the path: `make -C ryzen_smu` fails here)
make rpm                        # tarball from HEAD (only what is committed) + RPM in dist/; rpmlint NOT installed
make deb / make arch            # the same tarball, .deb / Arch package built and checked in a podman container
RYZENCTL_ROOT=/tmp/fake python3 ryzenctl boot   # CLI on the fake backend (state in $ROOT/fake_smu.json)
RYZENCTL_ROOT=$(mktemp -d) RYZENCTL_FAKE_FAMILY=vermeer python3 ryzenctl status   # another fake CPU: a key of Fake.VARIANTS, a fresh root each
python3 ryzen-control --mock    # GUI without driver or pkexec, on the repo's ryzenctl (state kept in $XDG_RUNTIME_DIR/ryzen-control-mock unless RYZENCTL_ROOT)
make locales && RYZEN_CONTROL_LOCALEDIR=build/locale LANGUAGE=it python3 ryzen-control --mock   # the repo's Italian catalogs (otherwise the installed ones)
make screenshots                # docs/screenshots/*.png from a fresh fake backend (regenerate after visible UI changes)
```

No per-case runner: `selftest` always runs everything (its main cases, then `selftest_watchdog`,
`selftest_variants`, `selftest_laptop`) and the first failing `assert` stops it with a traceback. `make check`
opens the GUI twice on the display (`--mock --smoke`, English and Italian, 120 s timeout each): it needs the
graphical session. Without `RYZENCTL_ROOT`, `ryzenctl` acts on the real machine, and `ryzen-control` without
`--mock` runs `pkexec` on the `ryzenctl` next to it (the repo's) against the real CPU: both are the user's to run.

Translations: no GNU gettext tools here (`xgettext`, `msgmerge`): a new `_()` string gets its entry in
`po/<domain>/it.po` by hand. `po/msgfmt.py` skips untranslated and fuzzy entries silently; `po/check.py` (in
`make check`) fails on an `it.po` that misses a `_("…")` literal of the source named after its domain, has it
fuzzy or keeps an unused entry, and on a `_()` of a non-literal.

On hardware (the user runs them, with `! command`; commit after their result): checklist in
README "Hardware verification".

Not on this machine: `dpkg-buildpackage`, `lintian`, `namcap` (run in containers: `make deb`, `make arch`),
`stress-ng`. The deb/Arch packages are container-tested only: the README says so.

### Architecture

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
  (one JSON-array line per request, one `{"ok":…}` line as reply; `boot/shutdown/resume/serve/selftest`
  denied via serve, `SERVE_DENY`). A new command = a `cmd_*` function + an entry in `COMMANDS` (+ in
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

### Hardware invariants (non-negotiable)

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

- Branches `dev` (development) and `main` (releases only). No remote yet; when the user creates it, the
  user pushes (`git push origin main dev vX.Y.Z`), never push from here.
- Release: `main` gets a `--no-ff` merge of `dev` titled "Version X.Y.Z: …" and the annotated tag `vX.Y.Z`
  ("Silicon Control X.Y.Z"); the tag version is `VERSION` in the Makefile, the RPM spec, debian/changelog and
  PKGBUILD (`make check` enforces it). A pushed tag starts the release workflow (RPM, deb, Arch built in
  containers, one job publishes them); GitHub releases are immutable, so a pushed tag is never moved. `gh` is
  not installed: check the runs and the assets with curl on api.github.com.
- Deliberate simplifications with a known ceiling are marked with a `# ponytail:` comment.
