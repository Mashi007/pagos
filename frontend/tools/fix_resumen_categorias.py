from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src" / "components" / "notificaciones" / "ResumenPlantillas.tsx"


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    new_block = """const categoriasOrden = [
  { key: 'Notificaci\u00f3n Previa', color: 'blue', icon: '\U0001f514' },
  { key: 'D\u00eda de Pago', color: 'green', icon: '\U0001f4c5' },
  { key: 'Notificaci\u00f3n Retrasada', color: 'orange', icon: '\u26a0\ufe0f' },
  { key: 'Prejudicial', color: 'red', icon: '\U0001f6a8' },
]

"""
    m = re.search(r"const categoriasOrden = \[[\s\S]*?\]\r?\n", text)
    if not m:
        raise SystemExit("categoriasOrden block not found")
    text = text[: m.start()] + new_block + text[m.end() :]
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print("updated", TARGET)


if __name__ == "__main__":
    main()
