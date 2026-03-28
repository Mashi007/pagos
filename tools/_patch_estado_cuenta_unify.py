"""One-shot patch: unify public estado de cuenta data with obtener_datos_estado_cuenta_prestamo."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "backend" / "app" / "services" / "estado_cuenta_pdf.py"
PUB = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "estado_cuenta_publico.py"

NEW_FUNC = '''

def obtener_datos_estado_cuenta_cliente(db, cedula_lookup: str):
    """
    Arma el mismo dict que consume generar_pdf_estado_cuenta para todos los prestamos
    del cliente (cedula normalizada sin guiones). Reutiliza obtener_datos_estado_cuenta_prestamo
    por cada prestamo para que cuotas pendientes, totales y amortizacion coincidan con
    GET /prestamos/{id}/estado-cuenta/pdf y notificaciones liquidado.
    """
    from sqlalchemy import func, select

    from app.models.cliente import Cliente
    from app.models.prestamo import Prestamo
    from app.services.cuota_estado import hoy_negocio
    from app.services.pagos_cuotas_sincronizacion import sincronizar_pagos_pendientes_a_prestamos

    cedula_lookup = (cedula_lookup or "").strip()
    if not cedula_lookup:
        return None

    cliente_row = db.execute(
        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_lookup)
    ).scalars().first()

    if not cliente_row:
        return None

    cliente = cliente_row[0] if hasattr(cliente_row, "__getitem__") else cliente_row
    cliente_id = getattr(cliente, "id", None)
    if not cliente_id:
        return None

    nombre = (getattr(cliente, "nombres", None) or "").strip()
    email = (getattr(cliente, "email", None) or "").strip()
    cedula_display = (getattr(cliente, "cedula", None) or "").strip()

    prestamos_rows = db.execute(
        select(Prestamo).where(Prestamo.cliente_id == cliente_id)
    ).scalars().all()

    prestamo_ids = []
    for row in prestamos_rows:
        p = row[0] if hasattr(row, "__getitem__") else row
        prestamo_ids.append(p.id)

    if prestamo_ids:
        try:
            sincronizar_pagos_pendientes_a_prestamos(db, prestamo_ids)
        except Exception as sync_exc:
            logger.warning(
                "obtener_datos_estado_cuenta_cliente: sincronizar_pagos_pendientes_a_prestamos "
                "cliente_id=%s: %s",
                cliente_id,
                sync_exc,
            )

    merged = {
        "cedula_display": cedula_display,
        "nombre": nombre,
        "email": email,
        "prestamos_list": [],
        "cuotas_pendientes": [],
        "total_pendiente": 0.0,
        "fecha_corte": hoy_negocio(),
        "amortizaciones_por_prestamo": [],
    }

    for pid in prestamo_ids:
        part = obtener_datos_estado_cuenta_prestamo(db, pid, sincronizar=False)
        if not part:
            continue
        merged["fecha_corte"] = part["fecha_corte"]
        merged["prestamos_list"].extend(part["prestamos_list"])
        merged["cuotas_pendientes"].extend(part["cuotas_pendientes"])
        merged["total_pendiente"] += float(part["total_pendiente"] or 0)
        merged["amortizaciones_por_prestamo"].extend(part["amortizaciones_por_prestamo"])

    return merged
'''

old_sig = "def obtener_datos_estado_cuenta_prestamo(db, prestamo_id: int):"
new_sig = "def obtener_datos_estado_cuenta_prestamo(db, prestamo_id: int, sincronizar: bool = True):"

old_try = """    try:

        sincronizar_pagos_pendientes_a_prestamos(db, [prestamo_id])

    except Exception as sync_exc:

        logger.warning(

            "obtener_datos_estado_cuenta_prestamo: sincronizar_pagos_pendientes_a_prestamos prestamo_id=%s: %s",

            prestamo_id,

            sync_exc,

        )

    

    prestamos_list"""

new_try = """    if sincronizar:

        try:

            sincronizar_pagos_pendientes_a_prestamos(db, [prestamo_id])

        except Exception as sync_exc:

            logger.warning(

                "obtener_datos_estado_cuenta_prestamo: sincronizar_pagos_pendientes_a_prestamos prestamo_id=%s: %s",

                prestamo_id,

                sync_exc,

            )

    

    prestamos_list"""

text = PDF.read_text(encoding="utf-8")
if old_sig not in text:
    raise SystemExit("signature not found")
if NEW_FUNC.strip() in text:
    raise SystemExit("already patched estado_cuenta_pdf")
text = text.replace(old_sig, new_sig, 1)
if old_try not in text:
    raise SystemExit("try block not found")
text = text.replace(old_try, new_try, 1)
# Docstring tweak
old_doc = """    Obtiene datos formateados para generar PDF de estado de cuenta de UN prestamo especifico.

    Reutilizable desde endpoints privados (autenticados)."""
new_doc = """    Obtiene datos formateados para generar PDF de estado de cuenta de UN prestamo especifico.

    Reutilizable desde endpoints privados (autenticados) y desde obtener_datos_estado_cuenta_cliente.

    Si sincronizar es False, el llamador debe haber llamado ya sincronizar_pagos_pendientes_a_prestamos."""
text = text.replace(old_doc, new_doc, 1)
text = text.rstrip() + NEW_FUNC
PDF.write_text(text, encoding="utf-8", newline="\n")
print("OK:", PDF)

# --- estado_cuenta_publico.py ---
pub = PUB.read_text(encoding="utf-8")
old_import = "from app.services.estado_cuenta_pdf import generar_pdf_estado_cuenta"
new_import = "from app.services.estado_cuenta_pdf import (\n    generar_pdf_estado_cuenta,\n    obtener_datos_estado_cuenta_cliente,\n)"
if old_import not in pub:
    raise SystemExit("import line not found")
pub = pub.replace(old_import, new_import, 1)

# Remove cuota_estado imports block and pagos sync - only if still present
old_cuota_block = """from app.services.cuota_estado import (
    estado_cuota_para_mostrar,
    etiqueta_estado_cuota,
    hoy_negocio,
    sincronizar_columna_estado_cuotas,
)
"""
if old_cuota_block in pub:
    pub = pub.replace(old_cuota_block, "", 1)

old_sync = "from app.services.pagos_cuotas_sincronizacion import sincronizar_pagos_pendientes_a_prestamos\n\n"
if old_sync in pub:
    pub = pub.replace(old_sync, "", 1)

marker_start = "def _obtener_datos_pdf(db: Session, cedula_lookup: str):"
marker_end = "@router.get(\"/recibo-cuota\")"
si = pub.find(marker_start)
ei = pub.find(marker_end)
if si == -1 or ei == -1 or ei <= si:
    raise SystemExit("markers for _obtener_datos_pdf block not found")

replacement = '''def _obtener_datos_pdf(db: Session, cedula_lookup: str):
    """Delega en obtener_datos_estado_cuenta_cliente (misma logica que PDF por prestamo)."""
    return obtener_datos_estado_cuenta_cliente(db, cedula_lookup)


'''

pub = pub[:si] + replacement + pub[ei:]
PUB.write_text(pub, encoding="utf-8", newline="\n")
print("OK:", PUB)
