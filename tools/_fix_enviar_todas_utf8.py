# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "notificaciones.py"
t = p.read_text(encoding="utf-8", errors="replace")
start = t.index('@router.post("/enviar-todas")')
end = t.index('@router.get("/estadisticas/resumen")')
new_block = '''@router.post("/enviar-todas")
def enviar_todas_notificaciones(background_tasks: BackgroundTasks):
    """
    Inicia el envio de todas las notificaciones en segundo plano.
    Responde 202 de inmediato para evitar timeout (el envio puede tardar muchos minutos).
    Respeta la configuracion guardada (modo_pruebas, email_pruebas, habilitado por tipo).
    """
    background_tasks.add_task(_tarea_envio_todas_notificaciones)
    return JSONResponse(
        status_code=202,
        content={
            "mensaje": (
                "Envio iniciado en segundo plano. Los correos se enviaran en los proximos minutos. "
                "Puedes cerrar esta ventana."
            ),
            "en_proceso": True,
        },
    )


'''
t2 = t[:start] + new_block + t[end:]
p.write_text(t2, encoding="utf-8", newline="\n")
print("OK fixed enviar-todas block (ASCII-safe Spanish)")
