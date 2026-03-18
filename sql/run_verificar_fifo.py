#!/usr/bin/env python3
"""
Ejecuta la verificación FIFO solo después de escribir "fin".
Uso: python sql/run_verificar_fifo.py
"""
import os
import sys

# Cargar .env si existe (backend)
backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(backend_dir))
env_path = os.path.join(backend_dir, ".env")
if os.path.isfile(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

def main():
    palabra = ""
    while palabra != "fin":
        palabra = input("Escriba 'fin' para ejecutar la verificación FIFO: ").strip().lower()
    print("Ejecutando verificación FIFO...")
    # Ejecutar el módulo de verificación
    from verificar_fifo import verificar_fifo
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        out = verificar_fifo(db)
        print("Resultado FIFO:", out["resultado_fifo"])
        print("Total violaciones:", out["total_violaciones"])
        print("Préstamos afectados:", out["total_prestamos_afectados"])
        if out["violaciones"]:
            print("\nDetalle:")
            for v in out["violaciones"]:
                print(
                    f"  Préstamo {v['prestamo_id']}: cuota {v['numero_cuota_anterior']} "
                    f"(id={v['cuota_anterior_id']}) no completada vs cuota {v['numero_cuota_posterior']} "
                    f"(id={v['cuota_posterior_id']}) con pago."
                )
        sys.exit(0 if out["resultado_fifo"] == "CUMPLE_FIFO" else 1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
