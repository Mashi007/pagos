#!/usr/bin/env python3
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
_REPO = os.path.dirname(BACKEND)
env_path = os.path.join(_REPO, ".env")
if os.path.isfile(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from sqlalchemy import text
from app.core.database import SessionLocal

db = SessionLocal()
try:
    rows = db.execute(
        text(
            """
            SELECT estado, COUNT(*) n,
                   COUNT(*) FILTER (WHERE comprobante_imagen_id IS NOT NULL) con_img
            FROM infopagos_escaner_borrador
            GROUP BY estado ORDER BY estado
            """
        )
    ).fetchall()
    print("BORRADORES POR ESTADO:", rows)
    orphan = db.execute(
        text(
            """
            SELECT COUNT(*) FROM infopagos_escaner_borrador b
            LEFT JOIN pago_comprobante_imagen i ON i.id = b.comprobante_imagen_id
            WHERE b.estado = 'borrador' AND (i.id IS NULL OR i.imagen_data IS NULL)
            """
        )
    ).scalar()
    print("Borradores activos sin binario:", orphan)
    recent = db.execute(
        text(
            """
            SELECT b.id, b.estado, b.cedula_normalizada, b.created_at,
                   b.comprobante_nombre, LENGTH(i.imagen_data) bytes, b.pago_reportado_id
            FROM infopagos_escaner_borrador b
            JOIN pago_comprobante_imagen i ON i.id = b.comprobante_imagen_id
            ORDER BY b.created_at DESC LIMIT 8
            """
        )
    ).fetchall()
    print("\nULTIMOS BORRADORES:")
    for r in recent:
        print(r)
    infopagos30 = db.execute(
        text(
            """
            SELECT COUNT(*) FROM pagos_reportados
            WHERE canal_ingreso = 'infopagos'
              AND created_at > NOW() - INTERVAL '30 days'
            """
        )
    ).scalar()
    print("\nReportes infopagos ultimos 30d:", infopagos30)
    confirm_sin_img = db.execute(
        text(
            """
            SELECT COUNT(*) FROM pagos_reportados pr
            LEFT JOIN pago_comprobante_imagen i ON i.id = pr.comprobante_imagen_id
            WHERE pr.canal_ingreso = 'infopagos'
              AND pr.created_at > NOW() - INTERVAL '30 days'
              AND (pr.comprobante_imagen_id IS NULL OR i.imagen_data IS NULL)
            """
        )
    ).scalar()
    print("Reportes infopagos 30d sin imagen:", confirm_sin_img)
finally:
    db.close()
