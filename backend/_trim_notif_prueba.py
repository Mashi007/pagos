from pathlib import Path

p = Path(__file__).resolve().parent / "app" / "api" / "v1" / "endpoints" / "notificaciones.py"
t = p.read_text(encoding="utf-8")
marker = "\n\n# --- Prueba de paquete completo (plantilla + Carta PDF + PDFs fijos) ---\n"
if marker not in t:
    raise SystemExit("marker not found")
idx = t.index(marker)
new_tail = '''

@router.post("/enviar-prueba-paquete")
def post_enviar_prueba_paquete(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Delega en servicio unico (evita duplicar logica con el router)."""
    from app.services.notificaciones_prueba_paquete import ejecutar_enviar_prueba_paquete

    return ejecutar_enviar_prueba_paquete(db, payload)
'''
p.write_text(t[:idx].rstrip() + new_tail + "\n", encoding="utf-8")
print("trimmed", p)
