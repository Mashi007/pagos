# -*- coding: utf-8 -*-
"""Wrap crear_pagos_batch in try/except OperationalError -> 503."""
import os
path = os.path.join(os.path.dirname(__file__), "app", "api", "v1", "endpoints", "pagos.py")
with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

# Add OperationalError to existing import
c = c.replace(
    "from sqlalchemy.exc import IntegrityError",
    "from sqlalchemy.exc import IntegrityError, OperationalError",
)

# Find start of crear_pagos_batch body (after docstring)
start = c.find('def crear_pagos_batch(')
if start == -1:
    print("crear_pagos_batch not found")
    exit(1)
# First line of body after docstring: usuario_email = ...
body_start = c.find("\n    usuario_email = current_user.email", start)
if body_start == -1:
    body_start = c.find("\n    usuario_email = ", start)
if body_start == -1:
    print("body start not found")
    exit(1)
body_start += 1  # include the newline

# End of function: next @router at column 0
next_router = c.find("\n@router.", body_start)
if next_router == -1:
    next_router = len(c)
func_end = next_router

body = c[body_start:func_end]
# Indent body by 4 spaces for try block
indented = "\n".join("    " + line if line.strip() else line for line in body.split("\n"))
except_block = """except OperationalError:
        from fastapi import HTTPException
        from fastapi import status
        raise HTTPException(
            status_code=503,
            detail="Servicio no disponible. Reintente en unos segundos.",
        )
"""
# Check if HTTPException is already imported
if "from fastapi import" in c[:2000]:
    except_block = """except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="Servicio no disponible. Reintente en unos segundos.",
        )
"""
new_body = "    try:\n" + indented + "\n" + except_block
new_c = c[:body_start] + new_body + c[func_end:]
with open(path, "w", encoding="utf-8") as f:
    f.write(new_c)
print("pagos.py crear_pagos_batch: OperationalError -> 503 added")
