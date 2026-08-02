"""One-off: copy en/navigate.yaml structure to el and apply Greek t: strings."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = ROOT / "Rules/Languages/en/navigate.yaml"
OUT = ROOT / "Rules/Languages/el/navigate.yaml"

# English -> Greek for t: "..." (longest keys first applied via sorted reverse key length)
T_MAP: dict[str, str] = {
    "zoomed out all of the way": "πλήρης σμίκρυνση",
    "zoomed in all of the way": "μεγεθύνθηκε πλήρως",
    "zoomed in to first character": "μεγέθυνση στον πρώτο χαρακτήρα",
    "zoomed to character": "μεγέθυνση σε χαρακτήρα",
    "undo zooming in all of the way": "αναίρεση πλήρους μεγέθυνσης",
    "undo zooming out all of the way": "αναίρεση πλήρους σμίκρυνσης",
    "undo zoom in": "αναίρεση μεγέθυνσης",
    "undo zoom out": "αναίρεση σμίκρυνσης",
    "undo move left": "αναίρεση μετακίνησης αριστερά",
    "undo move right": "αναίρεση μετακίνησης δεξιά",
    "no previous command": "δεν υπάρχει προηγούμενη εντολή",
    "cannot move right, end of math": "στα δεξιά, τέλος μαθηματικών",
    "cannot move left, start of math": "δεν μπορεί να γίνει μετακίνηση στα αριστερά, αρχή μαθηματικών",
    "cannot move right": "δεν μπορεί να γίνει μετακίνηση δεξιά",
    "cannot move left": "δεν μπορεί να γίνει μετακίνηση στα αριστερά",
    "move to start of math": "μετακίνηση στην αρχή των μαθηματικών",
    "move to start of line": "μετακίνηση στην αρχή της γραμμής",
    "move to end of math": "μετακίνηση στο τέλος των μαθηματικών",
    "move to end of line": "μετακίνηση στο τέλος της γραμμής",
    "move to previous row": "μετακίνηση προς τα επάνω",
    "move to next row": "μετακίνηση προς τα κάτω",
    "move to previous column": "μετακίνηση στην προηγούμενη στήλη",
    "move to next column": "μετακίνηση στην επόμενη στήλη",
    "read current entry": "ανάγνωση τρέχουσας καταχώρησης",
    "no previous column": "δεν υπάρχει προηγούμενη στήλη",
    "no next column": "δεν υπάρχει επόμενη στήλη",
    "no previous row": "δεν υπάρχει προηγούμενη γραμμή",
    "no next row": "δεν υπάρχει επόμενη γραμμή",
    "not in table": "δεν υπάρχει στον πίνακα",
    "speak expression after move": "απόδοση έκφρασης μετά τη μετακίνηση",
    "overview of expression after move": "επισκόπηση έκφρασης μετά τη μετακίνηση",
    "set placeholder": "ορισμός δεσμευτικού θέσης",
    "inside of nothing more": "εντός χωρίς τίποτα παραπάνω",
    "pre-superscript": "προεκθέτης",
    "pre-subscript": "προδείκτης",
    "superscript": "εκθέτης",
    "subscript": "δείκτης",
    "to start of line": "στην αρχή της γραμμής",
    "to end of line": "στο τέλος της γραμμής",
    "end of math": "τέλος μαθηματικών",
    "start of math": "αρχή μαθηματικών",
    "placeholder": "δεσμευτικό θέσης",
    "current": "τρέχων",
    "describe": "περιγραφή",
    "character": "χαρακτήρας",
    "enhanced": "ενισχυμένος",
    "column": "στήλη",
    "cannot": "δεν μπορεί να γίνει",
    "simple": "απλός",
    "right": "δεξιά",
    "left": "αριστερά",
    "read": "ανάγνωση",
    "move": "μετακίνηση",
    "mode": "λειτουργία",
    "part": "μέρος",
    "base": "βάση",
    "row": "γραμμή",
    "inside": "εντός",
    "move up": "μετακίνηση επάνω",
    "move down": "μετακίνηση προς τα κάτω",
    "move left": "μετακίνηση αριστερά",
    "move right": "μετακίνηση δεξιά",
    "move to ": "μετακίνηση στο ",
    "set": "ορισμός",
    "in": "σε",
    "out": "έξω",
    # Same as English: internal concat marker \\uF8FE must stay for rule engine
    r"\uF8FEed in all of the way": r"\uF8FEed in all of the way",
    r"\uF8FEed out all of the way": r"\uF8FEed out all of the way",
}


def apply_t_map(text: str) -> str:
    """Replace only speech markers: ``[t: \"...\"]`` or ``- t: \"...\"`` (not ``NavNodeOffset: \"...\"``)."""

    def repl(m: re.Match[str]) -> str:
        prefix = m.group(1)  # includes optional '[' and whitespace before t:
        inner = m.group(2)
        greek = T_MAP.get(inner)
        if greek is None:
            raise KeyError(f"No Greek mapping for t: {inner!r}")
        escaped = greek.replace("\\", "\\\\").replace('"', '\\"')
        return f'{prefix}"{escaped}"'

    # Only speech ``- t:`` or ``[t:`` (skip keys like ``NavNodeOffset: "IfThenElse(...)"``).
    pattern = re.compile(r'((?:^[ \t]*-[ \t]+|\[)t:\s*)"((?:\\.|[^"\\])*)"', re.MULTILINE)
    return pattern.sub(repl, text)


def main() -> None:
    raw = EN.read_text(encoding="utf-8")
    # Documentation header: keep English like en (already from en file)
    out = apply_t_map(raw)
    OUT.write_text(out, encoding="utf-8", newline="\n")
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
