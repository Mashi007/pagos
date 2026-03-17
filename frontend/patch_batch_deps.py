# -*- coding: utf-8 -*-
"""Remove prestamosPorCedula from fallback useEffect deps to avoid repeated batch requests."""
import os
path = os.path.join(os.path.dirname(__file__), "src", "hooks", "useExcelUploadPagos.ts")
with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

# Fallback effect: remove prestamosPorCedula so effect does not re-run after each batch response
old_deps = "}, [showPreview, excelData.length, cedulasUnicas.join(','), prestamosPorCedula])"
new_deps = "}, [showPreview, excelData.length, cedulasUnicas.join(',')])"
if old_deps in c:
    c = c.replace(old_deps, new_deps, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("OK: removed prestamosPorCedula from fallback useEffect deps")
else:
    # Try alternate (different quote)
    old2 = "}, [showPreview, excelData.length, cedulasUnicas.join(\",\"), prestamosPorCedula])"
    if old2 in c:
        c = c.replace(old2, "}, [showPreview, excelData.length, cedulasUnicas.join(\",\")])", 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(c)
        print("OK: removed prestamosPorCedula (alt pattern)")
    else:
        print("Pattern not found")
