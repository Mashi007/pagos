#!/usr/bin/env python3
"""
Ejecuta la verificacion en cascada solo despues de escribir fin.
Uso: python sql/run_verificar_cascada.py
"""
import os
import sys

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


def main() -> None:
    palabra = ""
    while palabra != "fin":
        palabra = input("Escriba fin para ejecutar la verificacion en cascada: ").strip().lower()
    print("Ejecutando verificacion en cascada...")
    from verificar_cascada import verificar_cascada
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        out = verificar_cascada(db)
        print("Resultado cascada:", out["resultado_cascada"])
        print("Total violaciones:", out["total_violaciones"])
        print("Prestamos afectados:", out["total_prestamos_afectados"])
        if out["violaciones"]:
            print("\nDetalle:")
            for v in out["violaciones"]:
                print(
                    f"  Prestamo {v['prestamo_id']}: cuota {v['numero_cuota_anterior']} "
                    f"(id={v['cuota_anterior_id']}) no completada vs cuota {v['numero_cuota_posterior']} "
                    f"(id={v['cuota_posterior_id']}) con pago."
                )
        ok = out["resultado_cascada"] == "CUMPLE_CASCADA"
        sys.exit(0 if ok else 1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
