# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent / "app" / "api" / "v1" / "endpoints" / "notificaciones.py"
t = p.read_text(encoding="utf-8")
if "diagnostico-paquete-prueba" in t:
    print("router already")
    raise SystemExit(0)

# ensure Query imported
if "Query" not in t.split("from fastapi import")[1].split("\n")[0] if "from fastapi import" in t else "":
    t = t.replace(
        "from fastapi import APIRouter, Depends, HTTPException, Body, Query, File, UploadFile, BackgroundTasks",
        "from fastapi import APIRouter, Depends, HTTPException, Body, Query, File, UploadFile, BackgroundTasks",
    )

needle = '''@router.post("/enviar-prueba-paquete")
def post_enviar_prueba_paquete(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Delega en servicio unico (evita duplicar logica con el router)."""
    from app.services.notificaciones_prueba_paquete import ejecutar_enviar_prueba_paquete

    return ejecutar_enviar_prueba_paquete(db, payload)
'''

insert = '''@router.get("/diagnostico-paquete-prueba")
def get_diagnostico_paquete_prueba(
    tipo: str = Query("PAGO_1_DIA_ATRASADO"),
    db: Session = Depends(get_db),
):
    """Sin enviar correo: revisa plantilla, adjuntos y paquete estricto para el criterio."""
    from app.services.notificaciones_prueba_paquete import ejecutar_diagnostico_paquete_prueba

    return ejecutar_diagnostico_paquete_prueba(db, tipo)


@router.post("/enviar-prueba-paquete")
def post_enviar_prueba_paquete(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Delega en servicio unico (evita duplicar logica con el router)."""
    from app.services.notificaciones_prueba_paquete import ejecutar_enviar_prueba_paquete

    return ejecutar_enviar_prueba_paquete(db, payload)
'''

if needle not in t:
    raise SystemExit("needle not found for router")
t = t.replace(needle, insert, 1)
p.write_text(t, encoding="utf-8")
print("ok router")
