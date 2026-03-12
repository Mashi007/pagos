# Fix test: remove patch(notificaciones_tabs.db), use patch.object(db, "get", side_effect=fake_db_get)
path = r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\tests\test_config_notificaciones_envios.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

target = '            "app.api.v1.endpoints.notificaciones_tabs.db",\n'
i = 0
while i < len(lines):
    if target in lines[i]:
        start = i - 1
        j = i
        while j < len(lines) and "_enviar_correos_items(" not in lines[j]:
            j += 1
        end = j

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
            '        with patch.object(db, "get", side_effect=fake_db_get):\n',
        ]
        rest = lines[end:]
        if rest and "_enviar_correos_items(" in rest[0]:
            rest[0] = "            " + rest[0].lstrip()
        lines = lines[:start] + new_block + rest
        break
    i += 1
else:
    print("Block not found")
    exit(1)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Fixed")
