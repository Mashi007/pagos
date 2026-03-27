from pathlib import Path

p = Path("backend/app/api/v1/endpoints/prestamos.py")
s = p.read_text(encoding="utf-8")

old = """from app.services.prestamo_estado_coherencia import (
    condicion_filtro_estado_prestamo,
    prestamo_bloquea_insertar_filas_cuota_si_liquidado_bd,
    prestamo_bloquea_nuevas_cuotas_o_cambio_plazo,
    prestamo_ids_aprobados_todas_cuotas_cubiertas,
)
"""
new = old + """from app.services.prestamo_db_compat import (
    fetch_prestamos_fecha_desistimiento_map,
    prestamos_tiene_columna_fecha_desistimiento,
)
"""
if new not in s:
    assert old in s, "import block not found"
    s = s.replace(old, new, 1)

marker = "    prestamo_ids = [row[0].id for row in rows]\n\n    # Conteo de cuotas por prAcstamo (para mostrar en columna Cuotas)"
ins = "    prestamo_ids = [row[0].id for row in rows]\n\n    fd_desist_map = fetch_prestamos_fecha_desistimiento_map(db, prestamo_ids)\n\n    # Conteo de cuotas por prAcstamo (para mostrar en columna Cuotas)"
if ins not in s:
    assert marker in s, "list marker1 not found"
    s = s.replace(marker, ins, 1)

block = """            revision_manual_estado=revision_manual_estados.get(p.id),  # None si no existe

        )

        items.append(item)"""
block_new = """            revision_manual_estado=revision_manual_estados.get(p.id),  # None si no existe

            fecha_desistimiento=fd_desist_map.get(p.id),

        )

        items.append(item)"""
if block_new not in s:
    assert block in s, "PrestamoListResponse block not found"
    s = s.replace(block, block_new, 1)

m2 = "        prestamo_ids = [row[0].id for row in rows]\n\n        cuotas_por_prestamo = {}"
m2_ins = "        prestamo_ids = [row[0].id for row in rows]\n\n        fd_desist_map_ced = fetch_prestamos_fecha_desistimiento_map(db, prestamo_ids)\n\n        cuotas_por_prestamo = {}"
if m2_ins not in s:
    assert m2 in s, "cedula marker not found"
    s = s.replace(m2, m2_ins, 1)

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
ced_new = """                PrestamoListResponse(

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
if ced_new not in s:
    assert ced_block in s, "cedula PrestamoListResponse not found"
    s = s.replace(ced_block, ced_new, 1)

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
if upd_new not in s:
    assert upd_old in s, "update DESISTIMIENTO block not found"
    s = s.replace(upd_old, upd_new, 1)

get_old = """    resp = PrestamoResponse.model_validate(p)

    # Preferir cedula/nombres del cliente (join) si faltan o vacA-os en prestamo"""
get_new = """    resp = PrestamoResponse.model_validate(p)

    fd_one = fetch_prestamos_fecha_desistimiento_map(db, [prestamo_id])

    if prestamo_id in fd_one:

        resp.fecha_desistimiento = fd_one[prestamo_id]

    # Preferir cedula/nombres del cliente (join) si faltan o vacA-os en prestamo"""
if get_new not in s:
    assert get_old in s, "get_prestamo block not found"
    s = s.replace(get_old, get_new, 1)

p.write_text(s, encoding="utf-8")
print("OK")
