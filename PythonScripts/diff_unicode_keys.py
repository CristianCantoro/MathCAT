"""Diff Nemeth vs UEB unicode*.yaml entries, preserving raw YAML text.

If an entry lacks a hex Unicode comment on its first line, append one in the
output .txt (YAML source files are not modified).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ENTRY_START = re.compile(r'^(\s*)-\s*"([^"]+)"\s*:')
# Existing hex-ish unicode comment on the entry's first line
HAS_HEX_COMMENT = re.compile(
    r"#\s*(?:0[xX][0-9A-Fa-f]+|U\+[0-9A-Fa-f]+)",
)


def extract_raw_entries(path: Path) -> dict[str, str]:
    """Map key -> raw YAML text block for that entry (as in file)."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    entries: dict[str, str] = {}
    i = 0
    while i < len(lines):
        m = ENTRY_START.match(lines[i])
        if not m:
            i += 1
            continue
        indent, key = m.group(1), m.group(2)
        start = i
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if ENTRY_START.match(nxt):
                break
            # blank lines after an entry belong between entries, not inside
            if nxt.strip() == "":
                # peek: if next non-empty is another entry or EOF, stop
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                if j >= len(lines) or ENTRY_START.match(lines[j]):
                    break
            # less-indented content ends the entry (except blank/comment-only)
            if nxt.strip() and not nxt.startswith(indent + " ") and not nxt.startswith(
                indent + "\t"
            ):
                if not nxt.lstrip().startswith("#"):
                    break
            i += 1
        # trim trailing blank lines from the block
        end = i
        while end > start + 1 and lines[end - 1].strip() == "":
            end -= 1
        entries[key] = "".join(lines[start:end]).rstrip("\n")
    return entries


def hex_comment_for_key(key: str) -> str:
    """Build a `# 0x…` comment matching common style in these files."""
    if len(key) == 3 and key[1] == "-":
        a, b = key[0], key[2]
        return f"# 0x{ord(a):x} - 0x{ord(b):x}"
    if len(key) == 1:
        return f"# 0x{ord(key):x}"
    return "# " + ", ".join(f"0x{ord(c):x}" for c in key)


def ensure_hex_comment(block: str, key: str) -> str:
    """Return block text, appending a hex comment on the first line if missing."""
    lines = block.splitlines()
    if not lines:
        return block
    first = lines[0]
    if HAS_HEX_COMMENT.search(first):
        return block
    # Append comment; preserve existing trailing spaces lightly
    lines[0] = first.rstrip() + "  " + hex_comment_for_key(key)
    return "\n".join(lines)


def emit_section(
    lines: list[str],
    title: str,
    keys: list[str],
    primary: dict[str, str],
    full: dict[str, str],
) -> None:
    lines.append(title)
    for k in keys:
        # Prefer unicode.yaml text when present in both
        block = primary.get(k) or full[k]
        lines.append(ensure_hex_comment(block, k))


def main() -> None:
    nemeth_u = extract_raw_entries(ROOT / "Rules/Braille/Nemeth/unicode.yaml")
    nemeth_f = extract_raw_entries(ROOT / "Rules/Braille/Nemeth/unicode-full.yaml")
    ueb_u = extract_raw_entries(ROOT / "Rules/Braille/UEB/unicode.yaml")
    ueb_f = extract_raw_entries(ROOT / "Rules/Braille/UEB/unicode-full.yaml")

    nemeth = set(nemeth_u) | set(nemeth_f)
    ueb = set(ueb_u) | set(ueb_f)

    only_nemeth = sorted(nemeth - ueb, key=lambda s: (ord(s[0]) if s else 0, s))
    only_ueb = sorted(ueb - nemeth, key=lambda s: (ord(s[0]) if s else 0, s))
    only_nemeth_core = sorted(
        set(nemeth_u) - ueb, key=lambda s: (ord(s[0]) if s else 0, s)
    )
    only_ueb_core = sorted(
        set(ueb_u) - nemeth, key=lambda s: (ord(s[0]) if s else 0, s)
    )

    out_lines: list[str] = []
    out_lines.append("=== COUNTS ===")
    out_lines.append(
        f"Nemeth unicode.yaml: {len(nemeth_u)}  "
        f"unicode-full.yaml: {len(nemeth_f)}  "
        f"combined unique: {len(nemeth)}"
    )
    out_lines.append(
        f"UEB    unicode.yaml: {len(ueb_u)}  "
        f"unicode-full.yaml: {len(ueb_f)}  "
        f"combined unique: {len(ueb)}"
    )
    out_lines.append(f"Only in Nemeth (combined): {len(only_nemeth)}")
    out_lines.append(f"Only in UEB (combined): {len(only_ueb)}")
    out_lines.append(f"In both: {len(nemeth & ueb)}")
    out_lines.append(
        f"Only in Nemeth unicode.yaml (not any UEB): {len(only_nemeth_core)}"
    )
    out_lines.append(
        f"Only in UEB unicode.yaml (not any Nemeth): {len(only_ueb_core)}"
    )
    out_lines.append("")
    out_lines.append(
        "Note: entries are copied as they appear in the YAML files."
    )
    out_lines.append(
        "If the first line lacked a hex unicode comment (# 0x…), one was added here."
    )
    out_lines.append("")

    emit_section(
        out_lines,
        "=== ONLY IN NEMETH unicode.yaml (not in any UEB unicode*) ===",
        only_nemeth_core,
        nemeth_u,
        nemeth_f,
    )
    emit_section(
        out_lines,
        "=== ONLY IN UEB unicode.yaml (not in any Nemeth unicode*) ===",
        only_ueb_core,
        ueb_u,
        ueb_f,
    )
    emit_section(
        out_lines,
        "=== ONLY IN NEMETH (combined unicode* not in UEB) — full list ===",
        only_nemeth,
        nemeth_u,
        nemeth_f,
    )
    emit_section(
        out_lines,
        "=== ONLY IN UEB (combined unicode* not in Nemeth) — full list ===",
        only_ueb,
        ueb_u,
        ueb_f,
    )

    out = ROOT / "PythonScripts/nemeth_ueb_unicode_diff.txt"
    out.write_text("\n".join(out_lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(out_lines)} lines)")


if __name__ == "__main__":
    main()
