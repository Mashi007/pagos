# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent / "app" / "api" / "v1" / "endpoints" / "notificaciones_tabs.py"
t = p.read_text(encoding="utf-8")
old = """        if paquete_estricto:
            ok_pkg, mot_pkg = _adjuntos_cumplen_paquete_completo(attachments)
            if not ok_pkg:
                log_envio_paquete_incompleto(item_id_log, mot_pkg, tipo)
                omitidos_paquete_incompleto += 1
                continue

        # Mismo HTML y adjuntos que produccion; destino: prueba o cliente."""
new = """        if paquete_estricto:
            ok_pkg, mot_pkg = _adjuntos_cumplen_paquete_completo(attachments)
            if not ok_pkg:
                relax_prueba = bool(
                    getattr(settings, "NOTIFICACIONES_PAQUETE_RELAX_SOLO_PRUEBA_DESTINO", False)
                )
                if relax_prueba and forzar_destinos_prueba is not None:
                    log = logging.getLogger(__name__)
                    log.warning(
                        "[notif_envio_paquete] RELAX_SOLO_PRUEBA_DESTINO: se envia correo de prueba con paquete "
                        "incompleto (%s). No aplica a envios masivos reales.",
                        mot_pkg,
                    )
                else:
                    log_envio_paquete_incompleto(item_id_log, mot_pkg, tipo)
                    omitidos_paquete_incompleto += 1
                    continue

        # Mismo HTML y adjuntos que produccion; destino: prueba o cliente."""
if old not in t:
    raise SystemExit("tabs block not found")
t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print("ok tabs")
