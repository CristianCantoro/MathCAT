# Polish Braille — Project State

> Personal scratchpad for the Polish braille work. Gitignored (see `.gitignore`: `notes/`).
> Resume protocol: at the start of a new chat, paste:
> *"Read `notes/polish-braille.md` and continue from 'Next step'."*
> At the end of a session, ask the agent: *"Update `notes/polish-braille.md`."*

## Goal
Fix Polish braille output so the tests in `tests/braille/Polish/spec.rs` pass.

Reference document for the Polish braille spec (local copy):
`BrailleDocs/brajlowska_notacja_matematyczna_fizyczna_chemiczna.pdf`
Online: <https://ore.edu.pl/images/files/pdf/Brajlowska%20notacja%20matematyczna%20fizyczna%20chemiczna%20wyd%20II.pdf>

Reading status: **not yet read by the agent** — read on demand and cite section/page numbers in the decisions log.

## Scope / non-goals
- In scope:
  - Polish braille code (`Rules/Braille/Polish/...`)
  - Polish-specific logic in `src/braille.rs` (`polish_cleanup`, `polish_remove_unneeded_mode_changes`, `POLISH_INDICATOR_REPLACEMENTS`, `BrailleLevel`, `Projectors`, …)
  - Tests under `tests/braille/Polish/spec.rs`
- Out of scope (unless a fix forces it):
  - Other braille codes (Nemeth, UEB, CMU, Vietnam, LaTeX, ASCIIMath, …)
  - Speech rules / SimpleSpeak / ClearSpeak

## Key files
- `tests/braille/Polish/spec.rs` — tests (now `Result<()>` style with `?` and `return Ok(());`)
- `tests/common/mod.rs` — `test_braille`, `test_braille_prefs`
- `src/braille.rs`
  - `polish_cleanup` (function-scoped `LazyLock<Regex>` regexes)
  - `polish_remove_unneeded_mode_changes`
  - `POLISH_INDICATOR_REPLACEMENTS` (phf::Map)
  - `BrailleLevel`, `Projectors`, `find_fraction_lengths_stack`
- `Rules/Braille/Polish/` — YAML rules (TBD: list specific files when first touched)
- `Rules/prefs.yaml` — `Polish_BrailleLevel` preference (`Beginner` | `Intermediate` | `Advanced`)

## Conventions / gotchas (from AGENTS.md and what I've seen)
- Don't run `cargo fmt` on the repo.
- Translation markers: `T:` verified, `t:` unverified — never demote unprompted.
- Prefer targeted tests: `cargo test --test braille <name>`.
- Validate Python tooling with `uv run pytest` when touching `PythonScripts/`.
- Polish tests already migrated to `-> Result<()>` + `?` + `return Ok(());` style (matches `tests/braille/Nemeth/other.rs`).

## How to run tests
```
cargo test --test braille Polish::spec
cargo test --test braille Polish::spec::Intro_1
cargo test --test braille Polish::spec::structural_formulas_p89_4
```

Common form for adding `Polish_BrailleLevel`:
```rust
test_braille_prefs("Polish", vec![("Polish_BrailleLevel", "Beginner")], expr, r"…")?;
```

## Decisions log
- 2026-05-02: Polish notes live in `notes/polish-braille.md` (gitignored).
- 2026-05-02: Polish spec tests converted to `Result<()>` style to match `Nemeth/other.rs`.
- 2026-05-02: `polish_cleanup` regexes converted from `lazy_static!` to `std::sync::LazyLock`.

## Open questions / blockers
- _None yet — fill in as they arise._

## Failing tests inventory
> Run `cargo test --test braille Polish::spec 2>&1 | tee target/polish-failures.txt`
> and paste a triage list here. Group by likely root cause.

| Test | Expected | Got | Likely cause | Notes |
| ---- | -------- | --- | ------------ | ----- |
| `Intro_1` | `⠩⠼⠁⠋` | `<⠩N⠁N⠋>⠱` | indicators not stripped/replaced | first pass shows raw markers `<…>⠱` and `N` survive |

## Next step
1. Run the full Polish test suite and capture failures into the table above.
2. Group failures by root cause (e.g. indicator stripping, mode changes, units, fractions).
3. Pick the smallest-blast-radius cluster and start there.

## Session log
- **2026-05-02 (evening)**: project scaffolded; pre-existing failure observed on `Intro_1` — output still contains raw indicators `<>` and `N`, suggesting `polish_cleanup` / `REPLACE_INDICATORS` path may not be running, or returning before substitution.
