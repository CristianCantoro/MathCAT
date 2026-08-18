# /// script
# requires-python = ">=3.14"
# dependencies = ["pyyaml"]
# ///
"""Package MathCAT Rules/ into Rules.zip or Rules-minimized.zip."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import yaml

YAML_SUFFIXES = {".yaml", ".yml"}
MINIMIZE_NAMES = {"unicode.yaml", "unicode-full.yaml"}
SKIP_LANGUAGE_DIRS = {"zz"}
ZIP_SECTIONS = ("Languages", "Braille")

# Non-WASM MathCAT links the `zip` crate with only the `bzip2` feature (see Cargo.toml).
# Inner language/braille zips must use BZIP2 — DEFLATE (method 8) fails at runtime with
# CompressionMethodNotSupported. build.rs uses the same choice for native targets.
RULES_ZIP_COMPRESSION = zipfile.ZIP_BZIP2
RULES_ZIP_COMPRESSLEVEL = 9


def _open_rules_zip(path: Path, mode: str = "w") -> zipfile.ZipFile:
    return zipfile.ZipFile(
        path,
        mode,
        compression=RULES_ZIP_COMPRESSION,
        compresslevel=RULES_ZIP_COMPRESSLEVEL,
    )


def _configure_yaml_dumper() -> None:
    """Quote all strings so yaml-rust does not treat words like 'infinity' as floats."""

    def represent_str(dumper: yaml.SafeDumper, data: str) -> yaml.nodes.ScalarNode:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')

    yaml.add_representer(str, represent_str, Dumper=yaml.SafeDumper)


_configure_yaml_dumper()


def should_minimize(path: Path) -> bool:
    if path.suffix.lower() not in YAML_SUFFIXES or path.name not in MINIMIZE_NAMES:
        return False
    # Speech unicode only — braille unicode.yaml keeps block form (tests and edits rely on it).
    return "Languages" in path.parts


def preprocess_for_load(text: str) -> str:
    """Normalize MathCAT YAML quirks so PyYAML can parse it."""
    text = text.replace("\t", "    ")
    text = re.sub(r'(?m)^(\s*-\s*)":(\s*:\s*)', r'\1"\\"":\2', text)
    text = re.sub(r'(?m)^(\s*-\s*)\\"(\s*:\s*)', r'\1"\\""\2', text)
    return text


def load_yaml(text: str) -> Any:
    """Load YAML using PyYAML with MathCAT-specific normalizations."""
    candidates = (text, text.replace("\t", "    "), preprocess_for_load(text))
    last_error: yaml.YAMLError | None = None
    for candidate in candidates:
        try:
            return yaml.safe_load(candidate)
        except yaml.YAMLError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return None


def dump_flow_style(data: Any) -> str:
    """Emit minimized flow-style YAML without comments."""
    if data is None:
        return ""
    dumped = yaml.dump(
        data,
        allow_unicode=True,
        default_flow_style=True,
        width=10**9,
        sort_keys=False,
        Dumper=yaml.SafeDumper,
    )
    return dumped if dumped.endswith("\n") else f"{dumped}\n"


def minimize_yaml_text(text: str) -> tuple[str, bool]:
    """Return flow-style YAML and whether parsing succeeded."""
    try:
        data = load_yaml(text)
    except yaml.YAMLError:
        return text, False
    return dump_flow_style(data), True


def copy_rules_tree(source: Path, destination: Path, *, minimize: bool) -> tuple[int, int, list[str]]:
    """Copy ``source`` Rules tree to ``destination``, optionally minimizing YAML."""
    minimized = 0
    copied = 0
    warnings: list[str] = []

    for src_path in sorted(source.rglob("*")):
        if src_path.is_dir():
            continue
        rel = src_path.relative_to(source)
        dest_path = destination / rel
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if minimize and should_minimize(src_path):
            text = src_path.read_text(encoding="utf-8")
            out, ok = minimize_yaml_text(text)
            if ok:
                dest_path.write_text(out, encoding="utf-8", newline="\n")
                minimized += 1
            else:
                dest_path.write_bytes(src_path.read_bytes())
                warnings.append(f"could not minimize {rel}; copied verbatim")
                copied += 1
        else:
            dest_path.write_bytes(src_path.read_bytes())
            copied += 1

    return minimized, copied, warnings


def apply_release_layout(rules_dir: Path) -> None:
    """Zip each language/braille subdir into ``<name>/<name>.zip`` and drop loose YAML inside."""
    zz = rules_dir / "Languages" / "zz"
    if zz.is_dir():
        shutil.rmtree(zz)

    for section in ZIP_SECTIONS:
        section_dir = rules_dir / section
        if section_dir.is_dir():
            _zip_immediate_subdirs(section_dir)


def _zip_immediate_subdirs(parent: Path) -> None:
    for entry in sorted(parent.iterdir(), key=lambda path: path.name):
        if not entry.is_dir():
            continue
        if entry.name in SKIP_LANGUAGE_DIRS:
            shutil.rmtree(entry)
            continue

        inner_zip = entry / f"{entry.name}.zip"
        yaml_count = _write_yaml_zip(entry, inner_zip)
        if yaml_count == 0:
            inner_zip.unlink(missing_ok=True)
            shutil.rmtree(entry)
            continue

        _remove_files_except(entry, keep={inner_zip})
        _prune_empty_dirs(entry)


def _write_yaml_zip(source_dir: Path, zip_path: Path) -> int:
    yaml_files = [
        path
        for path in sorted(source_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in YAML_SUFFIXES and path != zip_path
    ]
    if not yaml_files:
        return 0

    with _open_rules_zip(zip_path) as archive:
        for path in yaml_files:
            archive.write(path, path.relative_to(source_dir).as_posix())
    return len(yaml_files)


def _remove_files_except(root: Path, *, keep: set[Path]) -> None:
    keep_resolved = {item.resolve() for item in keep}
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file() and path.resolve() not in keep_resolved:
            path.unlink()


def _prune_empty_dirs(root: Path) -> None:
    for path in sorted((item for item in root.rglob("*") if item.is_dir()), reverse=True):
        try:
            path.rmdir()
        except OSError:
            continue


def zip_directory(source_dir: Path, zip_path: Path) -> None:
    """Write ``source_dir`` contents into ``zip_path`` preserving relative paths."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with _open_rules_zip(zip_path) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir.parent).as_posix())


def package_rules(source: Path, output: Path, *, minimize: bool = False) -> dict[str, int | list[str]]:
    """Package ``source`` (Rules directory) into ``output`` zip file."""
    source = source.resolve()
    output = output.resolve()

    if not source.is_dir():
        raise FileNotFoundError(f"Rules source directory not found: {source}")
    if source.name != "Rules":
        raise ValueError(f"Expected a directory named 'Rules', got '{source.name}'")

    with tempfile.TemporaryDirectory(prefix="mathcat-rules-") as tmp:
        staged_rules = Path(tmp) / "Rules"
        if minimize:
            minimized, copied, warnings = copy_rules_tree(source, staged_rules, minimize=True)
        else:
            shutil.copytree(source, staged_rules)
            minimized, copied, warnings = 0, sum(1 for p in staged_rules.rglob("*") if p.is_file()), []

        apply_release_layout(staged_rules)
        zip_directory(staged_rules, output)

    return {
        "minimized_yaml_files": minimized,
        "copied_files": copied,
        "warnings": warnings,
    }


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
