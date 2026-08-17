"""Tests for Rules packaging and YAML minimization."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import yaml

from rules_packaging.minimize import dump_flow_style, load_yaml, minimize_yaml_text
from rules_packaging.package import package_rules


def read_nested_zip_text(archive: zipfile.ZipFile, outer_path: str, inner_path: str) -> str:
    """Read ``inner_path`` from a zip file stored inside the outer archive."""
    with zipfile.ZipFile(io.BytesIO(archive.read(outer_path))) as inner:
        return inner.read(inner_path).decode("utf-8")


def test_minimize_yaml_strips_comments_and_uses_flow_style() -> None:
    """Minimized YAML drops comments and uses flow-style collections."""
    source = """---
# comment
 - \"+\": [t: \"plus\"]  # inline
"""
    minimized, ok = minimize_yaml_text(source)
    assert ok
    assert "#" not in minimized
    assert "[" in minimized and "{" in minimized or "t:" in minimized
    assert load_yaml(minimized) == load_yaml(source)


def test_package_rules_standard_zip_layout(tmp_path: Path) -> None:
    """Standard packaging preserves Rules/ prefix and per-language inner zips."""
    rules = tmp_path / "Rules"
    lang = rules / "Languages" / "en"
    lang.mkdir(parents=True)
    (rules / "prefs.yaml").write_text("- SpeechStyle: [t: \"ClearSpeak\"]\n", encoding="utf-8")
    (lang / "unicode.yaml").write_text("- \"+\": [t: \"plus\"]\n", encoding="utf-8")

    output = tmp_path / "Rules.zip"
    package_rules(rules, output, minimize=False)

    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert "Rules/prefs.yaml" in names
        assert "Rules/Languages/en/en.zip" in names
        assert "Rules/Languages/en/unicode.yaml" not in names
        assert read_nested_zip_text(archive, "Rules/Languages/en/en.zip", "unicode.yaml").replace("\r\n", "\n") == "- \"+\": [t: \"plus\"]\n"


def test_dump_flow_style_quotes_infinity() -> None:
    """Flow-style dump must quote 'infinity' so yaml-rust does not read it as a float."""
    minimized = dump_flow_style([{"∞": [{"t": "infinity"}]}])
    assert '"infinity"' in minimized
    assert "t: infinity" not in minimized


def test_should_not_minimize_braille_unicode(tmp_path: Path) -> None:
    """Braille unicode.yaml is copied verbatim even when minimization is enabled."""
    rules = tmp_path / "Rules"
    braille = rules / "Braille" / "Nemeth"
    braille.mkdir(parents=True)
    source = """---
 - "1": [t: "N⠂"]
"""
    (braille / "unicode.yaml").write_text(source, encoding="utf-8")

    output = tmp_path / "Rules-minimized.zip"
    stats = package_rules(rules, output, minimize=True)

    assert stats["minimized_yaml_files"] == 0
    with zipfile.ZipFile(output) as archive:
        text = read_nested_zip_text(archive, "Rules/Braille/Nemeth/Nemeth.zip", "unicode.yaml")
    assert text.replace("\r\n", "\n") == source.replace("\r\n", "\n")


def test_package_rules_minimized_matches_release_layout(tmp_path: Path) -> None:
    """Minimized archives use inner language zips and flow-style unicode YAML."""
    rules = tmp_path / "Rules"
    lang = rules / "Languages" / "en"
    lang.mkdir(parents=True)
    (lang / "unicode.yaml").write_text(
        """---
# header comment
 - \"+\": [t: \"plus\"]  # trailing
 - \"-\": [t: \"minus\"]
""",
        encoding="utf-8",
    )
    (lang / "definitions.yaml").write_text(
        """---
 - AdditionalFunctionNames:
    - real=inf
""",
        encoding="utf-8",
    )

    standard = tmp_path / "Rules.zip"
    minimized = tmp_path / "Rules-minimized.zip"
    package_rules(rules, standard, minimize=False)
    stats = package_rules(rules, minimized, minimize=True)

    assert stats["minimized_yaml_files"] == 1
    assert minimized.stat().st_size <= standard.stat().st_size

    with zipfile.ZipFile(minimized) as archive:
        names = archive.namelist()
        assert "Rules/Languages/en/en.zip" in names
        assert "Rules/Languages/en/unicode.yaml" not in names
        unicode_text = read_nested_zip_text(archive, "Rules/Languages/en/en.zip", "unicode.yaml")
        defs_text = read_nested_zip_text(archive, "Rules/Languages/en/en.zip", "definitions.yaml")
    assert "#" not in unicode_text
    assert "real=inf" in defs_text
    assert yaml.safe_load(unicode_text) is not None
