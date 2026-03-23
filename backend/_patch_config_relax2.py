# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent / "app" / "core" / "config.py"
t = p.read_text(encoding="utf-8")
if "NOTIFICACIONES_PAQUETE_RELAX_SOLO_PRUEBA_DESTINO" in t:
    print("config already has relax")
else:
    needle = '        description="Exige plantilla + PDF variable (carta) + PDF fijo antes de enviar notificaciones por pesta'
    i = t.find(needle)
    if i < 0:
        raise SystemExit("description line not found")
    # find closing of Field after NOTIFICACIONES_PAQUETE_ESTRICTO
    j = t.find("NOTIFICACIONES_PAQUETE_ESTRICTO", i - 200)
    if j < 0:
        raise SystemExit("NOTIFICACIONES block not found")
    k = t.find("    )", t.find("NOTIFICACIONES_PAQUETE_ESTRICTO", j))
    # find first `    )` after NOTIFICACIONES_PAQUETE_ESTRICTO Field
    start = t.find("NOTIFICACIONES_PAQUETE_ESTRICTO")
    end = t.find("\n    )\n", start)
    if end < 0:
        raise SystemExit("end paren not found")
    end = end + len("\n    )\n")
    block = t[start:end]
    insert = block + (
        "    # Si True: solo con destinos forzados (prueba de paquete) permite enviar aunque falte PDF fijo.\n"
        "    NOTIFICACIONES_PAQUETE_RELAX_SOLO_PRUEBA_DESTINO: bool = Field(\n"
        "        default=False,\n"
        "        description=(\n"
        "            'Relaja validacion de paquete solo para POST /enviar-prueba-paquete (destinos forzados). '\n"
        "            'Los envios masivos reales siguen sujetos a NOTIFICACIONES_PAQUETE_ESTRICTO.'\n"
        "        ),\n"
        "    )\n"
    )
    t = t.replace(block, insert, 1)
    p.write_text(t, encoding="utf-8")
    print("ok config2")
