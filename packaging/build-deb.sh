#!/bin/sh
# Builds the .deb on Debian/Ubuntu as root (a container: `make deb`, the release workflow) from the source
# tree in the current directory, then checks it with lintian; the package goes to $1 (default: dist).
set -e
out=${1:-dist}
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends build-essential debhelper dh-dkms dkms python3 make lintian >/dev/null
cp -r packaging/debian debian
dpkg-buildpackage -us -uc -b
lintian --fail-on error,warning ../ryzen-control_*_all.deb
mkdir -p "$out" && cp ../ryzen-control_*_all.deb "$out"/
