from pathlib import Path
p = Path("frontend/src/pages/Notificaciones.tsx")
t = p.read_text(encoding="utf-8")
old = (
    "                      ? 'Una fila por cliente con al menos una cuota a 60 o más días de atraso. "
    "La cuota y fecha mostradas son la más antigua en ese rango; «Cuotas atrasadas» cuenta las cuotas "
    "del cliente que cumplen ≥60 días. Permanecen hasta ponerse al día. Envío solo manual "
    "(sin automático ni «enviar todas»); To = cliente; CCO = cobranza@ y notificaciones@.'"
)
new = (
    "                      ? 'Una fila por préstamo con 2 o más cuotas vencidas pendientes "
    "(atraso >= 1 día). Segunda en jerarquía: si el titular está en día siguiente no aparece aquí; "
    "prioriza sobre 1 Cuota. Envío solo manual (sin automático ni «enviar todas»); "
    "To = cliente; From notificaciones@.'"
)
assert old in t, "a2cuotas card desc missing"
t = t.replace(old, new)
# general: clarify hierarchy reduces overlap for mora cases
old_g = (
    "Un mismo cliente puede aparecer más de una vez si cumple varios criterios. "
)
new_g = (
    "En mora (día siguiente / 2 Cuotas) la jerarquía evita solape; otros criterios sí pueden repetir cliente. "
)
if old_g in t:
    t = t.replace(old_g, new_g)
p.write_text(t, encoding="utf-8")
print("FE card OK")
