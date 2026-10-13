# Plan: "Silicon Control" — CPU power, boost, temperature limit, undervolt and fans on Linux, every vendor

Revision 1 (2026-10-13): created from Ryzen Control v0.8.0 at the user's request: "un programma che usa
questo come base ma per tutte le cpu, non solo AMD". Name chosen by the user among the proposals (Silicon
Control; alternatives were Tempra and Calibro).

Revision 2 (2026-10-13): the open decisions confirmed by the user, one question each (moved to "Decisions
taken").

Revision 3 (2026-10-13): phase 0, step 2 without the `DRV_VERSION` bump. Measured on the 9800X3D: with 0.4.2 (same
source) dkms 3.4.3 refused to install a module whose `MODULE_VERSION` (0.1.7) equals the installed one, and
ryzen-control's `%preun` then removed `ryzen_smu/0.4.1`, the only installed copy. With the same version the new
package's `dkms add --rpm_safe_upgrade` cancels that removal, as in Ryzen Control's own upgrades.

Revision 4 (2026-10-13): phases 1 and 2 merged, the user's choice. The AMD code is already driven by its
capabilities: the family entry declares the SMU allowlist and the PM map, the baseline captures only what can be
read, and every write needs its baseline key (Pinnacle Ridge, with no SMU command, already runs on boost, power
profile and fans alone, and the selftest proves it). A backend class with one implementation would add nothing:
the generic backend is a descriptor like a family entry, with no SMU command and no PM table, chosen when the AMD
gate does not apply or when forced, plus the kernel's knobs; the capabilities reach the GUI through `status` as
today. The helper stays one file.

Revision 5 (2026-10-13): phase 3, step 5 done: the Intel research by three agents (power limits; TCC offset,
turbo and telemetry; undervolt), in "Intel: research" below with its sources, and the design of steps 6 and 7.

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
- Intel (revision 5, the user's choices): the undervolt is written now although nobody here can test it — shipped
  disabled (an explicit opt-in) and "expected" until an owner's `hwtest`; an active thermald does not block the PL
  and TCC writes but brings a prominent warning; `unlock on` raises PL1/PL2 up to the kernel's `max_power_uw`, never
  on Raptor Lake desktop.
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

Code organisation (decided in revision 4): the helper stays one file while it stays navigable (ponytail: fewest
files; about 5000 lines with the selftest). If it has to be split, a private module directory under
`/usr/lib/silicon-control/` with the entry point in `/usr/bin`.

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

## Intel: research (revision 5)

Kernel sources: torvalds master (7.3-rc7) and the tags named; SDM 325384/335592-093US. "Uncertain" marks forum
reports, conflicting sources or inferences. Everything below works under Secure Boot unless stated: the kernel
drivers write their own registers; lockdown ("integrity") blocks only `/dev/cpu/*/msr` writes, `/dev/mem` and PCI
BAR access. Raw MSR **reads** stay allowed (root, CAP_SYS_RAWIO); `msr.allow_writes` cannot bypass lockdown and
every raw write taints the kernel since 5.9.

### Power limits (PL1, PL2) — powercap

- Zones: `intel-rapl:0` (package, MSR 0x610 through `intel_rapl_msr`) and, where the processor thermal device
  binds, its MMIO mirror `intel-rapl-mmio:0` (MCHBAR 0x59A0): unconditionally on ADL, RPL, MTL, ARL-S, LNL and
  later; on SKL/ICL/TGL only with DPTF firmware (an ACPI `PPCC`). The hardware applies the **lower** of the two
  (Intel's coreboot code for Apollo Lake; thermald acts accordingly); as a general rule uncertain, so both are
  written with the same value, as coreboot programs them.
- Files: `constraint_N_name` (`long_term` = PL1, `short_term` = PL2, `peak_power` = PL4: match by name, the index
  follows the limits present), `constraint_N_power_limit_uw` and `_time_window_us` (0644), `_max_power_uw` (TDP
  for PL1, POWER_INFO max for PL2; PL4's is a kernel heuristic), `enabled`, `energy_uj` (root only since 5.10).
- Readback: every read hits the register (no cache, no delay as on AMD's PM table). Writes floor to the power unit
  (MSR 0x606, usually 1/8 W) and **silently truncate** values that overflow the 15-bit field (PL4: 13 bits). Time
  windows round down to a 2^Y·(1+Z/4) grid; the PL2 window may be hard-wired.
- Lock (0x610 bit 63, MMIO bit 63; the hardware ignores writes silently): the kernel reads it **once at probe**,
  logs "package-0:package:long_term locked by BIOS" (≥ 6.5; both zones are named package-0) and then refuses the
  write with EACCES, which powercap turns into **ENODATA**. Probe without changing anything: write back the value
  just read; ENODATA = locked. A lock set after the probe, PL4 and `enabled` fail silently: only a readback
  catches them. `enabled` reads 0 whenever PL1 is locked.
- Who rewrites them: laptop ECs (Lenovo T480/X1C6 reset PL1/PL2: throttled re-applies every 5 s, 30 s on
  battery), firmware clamps on battery (uncertain report on MTL-H), **thermald** on DPTF laptops (sets PL1 at
  start, lowers it as a cooling device, applies the OEM's targets in adaptive mode, restores at exit), the kernel
  after S3 (values only, no hibernation hook).
- Floors: none in hardware (PL4 at 0.125 W forced the lowest performance). Sources of a floor: POWER_INFO min
  power (an MSR read), the OEM's PPCC limits on DPTF laptops (`/sys/bus/pci/devices/0000:00:04.0/power_limits/
  power_limit_{0,1}_{min,max}_uw`), ARK's "minimum assured power" / cTDP-down. thermald's lowest PL1: PPCC min,
  otherwise 50 % of max. Nothing enforces PL2 ≥ PL1 (coreboot clamps it).
- Desktop boards often ship PL1/PL2 "unlimited" (field maximum ≈ 4096 W): a motherboard value, like
  `board_limits` on AMD. Raptor Lake desktop (06_B7/06_BF): Intel's Vmin-shift root cause includes power settings
  above its guidance; microcode 0x125/0x129/0x12B/0x12F; mobile, LNL and ARL unaffected.

### Temperature limit — TCC offset

- MSR 0x1A2: TjMax bits 23:16, offset from bit 24, lock bit 31; 0xCE bit 30 = offset programmable. Throttle point
  = TjMax − offset; it only ever lowers it. Bits 6:0 can hold a RATL averaging window (the limit becomes an
  average).
- `tcc_offset_degree_celsius` of the processor thermal device (`/sys/bus/pci/devices/*/tcc_offset_degree_celsius`):
  reads the MSR (a real readback); ≥ 5.14 checks range and lock (EACCES when not programmable, EPERM when locked;
  **5.4–5.13 had no check and cleared bits 31:24**: refused); ≥ 6.3 restores the offset after suspend. It exists
  only with a DPTF `PPCC` (laptops mostly; desktops usually lack it, uncertain).
- `intel_tcc_cooling` (≥ 5.13): cooling device of type "TCC Offset", `cur_state` = offset (readback),
  `max_state` = width; registers only on listed models when unlocked at load; no restore after resume. Never on
  Rocket, Meteor or Lunar Lake.
- Offset width per model since 6.11: none on Sandy/Ivy/Haswell client; 4 bits on HSW-X/BDW-X/SKX; 6 bits from
  Broadwell to Raptor Lake; unlisted models (MTL, LNL, ARL, PTL) default to 7 bits while turbostat uses 6:
  uncertain, so the offset is capped at 63.
- TjMax: coretemp `temp1_crit` (0x1A2 bits 23:16, re-read at every access). thermald's `--workaround-enabled`
  (off by default) rewrites offsets above 10 to 5, raising the throttle point.

### Turbo, frequency, telemetry

- `intel_pstate` (active with HWP, passive without since 5.8): `no_turbo` is global and reads back its flag; a
  write returns EPERM when the BIOS disabled turbo; **setting it lowers every policy's `cpuinfo_max_freq`** and
  clamps `scaling_max_freq` (restored when cleared). `max_perf_pct` is not visible in `scaling_max_freq` in active
  mode: never written. Without HWP and with cTDP, a cap between the non-turbo and turbo maximum is raised to
  `cpuinfo_max_freq` (a readback above the written value). Hybrid parts: per-policy maxima from HWP_CAP, changing
  at runtime on HWP interrupts. acpi-cpufreq's `boost` (global, per policy since 6.6) toggles MISC_ENABLE bit 38.
- Other writers: power-profiles-daemon and tuned-ppd (Fedora's default since F41) own EPP and may set `no_turbo`;
  thermald writes `max_perf_pct` and `no_turbo`.
- Telemetry without root: coretemp `Package id N` / `Core N`, the `x86_pkg_temp` zone, throttle counters
  (`cpuN/thermal_throttle/*`), the TCC offset. Root only: RAPL `energy_uj` (package, core, uncore; dram on servers;
  psys `intel-rapl:1` on Skylake+ laptops, uncertain). No kernel file exposes the core voltage (MSR 0x198[47:32]
  /2^13 V, an estimate, readable as root).

### Undervolt — OC mailbox (MSR 0x150)

- Not in the SDM. Layout (Plundervolt, undervolt.py): bit 63 busy, bits 39:32 command (0x10 read, 0x11 write),
  bits 42:40 plane (0 core, 1 GPU, 2 cache; 3 and 4 disputed), bits 31:21 offset in 1/1024 V (11-bit two's
  complement). Intel's own `turbo_max_3.c` polls bit 63 (~3 µs) and treats a nonzero bits 39:32 as failure. Core and
  cache share one rail ("the higher voltage of both is applied"): both always written with the same value. The
  voltage drops 0.2–0.4 ms after the write; a full power-off resets it.
- Locks: Plundervolt (CVE-2019-11157, INTEL-SA-00289, 6th–10th gen): BIOS updates disable the mailbox, a **locked
  mailbox accepts the write without error and reads back 0**; OC Lock = MSR 0x194 bit 20; 12th gen and later
  "Undervolt Protection" (UVP: IA32_ARCH_CAPABILITIES bit 23 → IA32_OVERCLOCKING_STATUS 0x195 bit 1), enabled by
  most OEMs, Intel advises against disabling it. Detectable without writing (MSR reads).
- Per generation: Haswell/Broadwell open; Skylake–Comet Lake desktop usually open, laptops often locked by 2020 OEM
  BIOS updates; Tiger Lake U mostly locked (uncertain); Alder/Raptor Lake S/HX only with UVP off; 06_9A, 06_BA,
  Meteor Lake, Lunar Lake: no; Arrow Lake: unverified. Raptor Lake S with Vmin shift may fail even at 0 mV. CEP
  (12th–14th gen, on by default) lowers clocks instead of crashing: an undervolt can lose performance.
- No upstream or narrow out-of-tree module exposes 0x150 (Intel declined such kernel code: the commands are model
  specific). Under Secure Boot an undervolt therefore needs our own MOK-signed DKMS module (like ryzen_smu).
- Instability: Plundervolt measured faults ~30 mV before the crash (−130 vs −161 mV on an i3-7100U), worse when hot;
  chips of the same model differ by 90 mV. Tools' floors: VoltageShift −250 mV, the others none.

### Design of step 6 (power limits, TCC offset, turbo; no voltage)

- An `INTEL` descriptor (backend "intel"), chosen by `family()` for `GenuineIntel` (vendor_id in /proc/cpuinfo): the
  generic backend plus the knobs below where the kernel exposes them, with a small per-model table for the special
  rules. No raw MSR write, ever; no MSR read in step 6 either (the kernel's errors and the readback decide).
- `pl1`, `pl2` (W): both zones written with the same whole-watt value (exact on the 1/8 W grid), matched by
  constraint name; baseline = the effective value (the lower zone); ceiling = baseline, with `unlock on` up to the
  constraint's `max_power_uw` where that is higher (never on Raptor Lake desktop); floor = max(PPCC min where
  present, 50 % of the baseline PL1, a knob `INTEL_PL_MIN`); PL2 ≥ PL1 kept in the
  write order (lowering: PL1 first; raising: PL2 first, like slow/fast on the APUs). Locked (ENODATA on the no-op
  write-back) or unlimited (≥ 4000 W) → the key is not in the capabilities, with the reason. Never written:
  `enabled`, `peak_power`, time windows, psys; `intel_rapl_msr` never unloaded.
- `tjmax` (°C, the same key as AMD's, so the presets' Tjmax 80 works): offset = TjMax − value through the int340x
  attribute (≥ 5.14) or the "TCC Offset" cooling device; ceiling = the baseline's limit (never raised), floor
  TJMAX_MIN, offset ≤ min(63, max_state); every error code refuses; the resume unit re-applies (the cooling device
  does not restore it).
- `boost`: `intel_pstate/no_turbo` (inverted) where there is no cpufreq `boost` file — this also completes the
  generic backend on Intel; never turned on when the baseline had it off; the baseline's FMax ceiling taken with
  turbo on.
- Firmware and daemons: laptops use the existing `reapply` (drift → re-applied, give-up after 3 corrections in
  2 minutes); an active thermald (it drives RAPL and TCC as cooling devices and may rewrite them) does not block the
  writes but is warned about prominently: in `status`, in the output of every PL and TCC write, and in a GUI banner.
- Raptor Lake desktop (06_B7, 06_BF): no raise above the baseline ever; a warning in `status` when the microcode of
  06_B7 is older than 0x12B.
- Fake variants: `intel` (a desktop with both zones, the TCC attribute, intel_pstate), `intel-locked` (ENODATA on PL,
  EPERM on TCC), `intel-laptop` (battery, the firmware rewriting PL1); the fake's sysfs writes raise the kernel's
  errors.

### Step 7 (undervolt): written untested, shipped disabled

Done in this phase although nobody here owns an Intel CPU (the user's choice): disabled until an explicit opt-in,
"expected" on every model until an owner's `hwtest`, compiled and loaded here only to prove it refuses an AMD CPU.
A MOK-signed DKMS module with one attribute (the core+cache offset in mV): planes 0 and 2 only, always equal;
read-modify-write keeping bits 20:0; busy poll ≤ 1 ms; success only with completion code 0 **and** a matching
readback; a probe at every boot with a value different from the baseline (−2 mV), since a locked mailbox reads
back 0; a model allowlist (Haswell–Comet Lake, Ice/Tiger/Rocket Lake, 06_97/B7/BF with UVP off; refused:
pre-Haswell, Atom, 06_9A, 06_BA, MTL, LNL, Xeon, ARL until tested, 06_B7 below microcode 0x12B); refused while UVP
(0x10A[23] ∧ 0x195[1]) or OC Lock (0x194[20]) is set, or while `/dev/sgx_enclave` exists (it would reopen
Plundervolt). Floor −150 mV in the module, −125 mV in siliconctl, 5 mV steps; calibration with stress-ng
`--verify` (light, single-thread, idle-transition and AVX phases, hot), any new MCE counted as a failure, the
performance per watt measured (CEP), the hardware watchdog kept.

### Sources

- Kernel: drivers/powercap/intel_rapl_common.c, intel_rapl_msr.c, powercap_sys.c; drivers/thermal/intel/
  int340x_thermal/processor_thermal_{device,device_pci,device_pci_legacy,rapl}.c, intel_tcc.c, intel_tcc_cooling.c;
  drivers/cpufreq/intel_pstate.c, acpi-cpufreq.c; drivers/hwmon/coretemp.c; arch/x86/kernel/msr.c;
  drivers/platform/x86/intel/turbo_max_3.c (https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git);
  commits 8365a898fe53, 3fb0eea8a1c4, 949dd0104c49, f442bd274217, a60ec4485f1c, 964209202ebe, 081690e94118,
  95f5e95f41df, a7e1f67ed29f; Documentation/driver-api/thermal/intel_dptf.rst.
- Intel: SDM vol. 3B §17.10.3 and vol. 4 (https://cdrdv2.intel.com/v1/dl/getContent/671447,
  https://cdrdv2.intel.com/v1/dl/getContent/671098); INTEL-SA-00289; support articles 000094219 and 000093813 (UVP);
  the 13th/14th gen instability root cause and microcode posts on community.intel.com; ARK pages of the CPUs in the
  table; FSP headers (github.com/intel/FSP).
- Tools: github.com/intel/thermal_daemon, github.com/erpalma/throttled, github.com/kitsunyan/intel-undervolt
  (issues 24, 43, 57, 61, 74), github.com/georgewhewell/undervolt (issues 9, 137, 193), github.com/sicreative/
  VoltageShift, github.com/LLNL/msr-safe, power-profiles-daemon, TuneD; coreboot src/soc/intel/common/block/
  power_limit; Plundervolt (https://plundervolt.com/doc/plundervolt.pdf); XMG's undervolting guide; AnandTech on
  TDP and turbo.

## Phases and commits

Each phase ends with a tag after the user's check on the 9800X3D (regression of the amd backend); the
backends nobody here can run stay "expected".

### Phase 0 — rename and migration → first tag

| # | Commit | Verification |
|---|---|---|
| 1 | `chore: rename to Silicon Control` — binaries, app id, `/etc`, `/var/lib`, `/run` paths, kernel parameter `siliconctl.off`, gettext domains (msgids with the name, Italian catalogs), systemd units, udev rule, modprobe and polkit files (action id), desktop, metainfo (`<replaces>` the old id), icon, tray, env vars of the fake backend (`SILICONCTL_ROOT`, `SILICONCTL_FAKE_FAMILY`), packaging (spec, debian, PKGBUILD, build scripts), release workflow, README, screenshots | `make check`, `make rpm` / `deb` / `arch`, GUI smoke en/it; `grep -ri ryzen` finds only the driver, the AMD family names, the migration code and history notes |
| 2 | `feat: take over from Ryzen Control` — packages replace `ryzen-control` (RPM `Obsoletes`, deb `Replaces/Breaks`, Arch `replaces/conflicts`); `DRV_VERSION` unchanged, so the `dkms add --rpm_safe_upgrade` of the new `%post` cancels the `dkms remove` of the old `%preun` (revision 3); `boot` imports `/etc/ryzenctl` (settings, profiles) and `/var/lib/ryzenctl` (calibration data, `crashed` marker) when the new directories do not exist yet; the polkit trust rule and the user's login autostart entry renamed; the old kernel parameter `ryzenctl.off` still honoured | selftest with a fake Ryzen Control state; the user installs over Ryzen Control 0.8.0 on the 9800X3D: profiles and calibrations kept (`new-auto` applies), `hwtest` ok, one service only |

### Phase 1 — generic backend, capabilities and the GUI from them (phases 1 and 2 merged, revision 4)

| # | Commit | Verification |
|---|---|---|
| 3 | `feat: generic backend (cpufreq, boost, EPP, powercap, hwmon)` + fake variant: a descriptor without SMU commands, chosen when ryzen_smu, a known codename or a supported layout is missing (HX laptops included) or when forced; maximum frequency through cpufreq, temperatures from hwmon and thermal zones, package power from RAPL energy | selftest identical on every AMD fake variant, and on the generic fake; the user forces the generic backend on the 9800X3D for presets, boost and fans |
| 4 | `feat(gui): pages and rows from the capabilities` | GUI smoke on every fake variant, screenshots |

### Phase 2 — merged into phase 1 (revision 4)

### Phase 3 — Intel

| # | Commit | Verification |
|---|---|---|
| 5 | research by agents, then a plan revision: per generation (Haswell … Arrow Lake, desktop and laptop) the power-limit, TCC and undervolt interfaces, locks, floors, how to read back; Linux tools to learn from (intel-undervolt, undervolt.py, throttled, thermald) — done, revision 5 | sources in the revision |
| 6 | `feat: Intel power limits, TCC offset, boost` (no voltage) + fake variants | selftest; owners' `hwtest` |
| 7 | `feat: Intel undervolt and its calibration` (only where the mailbox reads back), disabled until an opt-in | selftest with locked and unlocked fakes; the module built here and refusing the AMD CPU; owners' `hwtest` |

### Phase 4 — README tables per vendor and release

README "Processors" by vendor (verified / expected / not supported), the hwtest procedure for owners, the
release workflow, the GitHub repository when the user creates it.

## Notes for the first session

- Read `CLAUDE.md`, this plan and, for the history of a piece of code, `../Ryzen Control` (its CLAUDE.md, its
  plan revisions and `git log`).
- The rename touches almost every file (`grep -rIl -E "ryzenctl|ryzen-control|ryzencontrol|RyzenControl|Ryzen
  Control"` lists them): do it in one commit with `make check` green, so the next steps start from the new
  names; leave the AMD family names (Granite Ridge, …) and the `ryzen_smu` driver alone.
