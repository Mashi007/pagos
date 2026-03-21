from __future__ import annotations

import re
from pathlib import Path


def fix_content(s: str) -> tuple[str, int]:
    """Apply safe replacements for ?? corrupted to ? before literals in common patterns."""
    n = 0

    def sub(pat: str, repl: str, text: str) -> tuple[str, int]:
        nonlocal n
        new, c = re.subn(pat, repl, text)
        n += c
        return new, c

    # Object property: expr ? '',  ->  expr ?? '',
    s, _ = sub(r"(\S)\s+\?\s+(''|\"\")(\s*),", r"\1 ?? \2\3,", s)
    # expr ? '');  or expr ? '' );
    s, _ = sub(r"(\S)\s+\?\s+(''|\"\")(\s*)\)", r"\1 ?? \2\3)", s)
    # expr ? '' } 
    s, _ = sub(r"(\S)\s+\?\s+(''|\"\")(\s*)\}", r"\1 ?? \2\3}", s)

    # Numbers:  something ? 0, or ? 0)
    s, _ = sub(r"(\S)\s+\?\s+(0)(\s*),", r"\1 ?? \2\3,", s)
    s, _ = sub(r"(\S)\s+\?\s+(0)(\s*)\)", r"\1 ?? \2\3)", s)

    # false:  expr ? false,  ->  ?? false,
    s, _ = sub(r"(\S)\s+\?\s+(false)(\s*),", r"\1 ?? \2\3,", s)
    s, _ = sub(r"(\S)\s+\?\s+(false)(\s*)\)", r"\1 ?? \2\3)", s)
    s, _ = sub(r"(\S)\s+\?\s+(false)(\s*)\|\|", r"\1 ?? \2\3||", s)

    return s, n


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "src"
    files = list(root.rglob("*.ts")) + list(root.rglob("*.tsx"))
    total_changes = 0
    touched = 0
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        new, n = fix_content(text)
        if n and new != text:
            f.write_text(new, encoding="utf-8")
            touched += 1
            total_changes += n
            print(f"{f.relative_to(root.parent)}: {n} replacements")
    print("done. files:", touched, "total subs:", total_changes)


if __name__ == "__main__":
    main()
