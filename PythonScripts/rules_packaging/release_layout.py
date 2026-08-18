"""Transform a Rules tree into the release layout used by build.rs and CI."""

from __future__ import annotations

import shutil
from pathlib import Path

from .compress import open_rules_zip

YAML_SUFFIXES = {".yaml", ".yml"}
SKIP_LANGUAGE_DIRS = {"zz"}
ZIP_SECTIONS = ("Languages", "Braille")


def apply_release_layout(rules_dir: Path) -> None:
    """Zip each language/braille subdir into ``<name>/<name>.zip`` and drop loose YAML inside."""
    languages = rules_dir / "Languages"
    zz = languages / "zz"
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
    """Write all YAML under ``source_dir`` into ``zip_path``; return file count."""
    yaml_files = [
        path
        for path in sorted(source_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in YAML_SUFFIXES and path != zip_path
    ]
    if not yaml_files:
        return 0

    with open_rules_zip(zip_path) as archive:
        for path in yaml_files:
            archive.write(path, path.relative_to(source_dir).as_posix())
    return len(yaml_files)


def _remove_files_except(root: Path, *, keep: set[Path]) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file() and path.resolve() not in {item.resolve() for item in keep}:
            path.unlink()


def _prune_empty_dirs(root: Path) -> None:
    for path in sorted((item for item in root.rglob("*") if item.is_dir()), reverse=True):
        try:
            path.rmdir()
        except OSError:
            continue
