from pathlib import Path

p = Path("backend/app/services/notificacion_service.py")
t = p.read_text(encoding="utf-8")

# Block 1: PAGO_1_DIA_ATRASADO example — remove prejudicial exclusion
old1 = '''            from app.services.notificaciones_dedup_segmentos import (
                clientes_en_regla_prejudicial,
                item_excluido_por_prejudicial_en_envio,
                item_excluido_por_cobranzas_excel_en_envio,
            )
            from app.services.notificaciones_cobranzas_excel import (
                clientes_en_regla_cobranzas_excel,
            )

            cids_prej, ceds_prej = clientes_en_regla_prejudicial(db, hoy)
            cids_cob, ceds_cob = clientes_en_regla_cobranzas_excel(db, hoy)
            for cuota, cliente in ((r[0], r[1]) for r in rows):
                item = format_cuota_item(
                    cliente,
                    cuota,
                    dias_atraso=1,
                    cuotas_atrasadas=counts.get(cuota.prestamo_id, 0),
                    for_tab=True,
                    total_pendiente_pagar=totales.get(cuota.prestamo_id),
                )
                if item_excluido_por_prejudicial_en_envio(
                    "PAGO_1_DIA_ATRASADO", item, cids_prej, ceds_prej
                ):
                    continue
                if item_excluido_por_cobranzas_excel_en_envio(
                    "PAGO_1_DIA_ATRASADO", item, cids_cob, ceds_cob
                ):
                    continue
                return item
            return None'''

new1 = '''            from app.services.notificaciones_dedup_segmentos import (
                item_excluido_por_cobranzas_excel_en_envio,
            )
            from app.services.notificaciones_cobranzas_excel import (
                clientes_en_regla_cobranzas_excel,
            )

            cids_cob, ceds_cob = clientes_en_regla_cobranzas_excel(db, hoy)
            for cuota, cliente in ((r[0], r[1]) for r in rows):
                item = format_cuota_item(
                    cliente,
                    cuota,
                    dias_atraso=1,
                    cuotas_atrasadas=counts.get(cuota.prestamo_id, 0),
                    for_tab=True,
                    total_pendiente_pagar=totales.get(cuota.prestamo_id),
                )
                if item_excluido_por_cobranzas_excel_en_envio(
                    "PAGO_1_DIA_ATRASADO", item, cids_cob, ceds_cob
                ):
                    continue
                return item
            return None'''

assert old1 in t, "block1 missing"
t = t.replace(old1, new1)

old2 = '''        from app.services.notificaciones_dedup_segmentos import (
            clientes_en_regla_prejudicial,
            item_excluido_por_prejudicial_en_envio,
            item_excluido_por_cobranzas_excel_en_envio,
        )
        from app.services.notificaciones_cobranzas_excel import (
            clientes_en_regla_cobranzas_excel,
        )

        cids_prej, ceds_prej = clientes_en_regla_prejudicial(db, hoy)
        cids_cob, ceds_cob = clientes_en_regla_cobranzas_excel(db, hoy)
        for row in rows:
            cuota, cliente = row[0], row[1]
            ca = counts.get(cuota.prestamo_id, 0)
            if not prestamo_aplica_listado_10_dias_por_cuotas_atrasadas(ca):
                continue
            fv = cuota.fecha_vencimiento
            if not fv:
                continue
            dias_atraso = (hoy - fv).days
            if not cuota_aplica_listado_10_dias_por_dias_atraso(dias_atraso):
                continue
            item = format_cuota_item(
                cliente,
                cuota,
                dias_atraso=dias_atraso,
                cuotas_atrasadas=ca,
                for_tab=True,
                total_pendiente_pagar=totales.get(cuota.prestamo_id),
            )
            if item_excluido_por_prejudicial_en_envio(
                "PAGO_10_DIAS_ATRASADO", item, cids_prej, ceds_prej
            ):
                continue
            if item_excluido_por_cobranzas_excel_en_envio(
                "PAGO_10_DIAS_ATRASADO", item, cids_cob, ceds_cob
            ):
                continue
            return item
        return None'''

new2 = '''        from app.services.notificaciones_dedup_segmentos import (
            clientes_en_regla_dia_siguiente,
            clientes_en_regla_prejudicial,
            item_excluido_por_dia_siguiente_en_envio,
            item_excluido_por_prejudicial_en_envio,
            item_excluido_por_cobranzas_excel_en_envio,
        )
        from app.services.notificaciones_cobranzas_excel import (
            clientes_en_regla_cobranzas_excel,
        )

        cids_dia, ceds_dia = clientes_en_regla_dia_siguiente(db, hoy)
        cids_prej, ceds_prej = clientes_en_regla_prejudicial(db, hoy)
        cids_cob, ceds_cob = clientes_en_regla_cobranzas_excel(db, hoy)
        for row in rows:
            cuota, cliente = row[0], row[1]
            ca = counts.get(cuota.prestamo_id, 0)
            if not prestamo_aplica_listado_10_dias_por_cuotas_atrasadas(ca):
                continue
            fv = cuota.fecha_vencimiento
            if not fv:
                continue
            dias_atraso = (hoy - fv).days
            if not cuota_aplica_listado_10_dias_por_dias_atraso(dias_atraso):
                continue
            item = format_cuota_item(
                cliente,
                cuota,
                dias_atraso=dias_atraso,
                cuotas_atrasadas=ca,
                for_tab=True,
                total_pendiente_pagar=totales.get(cuota.prestamo_id),
            )
            if item_excluido_por_dia_siguiente_en_envio(
                "PAGO_10_DIAS_ATRASADO", item, cids_dia, ceds_dia
            ):
                continue
            if item_excluido_por_prejudicial_en_envio(
                "PAGO_10_DIAS_ATRASADO", item, cids_prej, ceds_prej
            ):
                continue
            if item_excluido_por_cobranzas_excel_en_envio(
                "PAGO_10_DIAS_ATRASADO", item, cids_cob, ceds_cob
            ):
                continue
            return item
        return None'''

assert old2 in t, "block2 missing"
t = t.replace(old2, new2)

# Fix stale PREJUDICIAL comment
t = t.replace(
    "        # Misma regla canónica que listado/envio (exactamente 2 totales, ambas >= 60).\n",
    "        # Misma regla canonica que listado/envio (>=2 atrasadas; sin dia siguiente).\n",
)

p.write_text(t, encoding="utf-8")
print("notificacion_service OK")
