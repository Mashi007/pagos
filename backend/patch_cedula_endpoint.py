"""Add try/except to listar_prestamos_por_cedula to avoid 500 on errors."""
import os
path = os.path.join(os.path.dirname(__file__), "app", "api", "v1", "endpoints", "prestamos.py")
with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

def_start = c.find("def listar_prestamos_por_cedula(cedula: str, db: Session = Depends(get_db)):")
if def_start == -1:
    print("DEF NOT FOUND")
    exit(1)

line_end = c.find("\n", def_start)
rest = c[line_end + 1 :]
body_start_global = line_end + 1 + rest.find("    cedula_clean = ")
if body_start_global <= line_end + 1:
    print("BODY NOT FOUND")
    exit(1)

next_router = c.find("@router.", body_start_global + 1)
func_end = c.rfind("\n", body_start_global, next_router) + 1
body = c[body_start_global:func_end]
indented = "\n".join("    " + line if line.strip() else line for line in body.split("\n"))
except_block = (
    "    except Exception as e:\n"
    "        logger.exception(\"listar_prestamos_por_cedula error: %s\", e)\n"
    "        return {\"prestamos\": [], \"total\": 0}\n"
)
new_body = "    try:\n" + indented + "\n" + except_block
new_c = c[:body_start_global] + new_body + c[func_end:]
with open(path, "w", encoding="utf-8") as f:
    f.write(new_c)
print("OK: try/except added to listar_prestamos_por_cedula")
