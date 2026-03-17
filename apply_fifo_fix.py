#!/usr/bin/env python3
"""
Aplica la corrección FIFO en backend/app/api/v1/endpoints/pagos.py.
Cambia order_by(Cuota.numero_cuota.desc()) por order_by(Cuota.numero_cuota.asc()).
Ejecutar desde la raíz del repo: python apply_fifo_fix.py
"""
import os

FILE = os.path.join(os.path.dirname(__file__), "backend", "app", "api", "v1", "endpoints", "pagos.py")
OLD = ".order_by(Cuota.numero_cuota.desc())  # De atras hacia delante: ultima cuota no cubierta al 100% primero"
NEW = ".order_by(Cuota.numero_cuota.asc())  # FIFO: primero las cuotas más antiguas (numero_cuota menor), luego las siguientes"

def main():
    if not os.path.isfile(FILE):
        print(f"No se encuentra {FILE}")
        return 1
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()
    if OLD not in content:
        if "numero_cuota.asc()" in content:
            print("El archivo ya tiene la corrección FIFO aplicada.")
            return 0
        print("No se encontró la línea exacta a reemplazar. Revisar manualmente (ver FIX_FIFO_CUOTAS_PAGOS.md).")
        return 2
    content = content.replace(OLD, NEW)
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print("Corrección FIFO aplicada correctamente en pagos.py")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
