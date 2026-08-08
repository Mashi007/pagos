from pathlib import Path

# --- pipeline ---
p = Path("backend/app/services/notificaciones_envio_pipeline.py")
t = p.read_text(encoding="utf-8")
old_imp = (
    "from app.services.notificaciones_dedup_segmentos import (\n"
    "    clientes_en_regla_prejudicial,\n"
    "    item_excluido_por_prejudicial_en_envio,\n"
    "    item_excluido_por_cobranzas_excel_en_envio,\n"
    "    item_excluido_por_cuotas_4_mas_en_envio,\n"
    ")"
)
new_imp = (
    "from app.services.notificaciones_dedup_segmentos import (\n"
    "    clientes_en_regla_dia_siguiente,\n"
    "    clientes_en_regla_prejudicial,\n"
    "    item_excluido_por_dia_siguiente_en_envio,\n"
    "    item_excluido_por_prejudicial_en_envio,\n"
    "    item_excluido_por_cobranzas_excel_en_envio,\n"
    "    item_excluido_por_cuotas_4_mas_en_envio,\n"
    ")"
)
assert old_imp in t, "pipeline import missing"
t = t.replace(old_imp, new_imp)

old_load = (
    "    # Exclusion mutua: titulares en 2 Cuotas / Cobranzas Excel no reciben segmentos inferiores.\n"
    "    claves_prej: tuple = (set(), set())\n"
    "    claves_cobex: tuple = (set(), set())\n"
    "    claves_c4mas: tuple = (set(), set())\n"
    "    if db is not None:\n"
    "        try:\n"
    "            claves_prej = clientes_en_regla_prejudicial(db)\n"
)
new_load = (
    "    # Jerarquia: dia siguiente > 2 Cuotas > 1 Cuota (+ legacy Cobranzas/4+).\n"
    "    claves_dia: tuple = (set(), set())\n"
    "    claves_prej: tuple = (set(), set())\n"
    "    claves_cobex: tuple = (set(), set())\n"
    "    claves_c4mas: tuple = (set(), set())\n"
    "    if db is not None:\n"
    "        try:\n"
    "            claves_dia = clientes_en_regla_dia_siguiente(db)\n"
    "        except Exception:\n"
    "            logger.exception(\n"
    "                \"[notif_dedup] fallo consulta dia siguiente; abortando lote (fail-closed)\"\n"
    "            )\n"
    "            raise\n"
    "        try:\n"
    "            claves_prej = clientes_en_regla_prejudicial(db)\n"
)
assert old_load in t, "pipeline load missing"
t = t.replace(old_load, new_load)

old_check = (
    "            if item_excluido_por_prejudicial_en_envio(\n"
    "                tipo, item, claves_prej[0], claves_prej[1]\n"
    "            ):\n"
    "                logger.info(\n"
    "                    \"[notif_dedup] Omitido por exclusion mutua (titular en 2 Cuotas) \"\n"
    "                    \"cliente_id=%s prestamo_id=%s item=%s tipo=%s\",\n"
    "                    cid,\n"
    "                    item.get(\"prestamo_id\"),\n"
    "                    item_id_log,\n"
    "                    tipo,\n"
    "                )\n"
    "                omitidos_desistimiento += 1\n"
    "                _report_progress(idx + 1)\n"
    "                continue\n"
)
new_check = (
    "            if item_excluido_por_dia_siguiente_en_envio(\n"
    "                tipo, item, claves_dia[0], claves_dia[1]\n"
    "            ):\n"
    "                logger.info(\n"
    "                    \"[notif_dedup] Omitido por exclusion mutua (titular en dia siguiente) \"\n"
    "                    \"cliente_id=%s prestamo_id=%s item=%s tipo=%s\",\n"
    "                    cid,\n"
    "                    item.get(\"prestamo_id\"),\n"
    "                    item_id_log,\n"
    "                    tipo,\n"
    "                )\n"
    "                omitidos_desistimiento += 1\n"
    "                _report_progress(idx + 1)\n"
    "                continue\n"
    "            if item_excluido_por_prejudicial_en_envio(\n"
    "                tipo, item, claves_prej[0], claves_prej[1]\n"
    "            ):\n"
    "                logger.info(\n"
    "                    \"[notif_dedup] Omitido por exclusion mutua (titular en 2 Cuotas) \"\n"
    "                    \"cliente_id=%s prestamo_id=%s item=%s tipo=%s\",\n"
    "                    cid,\n"
    "                    item.get(\"prestamo_id\"),\n"
    "                    item_id_log,\n"
    "                    tipo,\n"
    "                )\n"
    "                omitidos_desistimiento += 1\n"
    "                _report_progress(idx + 1)\n"
    "                continue\n"
)
assert old_check in t, "pipeline check missing"
t = t.replace(old_check, new_check)
p.write_text(t, encoding="utf-8")
print("pipeline OK")

# --- routes docstring ---
p = Path("backend/app/api/v1/endpoints/notificaciones/routes.py")
t = p.read_text(encoding="utf-8")
old = (
    "    Lista «2 Cuotas» (a-2-cuotas): >=2 cuotas impagas atrasadas (atraso >= 1 dia).\n"
    "    Sin tope. Prioridad sobre 1 Cuota y dia siguiente.\n"
    "    Un item por prestamo. Revalida cada item antes de devolverlo."
)
new = (
    "    Lista «2 Cuotas» (a-2-cuotas): >=2 cuotas impagas atrasadas (atraso >= 1 dia).\n"
    "    Sin tope. Segunda en jerarquia: no incluye titulares en dia siguiente;\n"
    "    prioriza sobre «1 Cuota». Un item por prestamo. Revalida cada item."
)
assert old in t, "routes docstring missing"
t = t.replace(old, new)
# also fix stale comment
t = t.replace(
    "    # Regla unica: exactamente 2 atrasadas TOTALES y ambas >= 60 dias.\n",
    "    # Regla unica: >=2 atrasadas (atraso >=1); select ya excluye dia siguiente.\n",
)
p.write_text(t, encoding="utf-8")
print("routes OK")
