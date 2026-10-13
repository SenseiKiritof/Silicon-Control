# Silicon Control — the single source of truth for the installed layout. Packages (RPM, deb, Arch)
# call `make install DESTDIR=…`; `install-cli` / `install-gui` / `install-dkms-src` /
# `install-locales` are the pieces.
VERSION := 0.4.0
# DKMS module version: bump ONLY when ryzen_smu/ changes (a new /usr/src directory means a
# rebuild + dracut, about a minute at upgrade time). Same value as %drv_version in the spec. Also bump the
# driver's MODULE_VERSION: dkms does not install a module whose version equals the installed one, and the old
# package's %preun then removes the only installed copy (seen in the takeover of ryzen-control with 0.4.2).
DRV_VERSION := 0.4.1
APPID := io.github.senseikiritof.SiliconControl
PREFIX ?= /usr
DESTDIR ?=

BIN := $(DESTDIR)$(PREFIX)/bin
UNITDIR := $(DESTDIR)$(PREFIX)/lib/systemd/system
PRESETDIR := $(DESTDIR)$(PREFIX)/lib/systemd/system-preset
UDEVDIR := $(DESTDIR)$(PREFIX)/lib/udev/rules.d
MODPROBEDIR := $(DESTDIR)$(PREFIX)/lib/modprobe.d
POLKITDIR := $(DESTDIR)$(PREFIX)/share/polkit-1/actions
APPDIR := $(DESTDIR)$(PREFIX)/share/applications
ICONDIR := $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps
METADIR := $(DESTDIR)$(PREFIX)/share/metainfo
LOCALEDIR := $(DESTDIR)$(PREFIX)/share/locale
AUTOSTARTDIR := $(DESTDIR)/etc/xdg/autostart
ETCDIR := $(DESTDIR)/etc/siliconctl
STATEDIR := $(DESTDIR)/var/lib/siliconctl
DKMS_SRC := $(DESTDIR)$(PREFIX)/src/ryzen_smu-$(DRV_VERSION)
TMPROOT := $(or $(TMPDIR),/tmp)/silicon-control-check

# Translations: po/<domain>/<lang>.po → build/locale/<lang>/LC_MESSAGES/<domain>.mo, compiled by
# po/msgfmt.py (standard library only: no GNU gettext needed to build or install).
PO := $(wildcard po/*/*.po)
MO := $(foreach p,$(PO),build/locale/$(notdir $(basename $(p)))/LC_MESSAGES/$(notdir $(patsubst %/,%,$(dir $(p)))).mo)

.PHONY: all install install-cli install-gui install-dkms-src install-locales locales dkms uninstall check driver-check dist rpm deb arch screenshots

all:
	@echo "Targets: install [DESTDIR=…] (install-cli install-gui install-dkms-src install-locales), locales, dkms, uninstall, check, driver-check, dist, rpm, deb, arch"

install: install-cli $(if $(wildcard silicon-control),install-gui) install-dkms-src install-locales

install-cli:
	install -Dm755 siliconctl $(BIN)/siliconctl
	install -Dm644 -t $(UNITDIR) data/siliconctl.service data/siliconctl-resume.service data/siliconctl-reapply.service \
	  data/siliconctl-reapply.timer
	install -Dm644 -t $(PRESETDIR) data/80-silicon-control.preset
	install -Dm644 -t $(UDEVDIR) data/60-silicon-control.rules
	install -Dm644 data/silicon-control.modprobe.conf $(MODPROBEDIR)/silicon-control.conf
	install -Dm644 -t $(POLKITDIR) data/$(APPID).policy
	install -Dm644 -t $(AUTOSTARTDIR) data/siliconctl-notify.desktop
	install -dm755 $(ETCDIR)/profiles $(STATEDIR)

install-gui:
	install -Dm755 silicon-control $(BIN)/silicon-control
	install -Dm644 -t $(APPDIR) data/$(APPID).desktop
	install -Dm644 -t $(ICONDIR) data/$(APPID).svg
	install -Dm644 -t $(METADIR) data/$(APPID).metainfo.xml

# One .mo per catalog, mirrored under $(PREFIX)/share/locale.
locales: $(MO)


define MO_RULE
build/locale/$(notdir $(basename $(1)))/LC_MESSAGES/$(notdir $(patsubst %/,%,$(dir $(1)))).mo: $(1) po/msgfmt.py
	mkdir -p $$(dir $$@)
	python3 po/msgfmt.py $(1) $$@
endef
$(foreach p,$(PO),$(eval $(call MO_RULE,$(p))))

install-locales: locales
	mkdir -p build/locale && cd build/locale && find . -name '*.mo' -exec install -Dm644 {} $(LOCALEDIR)/{} \;

# Driver source for DKMS (no binaries are shipped: DKMS builds the module on the target kernel).
install-dkms-src:
	install -dm755 $(DKMS_SRC)
	install -m644 -t $(DKMS_SRC) ryzen_smu/drv.c ryzen_smu/smu.c ryzen_smu/smu.h ryzen_smu/Makefile
	sed -e 's/@VERSION@/$(DRV_VERSION)/' -e 's/@CFLGS@//' ryzen_smu/dkms.conf > $(DKMS_SRC)/dkms.conf

# Last resort without a package: `sudo make install && sudo make dkms`.
dkms:
	dkms add ryzen_smu/$(DRV_VERSION) || true
	dkms build ryzen_smu/$(DRV_VERSION) && dkms install ryzen_smu/$(DRV_VERSION)

uninstall:
	-dkms remove ryzen_smu/$(DRV_VERSION) --all
	rm -rf $(DKMS_SRC)
	rm -f $(BIN)/siliconctl $(BIN)/silicon-control
	rm -f $(UNITDIR)/siliconctl.service $(UNITDIR)/siliconctl-resume.service $(PRESETDIR)/80-silicon-control.preset
	rm -f $(UNITDIR)/siliconctl-reapply.service $(UNITDIR)/siliconctl-reapply.timer $(UDEVDIR)/60-silicon-control.rules
	rm -f $(MODPROBEDIR)/silicon-control.conf $(POLKITDIR)/$(APPID).policy $(AUTOSTARTDIR)/siliconctl-notify.desktop
	rm -f $(APPDIR)/$(APPID).desktop $(ICONDIR)/$(APPID).svg $(METADIR)/$(APPID).metainfo.xml
	rm -f $(LOCALEDIR)/*/LC_MESSAGES/siliconctl.mo $(LOCALEDIR)/*/LC_MESSAGES/silicon-control.mo

# Checks that need neither root nor hardware: the Italian catalogs against the sources, pyflakes, selftest,
# layout in a scratch root, units, desktop entries, metainfo, the calibration window over every state
# of the fake backend (needs a display; a fresh fake root each time), once in English, once with
# the Italian catalog, and on the generic and Intel (laptop) backends.
check: locales
	@v=$(VERSION); grep -q "^Version: *$$v$$" packaging/silicon-control.spec && head -1 packaging/debian/changelog | grep -qF "($$v)" \
	  && grep -q "^pkgver=$$v$$" packaging/PKGBUILD && grep -qF "VERSION = \"$$v\"" siliconctl \
	  || { echo "VERSION $$v differs in the spec, debian/changelog, PKGBUILD or siliconctl"; exit 1; }
	python3 po/check.py $(wildcard po/*/it.po)
	python3 -m pyflakes siliconctl silicon-control po/check.py po/msgfmt.py   # undefined names and the like (dnf install python3-pyflakes)
	python3 siliconctl selftest
	rm -rf "$(TMPROOT)" && $(MAKE) install DESTDIR="$(TMPROOT)" >/dev/null
	cd "$(TMPROOT)" && find . -type f | sort
	systemd-analyze --root="$(TMPROOT)" verify --recursive-errors=no siliconctl.service siliconctl-resume.service \
	  siliconctl-reapply.service siliconctl-reapply.timer
	udevadm verify --resolve-names=never data/60-silicon-control.rules
	desktop-file-validate data/siliconctl-notify.desktop data/$(APPID).desktop
	-appstreamcli validate --no-net data/$(APPID).metainfo.xml
	root=$$(mktemp -d) && LANGUAGE=C LC_ALL=C.UTF-8 SILICONCTL_ROOT=$$root timeout 120 python3 silicon-control --mock --smoke; \
	  rc=$$?; rm -rf $$root; exit $$rc
	root=$$(mktemp -d) && LANGUAGE=it LC_ALL=it_IT.UTF-8 SILICON_CONTROL_LOCALEDIR=build/locale SILICONCTL_ROOT=$$root timeout 120 \
	  python3 silicon-control --mock --smoke; rc=$$?; rm -rf $$root; exit $$rc
	for v in generic intel-laptop; do root=$$(mktemp -d) && LANGUAGE=C LC_ALL=C.UTF-8 SILICONCTL_ROOT=$$root SILICONCTL_FAKE_FAMILY=$$v \
	  timeout 120 python3 silicon-control --mock --smoke; rc=$$?; rm -rf $$root; [ $$rc = 0 ] || exit $$rc; done

# README screenshots: the GUI on a fresh fake backend (fan roles, presets, the three calibrations),
# one PNG per page plus the calibration window and a short GIF of an Auto calibration (ImageMagick),
# in English (needs a display; windows flash briefly).
screenshots:
	root=$$(mktemp -d) && LANGUAGE=C LC_ALL=C.UTF-8 SILICONCTL_ROOT=$$root timeout 120 python3 silicon-control --mock --screenshots docs/screenshots \
	  && magick -delay 40 $$root/frames/f-*.png -delay 350 $$root/frames/last.png -loop 0 -resize 720x -layers Optimize docs/screenshots/calibration.gif; \
	  rc=$$?; rm -rf $$root; exit $$rc

# Tarball from the current commit (HEAD): packages are built from what is versioned.
dist:
	mkdir -p dist
	git archive --format=tar.gz --prefix=silicon-control-$(VERSION)/ -o dist/silicon-control-$(VERSION).tar.gz HEAD

# RPM in the standard ~/rpmbuild tree (no spaces in paths); result copied to dist/.
rpm: dist
	rpmdev-setuptree
	cp dist/silicon-control-$(VERSION).tar.gz "$$HOME/rpmbuild/SOURCES/"
	rpmbuild -ba packaging/silicon-control.spec
	cp "$$HOME"/rpmbuild/RPMS/noarch/silicon-control-$(VERSION)-*.rpm dist/
	ls -1 dist/

# deb and Arch packages, built in a container with podman from the committed tree (like `make rpm`);
# the same scripts run in the release workflow.
deb: dist
	podman run --rm -i -v "$(CURDIR)/dist":/out:z docker.io/library/debian:trixie \
	  sh -c 'mkdir /src && cd /src && tar -xz --strip-components=1 --no-same-owner && sh packaging/build-deb.sh /out' \
	  < dist/silicon-control-$(VERSION).tar.gz

arch: dist
	podman run --rm -i -v "$(CURDIR)/dist":/out:z docker.io/library/archlinux:latest \
	  sh -c 'mkdir /src && cd /src && tar -xz --strip-components=1 --no-same-owner && sh packaging/build-arch.sh /out' \
	  < dist/silicon-control-$(VERSION).tar.gz

# kbuild rejects spaces in the path: build a copy of the driver outside the repo.
driver-check:
	rm -rf "$(TMPROOT)-driver" && cp -r ryzen_smu "$(TMPROOT)-driver"
	$(MAKE) -C "$(TMPROOT)-driver" && modinfo -F vermagic "$(TMPROOT)-driver/ryzen_smu.ko"
