"""Convert MathCAT Rules YAML files to compact flow-style form."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

YAML_SUFFIXES = {".yaml", ".yml"}
MINIMIZE_NAMES = {"unicode.yaml", "unicode-full.yaml"}


def should_minimize(path: Path) -> bool:
    if path.suffix.lower() not in YAML_SUFFIXES or path.name not in MINIMIZE_NAMES:
        return False
    # Speech unicode only — braille unicode.yaml keeps block form (tests and edits rely on it).
    return "Languages" in path.parts


def _configure_yaml_dumper() -> None:
    """Quote all strings so yaml-rust does not treat words like 'infinity' as floats."""

    def represent_str(dumper: yaml.SafeDumper, data: str) -> yaml.nodes.ScalarNode:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')

    yaml.add_representer(str, represent_str, Dumper=yaml.SafeDumper)


_configure_yaml_dumper()


def preprocess_for_load(text: str) -> str:
    """Normalize MathCAT YAML quirks so PyYAML can parse it."""
    text = text.replace("\t", "    ")
    # Bare double-quote or colon used as a mapping key in unicode list entries.
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
