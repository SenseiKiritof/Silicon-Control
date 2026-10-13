# Plan: "Silicon Control" — CPU power, boost, temperature limit, undervolt and fans on Linux, every vendor

Revision 1 (2026-10-13): created from Ryzen Control v0.8.0 at the user's request: "un programma che usa
questo come base ma per tutte le cpu, non solo AMD". Name chosen by the user among the proposals (Silicon
Control; alternatives were Tempra and Calibro).

Revision 2 (2026-10-13): the open decisions confirmed by the user, one question each (moved to "Decisions
taken").

## Context

Ryzen Control (`../Ryzen Control`, v0.8.0, public on GitHub) is a Ryzen Master-style tool for Linux: a root
helper `ryzenctl` (Python stdlib, the trust boundary), a GTK4/libadwaita GUI `ryzen-control` with a tray
icon, systemd units, the vendored `ryzen_smu` driver built by DKMS, RPM/deb/Arch packages and a release
workflow. What makes it different from other Linux tools: per-chip automatic calibration (Curve Optimizer
search, final pass, performance-per-watt knee), a crash-guard that never re-applies a profile after a crash
without the user's choice, a baseline captured at every boot that is the ceiling of every value, readback of
every write, modes (Default, Quiet, Performance, Eco, Auto, Boost, Custom), fan control on the BIOS curves.
Verified on the user's Ryzen 7 9800X3D only; the other AMD families (Zen–Zen 5 desktops, APUs, laptops) are
"expected".

Goal: the same application for every CPU — AMD as today, Intel, and any other CPU through the kernel's
generic interfaces — without giving up any of the safety rules.

Constraint: the only test hardware is the user's AMD 9800X3D. Intel and the generic backend can be verified
on fake backends only, unless the user gets access to other machines; their families stay "expected" until
an owner runs `hwtest`, exactly as for the AMD families today.

## Decisions taken

- Name **Silicon Control**: the helper `siliconctl`, the GUI `silicon-control`, the app id
  `io.github.senseikiritof.SiliconControl` (reverse DNS under the GitHub account, accepted by Flathub; the old
  `org.ryzencontrol` is not a domain we own). Vendor names stay out of the product name (Ryzen, Intel and Core
  are trademarks).
- Fresh git history: the first commit imports Ryzen Control v0.8.0 unchanged; the old history stays in
  `../Ryzen Control`.
- License unchanged: GPL-3.0-or-later, the vendored ryzen_smu GPL-2.0-only.
- Same stack and constraints: Python ≥ 3.9 stdlib for the helper, PyGObject + GTK4 + libadwaita ≥ 1.5 for the
  GUI, no test framework (`selftest` on fake backends), one `make install` behind every package.
- Version numbering starts again at **0.1.0** (new name, new project).
- Ryzen Control is frozen at 0.8.x (fixes only) and superseded: the Silicon Control packages replace it and
  import its data (phase 0, step 2).
- Scope: AMD + Intel + a **generic** backend that uses only kernel interfaces and therefore also covers ARM and
  anything else; no vendor-specific code for ARM.
- Intel test hardware: none for now ("ad oggi no, ma vedremo"). Intel ships fake-tested and "expected" until an
  owner runs `hwtest`.
- GitHub repository `SenseiKiritof/Silicon-Control`, created by the user at phase 4: until then everything stays
  local and the first public release is already multi-vendor. The packages' URLs point there from phase 0.
- The internal protocol keys with Italian names (`canale`, `modo`, `curva`, `ventola`, `pompa`, `instabile`)
  stay: they are stored in the user's settings and profiles, and renaming them would mean migrating data.

## Target architecture

Unchanged model: GUI as the user → `pkexec siliconctl serve` (root, validates everything) → kernel
interfaces; the same CLI and profile grammar; systemd `boot`/`shutdown`/`resume`/`reapply` units; markers,
baseline, profiles = baseline + own lines; one fake backend per variant in the selftest.

Backends, chosen at runtime from `/proc/cpuinfo` (`vendor_id`, family, model) and what the kernel exposes:

- **amd** — the current code: the `ryzen_smu` driver and the per-codename SMU allowlist (`FAMILIES`).
  Behaviour unchanged; still the only verified backend.
- **intel** — to research before writing code (phase 3): power limits PL1/PL2 through the kernel powercap
  (`/sys/class/powercap/intel-rapl:0/constraint_*`, and the `intel-rapl-mmio` mirror where present: which one
  the firmware honours, and the lock bit), the TCC offset (lower throttle temperature) through the
  `intel_tcc_cooling` cooling device or `tcc_offset_degree_celsius` of the processor thermal device, boost
  through `intel_pstate/no_turbo`, maximum frequency through cpufreq, undervolt through the OC mailbox
  (MSR 0x150: core and cache planes, negative offsets only) where the CPU and the BIOS allow it.
- **generic** — kernel interfaces only, any CPU: cpufreq maximum frequency, boost switch, EPP / power
  profiles, powercap where writable, hwmon and thermal-zone temperatures, power from RAPL energy or hwmon
  where present, fans through the hwmon support that already exists. Gives Default, Quiet and Performance on
  every CPU, and the efficiency knee where power can be measured.

A **capability model**: each backend declares what it can do (curve per core or offset per plane, which
power limits and their names, maximum frequency, temperature limit, boost, power profile, telemetry fields);
the CLI refuses the rest, the presets and calibrations use what is there, and the GUI builds its pages and
rows from it (today it already hides what an AMD family lacks: generalise that).

Code organisation: keep the single-file helper while it stays navigable (ponytail: fewest files); if it has
to be split, a private module directory under `/usr/lib/silicon-control/` with the entry point in
`/usr/bin`, decided in phase 1, not before.

## Safety (carried over and extended)

- Every rule of the Ryzen Control "Hardware invariants" stays for the amd backend.
- Shared by every backend: the baseline of this boot as the ceiling of every value (above it only with an
  explicit unlock and a warning), readback of every write (mismatch → one retry → baseline value → error), the
  crash-guard markers written before every write that differs from the baseline, fail closed when something
  cannot be read or verified, the hardware watchdog during calibrations, the laptop power-source rules and
  `reapply` with its give-up.
- Intel undervolt: only negative offsets with a floor (a knob at the top of the file, like the CO range),
  core and cache planes set together where the CPU needs it, never the GPU, system agent or I/O planes at
  first, never the fixed ("override") voltage mode, never on a CPU whose mailbox does not read back the
  written offset (locked by the BIOS or by the Plundervolt mitigations: refused, never forced).
- Intel limits: PL1/PL2 never above the baseline without unlock, never below a floor (like PPT ≥ 45 W today;
  the floor per segment comes from the research); a locked register is refused; the TCC offset only lowers the
  throttle temperature.
- Kernel lockdown: with Secure Boot (the user's case) the kernel refuses writes through `/dev/cpu/*/msr`. Use
  the kernel's own sysfs interfaces (powercap, thermal) wherever they exist; the undervolt then needs a small
  signed kernel module for the OC mailbox (DKMS + MOK, as for ryzen_smu) or is not offered. Never suggest
  turning Secure Boot or lockdown off as the default path. Recent kernels also warn about raw MSR writes
  (`msr.allow_writes`): to verify in the research.
- Never: memory, FCLK/BCLK, ratio overclocking, raising any limit by analogy with another family or vendor;
  the same register or command number can mean different things per generation.

## Phases and commits

Each phase ends with a tag after the user's check on the 9800X3D (regression of the amd backend); the
backends nobody here can run stay "expected".

### Phase 0 — rename and migration → first tag

| # | Commit | Verification |
|---|---|---|
| 1 | `chore: rename to Silicon Control` — binaries, app id, `/etc`, `/var/lib`, `/run` paths, kernel parameter `siliconctl.off`, gettext domains (msgids with the name, Italian catalogs), systemd units, udev rule, modprobe and polkit files (action id), desktop, metainfo (`<replaces>` the old id), icon, tray, env vars of the fake backend (`SILICONCTL_ROOT`, `SILICONCTL_FAKE_FAMILY`), packaging (spec, debian, PKGBUILD, build scripts), release workflow, README, screenshots | `make check`, `make rpm` / `deb` / `arch`, GUI smoke en/it; `grep -ri ryzen` finds only the driver, the AMD family names, the migration code and history notes |
| 2 | `feat: take over from Ryzen Control` — packages replace `ryzen-control` (RPM `Obsoletes`, deb `Replaces/Breaks`, Arch `replaces/conflicts`); bump `DRV_VERSION` so the old package's `%preun`, which removes `ryzen_smu/0.4.1` from dkms, cannot remove the new module; `boot` imports `/etc/ryzenctl` (settings, profiles) and `/var/lib/ryzenctl` (calibration data, `crashed` marker) when the new directories do not exist yet; the polkit trust rule and the user's login autostart entry renamed; the old kernel parameter `ryzenctl.off` still honoured | selftest with a fake Ryzen Control state; the user installs over Ryzen Control 0.8.0 on the 9800X3D: profiles and calibrations kept (`new-auto` applies), `hwtest` ok, one service only |

### Phase 1 — backends and capabilities, AMD unchanged

| # | Commit | Verification |
|---|---|---|
| 3 | `refactor: vendor backends and capabilities` (amd only behind it) | selftest identical on every AMD fake variant; the user's `hwtest` on the 9800X3D |
| 4 | `feat(gui): pages and rows from the capabilities` | GUI smoke on every fake variant, screenshots |

### Phase 2 — generic backend

| # | Commit | Verification |
|---|---|---|
| 5 | `feat: generic backend (cpufreq, boost, EPP, powercap, hwmon)` + fake variant | selftest; the user forces the generic backend on the 9800X3D (an env var or a setting) for presets, boost and fans |

### Phase 3 — Intel

| # | Commit | Verification |
|---|---|---|
| 6 | research by agents, then a plan revision: per generation (Haswell … Arrow Lake, desktop and laptop) the power-limit, TCC and undervolt interfaces, locks, floors, how to read back; Linux tools to learn from (intel-undervolt, undervolt.py, throttled, thermald) | sources in the revision |
| 7 | `feat: Intel power limits, TCC offset, boost` (no voltage) + fake variants | selftest; owners' `hwtest` |
| 8 | `feat: Intel undervolt and its calibration` (only where the mailbox reads back) | selftest with locked and unlocked fakes; owners' `hwtest` |

### Phase 4 — README tables per vendor and release

README "Processors" by vendor (verified / expected / not supported), the hwtest procedure for owners, the
release workflow, the GitHub repository when the user creates it.

## Notes for the first session

- Read `CLAUDE.md`, this plan and, for the history of a piece of code, `../Ryzen Control` (its CLAUDE.md, its
  plan revisions and `git log`).
- The rename touches almost every file (`grep -rIl -E "ryzenctl|ryzen-control|ryzencontrol|RyzenControl|Ryzen
  Control"` lists them): do it in one commit with `make check` green, so the next steps start from the new
  names; leave the AMD family names (Granite Ridge, …) and the `ryzen_smu` driver alone.
