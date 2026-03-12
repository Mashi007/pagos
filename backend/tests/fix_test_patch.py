# One-off script to fix test_envio_cobranza_respeta_incluir_pdf_anexo_false
path = r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\tests\test_config_notificaciones_envios.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the block to replace: from "    ):\n" (after get_plantilla_asunto_cuerpo) 
# then "        with patch(\n" ... "            db,\n" "        ):"
# ... "            plantilla = MagicMock()" ... "            with patch.object(db, \"get\", return_value=plantilla):\n"
# "                _enviar_correos_items("
target = '            "app.api.v1.endpoints.notificaciones_tabs.db",\n'
i = 0
while i < len(lines):
    if target in lines[i]:
        # Found. Replace from line with "        with patch(" (i-1) to line with "                _enviar_correos_items(" (exclusive of that line)
        start = i - 1  # "        with patch("
        # Find "                _enviar_correos_items("
        j = i
        while j < len(lines) and "_enviar_correos_items(" not in lines[j]:
            j += 1
        end = j  # keep _enviar_correos_items and rest

        new_block = [
            "    plantilla = MagicMock()\n",
            '    plantilla.tipo = "COBRANZA"\n',
            "    original_get = db.get\n",
            "\n",
            "    def fake_db_get(model, pk):\n",
            '        if getattr(model, "__name__", "") == "PlantillaNotificacion" and pk == 1:\n',
            "            return plantilla\n",
            "        return original_get(model, pk)\n",
            "\n",
            "        with patch.object(db, \"get\", side_effect=fake_db_get):\n",
            "            _enviar_correos_items(\n",
        ]
        lines = lines[:start] + new_block + lines[end:]
        break
    i += 1
else:
    print("Block not found")
    exit(1)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Fixed")
