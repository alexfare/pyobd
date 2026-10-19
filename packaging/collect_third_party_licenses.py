#!/usr/bin/env python3
"""Collect exact licenses from the environment used to package pyOBD."""

from __future__ import annotations

import argparse
import re
import shutil
import sysconfig
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


ROOT_PACKAGES = ("wxPython", "numpy", "Pint", "pyserial", "PyInstaller", "Pillow")
LICENSE_NAMES = re.compile(r"^(license|licence|copying|notice|authors)([._-].*)?$", re.I)


def dependency_names(dist):
    for requirement_text in dist.requires or ():
        requirement = Requirement(requirement_text)
        if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
            continue
        yield requirement.name


def installed_distributions():
    pending = list(ROOT_PACKAGES)
    seen = set()
    while pending:
        requested_name = pending.pop(0)
        canonical_name = canonicalize_name(requested_name)
        if canonical_name in seen:
            continue
        try:
            dist = distribution(requested_name)
        except PackageNotFoundError:
            continue
        seen.add(canonical_name)
        yield dist
        pending.extend(dependency_names(dist))


def is_license_file(path):
    parts = tuple(part.lower() for part in path.parts)
    return "licenses" in parts or LICENSE_NAMES.match(path.name)


def copy_distribution_licenses(dist, output_dir):
    package_dir = output_dir / f"{canonicalize_name(dist.metadata['Name'])}-{dist.version}"
    copied = 0
    for file in dist.files or ():
        if not is_license_file(Path(file)):
            continue
        source = Path(dist.locate_file(file))
        if not source.is_file():
            continue
        relative = Path(*Path(file).parts[1:]) if ".dist-info" in Path(file).parts[0] else Path(file)
        destination = package_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1
    return copied


def copy_python_license(output_dir):
    source = Path(sysconfig.get_path("stdlib")) / "LICENSE.txt"
    if source.is_file():
        destination = output_dir / "python" / "LICENSE.txt"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?", default="third-party-licenses")
    args = parser.parse_args()
    output_dir = Path(args.output).resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    manifest = ["Third-party licenses included in this pyOBD build", ""]
    if copy_python_license(output_dir):
        manifest.append("Python: bundled interpreter license copied")

    for dist in sorted(installed_distributions(), key=lambda item: item.metadata["Name"].lower()):
        count = copy_distribution_licenses(dist, output_dir)
        license_name = dist.metadata.get("License-Expression") or dist.metadata.get("License") or "See license files"
        manifest.append(f"{dist.metadata['Name']} {dist.version}: {license_name} ({count} license file(s))")

    fallback = Path(__file__).with_name("licenses") / "pyserial-LICENSE.txt"
    pyserial_dir = next(output_dir.glob("pyserial-*"), output_dir / "pyserial")
    if not any(pyserial_dir.rglob("*LICENSE*")):
        pyserial_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fallback, pyserial_dir / "LICENSE.txt")

    (output_dir / "README.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
