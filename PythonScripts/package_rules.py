# /// script
# requires-python = ">=3.14"
# dependencies = ["pyyaml"]
# ///
"""Package MathCAT Rules/ into Rules.zip or Rules-minimized.zip."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Standalone script: sibling package, not installed via audit_translations.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rules_packaging.package import package_rules  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Package MathCAT Rules/ into a zip archive. "
        "Use --minimize for flow-style unicode.yaml / unicode-full.yaml without comments."
    )
    parser.add_argument("source", type=Path, help="Path to the Rules directory")
    parser.add_argument("output", type=Path, help="Output zip file path (e.g. Rules.zip)")
    parser.add_argument(
        "--minimize",
        action="store_true",
        help="Emit compact flow-style YAML (comments and block formatting removed)",
    )
    args = parser.parse_args(argv)

    try:
        stats = package_rules(args.source, args.output, minimize=args.minimize)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    label = "minimized" if args.minimize else "standard"
    print(f"Created {label} archive: {args.output}")
    if args.minimize:
        print(f"  minimized YAML files: {stats['minimized_yaml_files']}")
        print(f"  copied verbatim: {stats['copied_files']}")
        for warning in stats["warnings"]:
            print(f"  warning: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
