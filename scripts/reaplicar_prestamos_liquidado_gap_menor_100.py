r"""
Lanzador desde la raiz del repo (pagos/). Ejecuta el script real en backend/ con cwd correcto.

  cd .../GitHub/pagos
  python scripts/reaplicar_prestamos_liquidado_gap_menor_100.py --dry-run --prestamo-id 253
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _ROOT / "backend"
_SCRIPT = _BACKEND / "scripts" / "reaplicar_prestamos_liquidado_gap_menor_100.py"

if not _SCRIPT.is_file():
    print(f"No se encuentra {_SCRIPT}", file=sys.stderr)
    raise SystemExit(1)

r = subprocess.run(
    [sys.executable, str(_SCRIPT), *sys.argv[1:]],
    cwd=str(_BACKEND),
)
raise SystemExit(r.returncode if r.returncode is not None else 1)
