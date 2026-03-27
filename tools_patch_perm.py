from pathlib import Path
p = Path("frontend/src/hooks/usePermissions.ts")
t = p.read_text(encoding="utf-8")
old = """  const canEditPrestamo = (prestamoEstado: string): boolean => {
    if (!prestamoEstado) return false

    if (isAdmin()) {
      return true // Admin puede editar siempre
    }

    return prestamoEstado === 'DRAFT' // User solo puede editar DRAFT
  }"""
new = """  const canEditPrestamo = (prestamoEstado: string): boolean => {
    if (!prestamoEstado) return false

    if (prestamoEstado === 'DESISTIMIENTO') {
      return false
    }

    if (isAdmin()) {
      return true // Admin puede editar siempre
    }

    return prestamoEstado === 'DRAFT' // User solo puede editar DRAFT
  }"""
if old not in t:
    raise SystemExit("canEditPrestamo block not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8", newline="\n")
print("usePermissions ok")
