#!/usr/bin/env python3
from pathlib import Path
path = Path('tests/braille/Vietnam/vi.rs')
content = path.read_text(encoding='utf-8')
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'fn salt()' in line:
        print(f"Line {i}: {repr(line)}")
        print(f"  Has Result: {'-> Result<()>' in line}")
        for j in range(i, min(i+5, len(lines))):
            print(f"  {j}: {repr(lines[j][:80])}")
        break
