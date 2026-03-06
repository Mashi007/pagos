# Patch: ensure KPIs are explicitly "datos reales" and year param works (anio/año)
import os
base = os.path.dirname(os.path.abspath(__file__))

# 1) Prestamos stats: use "anio" as param name with alias "año" so URL can send either
prestamos_path = os.path.join(base, "backend", "app", "api", "v1", "endpoints", "prestamos.py")
with open(prestamos_path, "r", encoding="utf-8") as f:
    s = f.read()

# Replace the stats function signature and docstring - match exact existing pattern
old_sig = """    mes: Optional[int] = Query(None),
    a\u00f1o: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    \"\"\"Estad\u00edsticas de pr\u00e9stamos mensuales desde BD (solo clientes ACTIVOS)."""
new_sig = """    mes: Optional[int] = Query(None),
    anio: Optional[int] = Query(None, alias="a\u00f1o"),
    db: Session = Depends(get_db),
):
    \"\"\"Estad\u00edsticas de pr\u00e9stamos mensuales desde BD real (solo clientes ACTIVOS)."""

if "anio: Optional[int] = Query(None, alias=" in s:
    print("Prestamos stats: already patched")
else:
    s = s.replace(
        "mes: Optional[int] = Query(None),\n    a\u00f1o: Optional[int] = Query(None),\n    db: Session = Depends(get_db),\n):\n    \"\"\"Estad\u00edsticas de pr\u00e9stamos mensuales desde BD (solo clientes ACTIVOS).",
        new_sig
    )
    if "anio: Optional[int]" not in s:
        # Try without unicode escapes
        s = s.replace(
            "a\u00f1o: Optional[int] = Query(None)",
            'anio: Optional[int] = Query(None, alias="a\u00f1o")'
        )
        s = s.replace(
            "Estad\u00edsticas de pr\u00e9stamos mensuales desde BD (solo clientes ACTIVOS).",
            "Estad\u00edsticas de pr\u00e9stamos mensuales desde BD real (solo clientes ACTIVOS)."
        )
    with open(prestamos_path, "w", encoding="utf-8") as f:
        f.write(s)
    print("Prestamos stats: patched")

# Fix references to "año" inside the function - they must use "anio" now
with open(prestamos_path, "r", encoding="utf-8") as f:
    s = f.read()
# Replace año_u = año with anio
if "a\u00f1o_u = a\u00f1o" in s:
    s = s.replace("a\u00f1o_u = a\u00f1o if a\u00f1o is not None", "a\u00f1o_u = anio if anio is not None")
if "a\u00f1o_u = anio" in s and "a\u00f1o_u = a\u00f1o" in s:
    s = s.replace("a\u00f1o_u = a\u00f1o if a\u00f1o is not None and a\u00f1o >= 2000", "a\u00f1o_u = anio if anio is not None and anio >= 2000")
with open(prestamos_path, "w", encoding="utf-8") as f:
    f.write(s)

# 2) Clientes stats: docstring explicit "datos reales"
clientes_path = os.path.join(base, "backend", "app", "api", "v1", "endpoints", "clientes.py")
with open(clientes_path, "r", encoding="utf-8") as f:
    s = f.read()
if "Datos reales desde BD" in s and "get_clientes_stats" in s:
    # Already has it in module docstring; add to function
    pass
s = s.replace(
    """    \"\"\"
    Estad\u00edsticas de clientes: total, activos, inactivos, finalizados, nuevos_este_mes.
    nuevos_este_mes = clientes con fecha_registro en el mes actual (calendario).
    \"\"\"""",
    """    \"\"\"
    Estad\u00edsticas de clientes desde BD real: total, activos, inactivos, finalizados, nuevos_este_mes.
    nuevos_este_mes = clientes con fecha_registro en el mes actual (calendario).
    \"\"\""""
)
with open(clientes_path, "w", encoding="utf-8") as f:
    f.write(s)
print("Clientes stats: docstring updated")

# 3) Frontend: send anio (ASCII) so backend always receives year
fe_path = os.path.join(base, "frontend", "src", "services", "prestamoService.ts")
with open(fe_path, "r", encoding="utf-8") as f:
    s = f.read()
# Ensure params use "anio" for year so URL is ASCII
old_params = "mes: filters.mes ?? now.getMonth() + 1,\n            a\u00f1o: filters.a\u00f1o ?? now.getFullYear(),"
new_params = "mes: filters.mes ?? now.getMonth() + 1,\n            anio: filters.anio ?? filters.a\u00f1o ?? now.getFullYear(),"
if "anio: filters.anio" in s:
    print("Frontend getKPIs: already sends anio")
else:
    s = s.replace(
        "mes: filters.mes ?? now.getMonth() + 1,\n            a\u00f1o: filters.a\u00f1o ?? now.getFullYear(),",
        "mes: filters.mes ?? now.getMonth() + 1,\n            anio: filters.anio ?? (filters as any).a\u00f1o ?? now.getFullYear(),"
    )
    with open(fe_path, "w", encoding="utf-8") as f:
        f.write(s)
    print("Frontend getKPIs: sends anio param")

print("Done.")
