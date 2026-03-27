from pathlib import Path
import re

p = Path("backend/app/api/v1/endpoints/prestamos.py")
s = p.read_text(encoding="utf-8")

old_imp = """from app.services.prestamo_estado_coherencia import (
    condicion_filtro_estado_prestamo,
    prestamo_bloquea_insertar_filas_cuota_si_liquidado_bd,
    prestamo_bloquea_nuevas_cuotas_o_cambio_plazo,
    prestamo_ids_aprobados_todas_cuotas_cubiertas,
)
"""
new_imp = old_imp + """from app.services.prestamo_db_compat import (
    fetch_prestamos_fecha_desistimiento_map,
    prestamos_tiene_columna_fecha_desistimiento,
)
"""
if "prestamo_db_compat" not in s:
    assert old_imp in s, "import block not found"
    s = s.replace(old_imp, new_imp, 1)

if "fd_desist_map = fetch_prestamos_fecha_desistimiento_map" not in s:
    s = s.replace(
        "    prestamo_ids = [row[0].id for row in rows]\n\n",
        "    prestamo_ids = [row[0].id for row in rows]\n\n"
        "    fd_desist_map = fetch_prestamos_fecha_desistimiento_map(db, prestamo_ids)\n\n",
        1,
    )

main_tail = """            revision_manual_estado=revision_manual_estados.get(p.id),  # None si no existe

        )

        items.append(item)"""
main_new = """            revision_manual_estado=revision_manual_estados.get(p.id),  # None si no existe

            fecha_desistimiento=fd_desist_map.get(p.id),

        )

        items.append(item)"""
if "fecha_desistimiento=fd_desist_map.get" not in s:
    assert main_tail in s, "main list tail missing"
    s = s.replace(main_tail, main_new, 1)

ced_needle = (
    "        prestamo_ids = [row[0].id for row in rows]\n\n        cuotas_por_prestamo = {}"
)
ced_rep = (
    "        prestamo_ids = [row[0].id for row in rows]\n\n"
    "        fd_desist_map_ced = fetch_prestamos_fecha_desistimiento_map(db, prestamo_ids)\n\n"
    "        cuotas_por_prestamo = {}"
)
if "fd_desist_map_ced" not in s:
    assert ced_needle in s, "cedula needle missing"
    s = s.replace(ced_needle, ced_rep, 1)

ced_block = """                PrestamoListResponse(

                    id=p.id,

                    cliente_id=p.cliente_id,

                    total_financiamiento=p.total_financiamiento,

                    estado=estado_resp,

                    concesionario=p.concesionario,

                    modelo=p.modelo,

                    analista=p.analista,

                    fecha_creacion=p.fecha_creacion,

                    fecha_actualizacion=p.fecha_actualizacion,

                    fecha_registro=p.fecha_registro,

                    fecha_aprobacion=p.fecha_aprobacion,

                    nombres=nombres_cliente or p.nombres,

                    cedula=cedula_cliente or p.cedula,

                    numero_cuotas=numero_cuotas,

                    modalidad_pago=p.modalidad_pago,

                )"""
ced_block_new = """                PrestamoListResponse(

                    id=p.id,

                    cliente_id=p.cliente_id,

                    total_financiamiento=p.total_financiamiento,

                    estado=estado_resp,

                    concesionario=p.concesionario,

                    modelo=p.modelo,

                    analista=p.analista,

                    fecha_creacion=p.fecha_creacion,

                    fecha_actualizacion=p.fecha_actualizacion,

                    fecha_registro=p.fecha_registro,

                    fecha_aprobacion=p.fecha_aprobacion,

                    nombres=nombres_cliente or p.nombres,

                    cedula=cedula_cliente or p.cedula,

                    numero_cuotas=numero_cuotas,

                    modalidad_pago=p.modalidad_pago,

                    fecha_desistimiento=fd_desist_map_ced.get(p.id),

                )"""
if "fecha_desistimiento=fd_desist_map_ced.get" not in s:
    assert ced_block in s, "cedula PrestamoListResponse missing"
    s = s.replace(ced_block, ced_block_new, 1)

upd_old = """    if est_despues == "DESISTIMIENTO" and est_antes != "DESISTIMIENTO":

        if getattr(row, "fecha_desistimiento", None) is None:

            row.fecha_desistimiento = hoy_negocio()

        cli_des = db.get(Cliente, row.cliente_id)"""
upd_new = """    if est_despues == "DESISTIMIENTO" and est_antes != "DESISTIMIENTO":

        if prestamos_tiene_columna_fecha_desistimiento(db):

            db.execute(

                text(

                    "UPDATE prestamos SET fecha_desistimiento = :fd "

                    "WHERE id = :pid AND fecha_desistimiento IS NULL"

                ),

                {"fd": hoy_negocio(), "pid": prestamo_id},

            )

        cli_des = db.get(Cliente, row.cliente_id)"""
if "UPDATE prestamos SET fecha_desistimiento" not in s:
    assert upd_old in s, "update DESISTIMIENTO block missing"
    s = s.replace(upd_old, upd_new, 1)

if "fd_one = fetch_prestamos_fecha_desistimiento_map" not in s:
    m = re.search(
        r"(    resp = PrestamoResponse\.model_validate\(p\)\n\n)"
        r"(    # Preferir cedula/nombres del cliente \(join\) si faltan o vac.+\n\n)"
        r"(    resp\.nombres = nombres_cliente or p\.nombres or \"\"\n)",
        s,
    )
    assert m, "get_prestamo validate/comment/nombres block not found"
    insert = (
        m.group(1)
        + "    fd_one = fetch_prestamos_fecha_desistimiento_map(db, [prestamo_id])\n\n"
        + "    if prestamo_id in fd_one:\n\n"
        + "        resp.fecha_desistimiento = fd_one[prestamo_id]\n\n"
        + m.group(2)
        + m.group(3)
    )
    s = s[: m.start()] + insert + s[m.end() :]

p.write_text(s, encoding="utf-8")
print("OK")
