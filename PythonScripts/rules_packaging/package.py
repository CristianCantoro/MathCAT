"""Create Rules.zip archives from a Rules directory tree."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .compress import open_rules_zip
from .minimize import copy_rules_tree
from .release_layout import apply_release_layout


def zip_directory(source_dir: Path, zip_path: Path) -> None:
    """Write ``source_dir`` contents into ``zip_path`` preserving relative paths."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with open_rules_zip(zip_path) as archive:
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
        staging_root = Path(tmp)
        staged_rules = staging_root / "Rules"
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
