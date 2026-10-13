# ryzen_smu driver — vendored copy

- Origin: https://github.com/amkillam/ryzen_smu
- Commit: d2983668300dd2a598e5a7dc40e71ce0678cc270 (2026-08-15, "Fix cpuid include on 7.2+ kernels")
- Copied files: `drv.c`, `smu.c`, `smu.h`, `Makefile`, `dkms.conf`, `LICENSE`, `README.md`,
  `docs/rsmu_commands.md`. Excluded: `lib/`, `userspace/`, `scripts/`, `pics/` (not needed by the module).

## Local changes

- `smu.c`, `smu_update_pmtable_size()`, `CODENAME_GRANITERIDGE` block: added the PM table
  versions 0x621101/0x621102 (0x724 bytes) and 0x621201/0x621202 (0x994 bytes) of the most
  recent AGESA, sizes from ZenStates-Core `Hardware/PowerTable.cs`. Without them the driver
  loads but disables `pm_table` on those firmwares.

## Updating

```sh
git clone https://github.com/amkillam/ryzen_smu /tmp/ryzen_smu && cd /tmp/ryzen_smu && git checkout <new-commit>
diff -ru --exclude=UPSTREAM.md "<repo>/ryzen_smu" /tmp/ryzen_smu   # review, then copy over again and reapply the local changes
```

Note: kbuild does not accept spaces in the path, so `make -C ryzen_smu` fails inside this
repo. To build use `make driver-check` (copy in a temporary directory).
