#!/bin/sh
# Builds the Arch package as root (a container: `make arch`, the release workflow) from the source tree in
# the current directory: makepkg, as an unprivileged user, takes the tag v$VERSION of a local snapshot
# (the PKGBUILD's own source is the GitHub tag); namcap checks it; the package goes to $1 (default: dist).
set -e
out=$(realpath -m "${1:-dist}")
src=$(pwd)
pacman -Syu --noconfirm --needed base-devel git python python-gobject gtk4 libadwaita polkit systemd dkms namcap </dev/null >/dev/null
v=$(sed -n 's/^VERSION := //p' Makefile)
id builder >/dev/null 2>&1 || useradd -m builder
snap=/home/builder/src pkg=/home/builder/pkg
mkdir -p "$snap" "$pkg"
tar -C "$src" --exclude=.git -c . | tar -C "$snap" -x --no-same-owner   # root-owned: git as root refuses a tree of
                                                                  # another user (CI checkout: "dubious ownership")
cd "$snap"
git init -q
git add -A
git -c user.email=build@localhost -c user.name=build commit -qm "v$v"
git tag "v$v"
cp packaging/PKGBUILD packaging/ryzen-control.install "$pkg"/
sed -i "s|^source=.*|source=(\"Ryzen-Control::git+file://$snap#tag=v\$pkgver\")|" "$pkg"/PKGBUILD
chown -R builder /home/builder
cd "$pkg"
su builder -c "makepkg --noconfirm"
namcap PKGBUILD ryzen-control-*.pkg.tar.zst
mkdir -p "$out" && cp ryzen-control-*.pkg.tar.zst "$out"/
