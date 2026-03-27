# -*- coding: utf-8 -*-
"""Move POST /batch before GET /{pago_id:int} in pagos.py."""
from pathlib import Path

path = Path("backend/app/api/v1/endpoints/pagos.py")
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)


def find_line_contains(sub: str, start: int = 0) -> int:
    for i in range(start, len(lines)):
        if sub in lines[i]:
            return i
    raise SystemExit(f"not found: {sub!r}")


i_batch = find_line_contains('@router.post("/batch", response_model=dict)')
i_get = find_line_contains('@router.get("/{pago_id:int}", response_model=dict)')
if i_batch < i_get:
    print("batch already before get pago_id; nothing to move")
else:
    i_post_create = find_line_contains('@router.post("", response_model=dict, status_code=201)')
    if i_post_create <= i_batch:
        raise SystemExit("unexpected order")
    batch_block = lines[i_batch:i_post_create]
    new_lines = lines[:i_get] + batch_block + lines[i_get:i_batch] + lines[i_post_create:]
    path.write_text("".join(new_lines), encoding="utf-8")
    print("moved batch block before obtener_pago")
