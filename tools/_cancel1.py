from pathlib import Path

# Pipeline: cancel check + return flag
path = Path("backend/app/services/notificaciones_envio_pipeline.py")
text = path.read_text(encoding="utf-8")

if "cancelado_usuario = False" not in text:
    text = text.replace(
        "    pausado_limite_gmail = False\n    motivo_pausa = None\n    ultimo_procesado = 0\n",
        "    pausado_limite_gmail = False\n    cancelado_usuario = False\n    motivo_pausa = None\n    ultimo_procesado = 0\n",
        1,
    )
    print("vars ok")
else:
    print("vars already")

# Find the for loop over items and add check at start
# Look for "for idx, item in enumerate(items):"
marker = "for idx, item in enumerate(items):"
idx = text.find(marker)
if idx < 0:
    raise SystemExit("for loop missing")
# insert after the for line
line_end = text.find("\n", idx)
insert = '''
        if db is not None:
            try:
                from app.services.notificaciones_envio_cancel import (
                    cancelacion_lote_activa,
                )

                if cancelacion_lote_activa(db):
                    cancelado_usuario = True
                    motivo_pausa = "cancelado_por_usuario"
                    logger.warning(
                        "[notif_envio] lote cancelado por usuario en item idx=%s/%s",
                        idx,
                        total_items,
                    )
                    break
            except Exception:
                logger.debug("[notif_envio] check cancel fallo", exc_info=True)
'''
# Only insert once
if "lote cancelado por usuario" in text:
    print("loop check already")
else:
    # next line after for should be indented body - insert at beginning of body
    text = text[: line_end + 1] + insert + text[line_end + 1 :]
    print("loop check ok")

# Also break path like pausado
old_break = """        ultimo_procesado = idx + 1
        _report_progress(ultimo_procesado)
        if pausado_limite_gmail:
            break
"""
new_break = """        ultimo_procesado = idx + 1
        _report_progress(ultimo_procesado)
        if pausado_limite_gmail or cancelado_usuario:
            break
"""
if "pausado_limite_gmail or cancelado_usuario" in text:
    print("break already")
elif old_break not in text:
    raise SystemExit("break missing")
else:
    text = text.replace(old_break, new_break, 1)
    print("break ok")

old_ret = '''        "procesados": int(ultimo_procesado if pausado_limite_gmail else total_items),
        "pausado_limite_gmail": bool(pausado_limite_gmail),
        "motivo_pausa": motivo_pausa,
    }
'''
new_ret = '''        "procesados": int(
            ultimo_procesado
            if (pausado_limite_gmail or cancelado_usuario)
            else total_items
        ),
        "pausado_limite_gmail": bool(pausado_limite_gmail),
        "cancelado_usuario": bool(cancelado_usuario),
        "motivo_pausa": motivo_pausa,
    }
'''
if '"cancelado_usuario": bool(cancelado_usuario)' in text:
    print("ret already")
elif old_ret not in text:
    raise SystemExit("ret missing")
else:
    text = text.replace(old_ret, new_ret, 1)
    print("ret ok")

path.write_text(text, encoding="utf-8")
print("pipeline done")
