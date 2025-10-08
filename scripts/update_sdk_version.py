#!/usr/bin/env python3
"""Update SDK version references in the repository."""

from __future__ import annotations

import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
SDK_VERSION_FILE = ROOT / "sdk" / "VERSION"
SDK_CMAKE = ROOT / "sdk" / "cpp" / "CMakeLists.txt"
SDK_USAGE = ROOT / "sdk" / "cpp" / "USAGE.md"


def update_file(path: pathlib.Path, pattern: str, replacement: str) -> bool:
    text = path.read_text(encoding="utf-8")
    new_text, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count == 0:
        raise RuntimeError(f"No matches found in {path} for pattern {pattern!r}")
    path.write_text(new_text, encoding="utf-8")
    return True


def main(version: str) -> int:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"Invalid version '{version}'. Expected format: X.Y.Z")

    # Update CMake project version.
    update_file(
        SDK_CMAKE,
        r"(project\(game-sdk VERSION) \d+\.\d+\.\d+",
        rf"\1 {version}",
    )

    # Update USAGE.md references (paths and FetchContent tag).
    update_file(
        SDK_USAGE,
        r"game-sdk-v\d+\.\d+\.\d+",
        f"game-sdk-v{version}",
    )
    update_file(
        SDK_USAGE,
        r"GIT_TAG v\d+\.\d+\.\d+",
        f"GIT_TAG v{version}",
    )

    # Persist version in sdk/VERSION for quick access.
    SDK_VERSION_FILE.write_text(f"{version}\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: update_sdk_version.py <version>")
    sys.exit(main(sys.argv[1]))
