#!/usr/bin/env bash
set -euo pipefail

version="$1"
architecture="${2:-$(dpkg --print-architecture)}"
package_root="$(mktemp -d)"
trap 'rm -rf "$package_root"' EXIT

install -d \
  "$package_root/DEBIAN" \
  "$package_root/opt/pyobd" \
  "$package_root/usr/bin" \
  "$package_root/usr/share/applications" \
  "$package_root/usr/share/doc/pyobd" \
  "$package_root/usr/share/pixmaps" \
  installer-dist

cp -R dist/pyOBD/. "$package_root/opt/pyobd/"
install -m 755 packaging/linux/pyobd "$package_root/usr/bin/pyobd"
install -m 644 packaging/linux/pyobd.desktop "$package_root/usr/share/applications/pyobd.desktop"
install -m 644 pyobd.ico "$package_root/usr/share/pixmaps/pyobd.ico"
install -m 644 COPYING "$package_root/usr/share/doc/pyobd/copyright"

installed_size="$(du -sk "$package_root" | cut -f1)"
printf '%s\n' \
  'Package: pyobd' \
  "Version: $version" \
  'Section: utils' \
  'Priority: optional' \
  "Architecture: $architecture" \
  'Maintainer: FareBrothers, LLC' \
  'Installed-Size: '"$installed_size" \
  'Depends: libgtk-3-0 | libgtk-3-0t64, libgl1, libnotify4 | libnotify4t64' \
  'Homepage: https://github.com/alexfare/pyobd' \
  'Description: OBD-II vehicle diagnostic application' \
  ' View sensors, readiness tests, trouble codes, freeze-frame data, and live graphs.' \
  > "$package_root/DEBIAN/control"

dpkg-deb --build --root-owner-group \
  "$package_root" \
  "installer-dist/pyOBD-${version}-Linux-${architecture}.deb"
