from __future__ import annotations

import re
from pathlib import Path


def scan_line(line: str) -> bool:
    s = line.strip()
    if not s or s.startswith("//") or s.startswith("*"):
        return False
    if "?" not in line:
        return False
    tmp = line.replace("??", "").replace("?.", "")
    if "?" not in tmp:
        return False
    tmp2 = re.sub(r"'(?:\\.|[^'\\])*'", "''", tmp)
    tmp2 = re.sub(r'"(?:\\.|[^"\\])*"', '""', tmp2)
    tmp2 = re.sub(r"`(?:\\.|[^`\\])*`", "``", tmp2)
    if "?" not in tmp2:
        return False
    m = re.search(r"[^<>=!]\s\?\s+([^;]+)$", tmp2)
    if not m:
        return False
    rhs = m.group(1)
    if ":" in rhs:
        return False
    return True


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "src"
    files = list(root.rglob("*.tsx")) + list(root.rglob("*.ts"))
    bad: list[tuple[str, list[tuple[int, str]]]] = []
    for f in files:
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        hits: list[tuple[int, str]] = []
        for i, line in enumerate(lines, 1):
            if scan_line(line):
                hits.append((i, line[:220]))
        if hits:
            bad.append((str(f.relative_to(root.parent)), hits))

    bad.sort(key=lambda x: len(x[1]), reverse=True)
    print("files:", len(bad))
    for p, hits in bad[:40]:
        print(len(hits), p)
        for ln, line in hits[:2]:
            print(" ", ln, line)


if __name__ == "__main__":
    main()
