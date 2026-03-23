# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent / "app" / "core" / "config.py"
t = p.read_text(encoding="utf-8")
needle = """    NOTIFICACIONES_PAQUETE_ESTRICTO: bool = Field(
        default=True,
        description="Exige plantilla + PDF variable (carta) + PDF fijo antes de enviar notificaciones por pestana",
    )
"""
insert = """    NOTIFICACIONES_PAQUETE_ESTRICTO: bool = Field(
        default=True,
        description="Exige plantilla + PDF variable (carta) + PDF fijo antes de enviar notificaciones por pestana",
    )
    # Si True: solo cuando forzar_destinos_prueba (prueba de paquete a emails de prueba) permite enviar aunque falte PDF fijo.
    # Produccion masiva sigue exigiendo paquete completo si NOTIFICACIONES_PAQUETE_ESTRICTO=True.
    NOTIFICACIONES_PAQUETE_RELAX_SOLO_PRUEBA_DESTINO: bool = Field(
        default=False,
        description="Relaja validacion de paquete solo para POST enviar-prueba-paquete (destinos forzados). Default False.",
    )
"""
if needle not in t:
    raise SystemExit("config needle not found")
if "NOTIFICACIONES_PAQUETE_RELAX_SOLO_PRUEBA_DESTINO" in t:
    print("already patched")
else:
    t = t.replace(needle, insert, 1)
    p.write_text(t, encoding="utf-8")
    print("ok config")
