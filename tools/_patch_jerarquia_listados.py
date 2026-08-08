from pathlib import Path

p = Path("backend/app/services/notificaciones_listados_motor.py")
t = p.read_text(encoding="utf-8")

old_imp = (
    "from app.services.notificaciones_dedup_segmentos import (\n"
    "    clientes_en_regla_prejudicial,\n"
    "    filtrar_items_sin_cobranzas_excel,\n"
    "    filtrar_items_sin_cuotas_4_mas,\n"
    "    filtrar_items_sin_prejudicial,\n"
    ")"
)
new_imp = (
    "from app.services.notificaciones_dedup_segmentos import (\n"
    "    clientes_en_regla_dia_siguiente,\n"
    "    clientes_en_regla_prejudicial,\n"
    "    filtrar_items_sin_cobranzas_excel,\n"
    "    filtrar_items_sin_cuotas_4_mas,\n"
    "    filtrar_items_sin_dia_siguiente,\n"
    "    filtrar_items_sin_prejudicial,\n"
    ")"
)
assert old_imp in t, "import block missing"
t = t.replace(old_imp, new_imp)

old_doc = (
    "    En ambas listas se excluyen los titulares que ya cumplen «2 Cuotas» (prejudicial):\n"
    "    un mismo cliente no debe recibir dos notificaciones el mismo día."
)
new_doc = (
    "    Jerarquia: dia siguiente > 2 Cuotas > 1 Cuota.\n"
    "    «1 Cuota» excluye titulares ya en dia siguiente o en «2 Cuotas».\n"
    "    «Dia siguiente» no se recorta por «2 Cuotas»."
)
assert old_doc in t, "docstring missing"
t = t.replace(old_doc, new_doc)

# Locate filter block by unique markers
start = t.find("    # Un mismo cliente no recibe dos avisos:")
end = t.find("    dias_1 = filtrar_items_sin_cobranzas_excel(")
assert start != -1 and end != -1 and start < end, (start, end)
new_filt = (
    "    # Jerarquia: dia siguiente (sin recorte por 2 Cuotas) > 2 Cuotas > 1 Cuota.\n"
    "    claves_dia = (\n"
    "        clientes_en_regla_dia_siguiente(db, fecha_referencia)\n"
    "        if dias_10\n"
    "        else (set(), set())\n"
    "    )\n"
    "    claves_prejudicial = (\n"
    "        clientes_en_regla_prejudicial(db, fecha_referencia)\n"
    "        if dias_10\n"
    "        else (set(), set())\n"
    "    )\n"
    "    claves_cobranzas = (\n"
    "        clientes_en_regla_cobranzas_excel(db, fecha_referencia)\n"
    "        if (dias_1 or dias_10)\n"
    "        else (set(), set())\n"
    "    )\n"
    "    claves_c4mas = (\n"
    "        clientes_en_regla_cuotas_4_mas(db, fecha_referencia)\n"
    "        if (dias_1 or dias_10)\n"
    "        else (set(), set())\n"
    "    )\n"
    "    dias_10 = filtrar_items_sin_dia_siguiente(\n"
    "        db, dias_10, fecha_referencia, claves=claves_dia, etiqueta=\"menor-60\"\n"
    "    )\n"
    "    dias_10 = filtrar_items_sin_prejudicial(\n"
    "        db, dias_10, fecha_referencia, claves=claves_prejudicial, etiqueta=\"menor-60\"\n"
    "    )\n"
)
t = t[:start] + new_filt + t[end:]
p.write_text(t, encoding="utf-8")
print("listados_motor OK")
