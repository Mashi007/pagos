from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "reaplicar_fifo_prestamo.py"
p.write_text(
    '''"""Compat: script historico; delega en reaplicar_cascada_prestamo."""
from __future__ import annotations

from reaplicar_cascada_prestamo import main

if __name__ == "__main__":
    main()
''',
    encoding="utf-8",
    newline="\n",
)
print("wrote", p)
