# -*- coding: utf-8 -*-
"""
Create SHA-256 checksums for repository data, code, and outputs.

Author: Farshad Hesamfar
Affiliation: University of Virginia
Contact: wky7xx@virginia.edu
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="SHA256SUMS.txt")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output

    files = sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and path.resolve() != output.resolve()
        and ".git" not in path.parts
        and "__pycache__" not in path.parts
    )

    lines = [
        f"{sha256(path)}  {path.relative_to(root).as_posix()}"
        for path in files
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved checksums: {output}")


if __name__ == "__main__":
    main()
