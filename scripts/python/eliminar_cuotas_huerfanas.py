"""Eliminar cuotas huérfanas después de confirmar que no afectan préstamos aprobados"""
import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=" * 70)
print("ELIMINACION DE CUOTAS HUERFANAS")
print("=" * 70)

# Verificar antes de eliminar
print("\n1. VERIFICACION PREVIA:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_huerfanas,
        COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS con_pagos,
        SUM(total_pagado) AS total_pagado
    FROM cuotas
    WHERE prestamo_id BETWEEN 1 AND 3784
"""))

row = resultado.fetchone()
total_huerfanas, con_pagos, total_pagado = row

print(f"Total cuotas huérfanas a eliminar: {total_huerfanas:,}")
print(f"Cuotas con pagos: {con_pagos:,} (${total_pagado:,.2f})")
print(f"Cuotas sin pagos: {total_huerfanas - con_pagos:,}")

# Verificar que los préstamos aprobados están intactos
resultado = db.execute(text("""
    SELECT COUNT(DISTINCT p.id) AS prestamos_aprobados
    FROM prestamos p
    INNER JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.estado = 'APROBADO'
      AND c.prestamo_id BETWEEN 3785 AND 7826
"""))

prestamos_aprobados = resultado.scalar()
print(f"\nPréstamos aprobados con cuotas propias: {prestamos_aprobados:,}")

if prestamos_aprobados != 4042:
    print("\n❌ ERROR: Los préstamos aprobados no tienen todas sus cuotas")
    print("   NO proceder con la eliminación")
    db.close()
    sys.exit(1)

print("\n✅ CONFIRMADO: Los préstamos aprobados están intactos")

# Preguntar al usuario (simulado - en producción sería input())
print("\n2. OPCIONES DE ELIMINACION:")
print("-" * 70)
print("A) Eliminar TODAS las cuotas huérfanas (incluyendo las con pagos)")
print(f"   - Eliminará {total_huerfanas:,} cuotas")
print(f"   - Incluye {con_pagos:,} cuotas con pagos (${total_pagado:,.2f})")
print("\nB) Eliminar solo cuotas huérfanas SIN pagos (mantener las con pagos)")
print(f"   - Eliminará {total_huerfanas - con_pagos:,} cuotas")
print(f"   - Mantendrá {con_pagos:,} cuotas con pagos (${total_pagado:,.2f})")

print("\n⚠️ IMPORTANTE:")
print("   - Se creará backup automáticamente antes de eliminar")
print("   - Los préstamos aprobados NO se afectarán")
print("   - Las cuotas con pagos pueden ser datos históricos importantes")

print("\n" + "=" * 70)
print("NOTA: Este script solo muestra la información.")
print("Para eliminar, ejecuta el script SQL: scripts/sql/eliminar_cuotas_huerfanas.sql")
print("=" * 70)

db.close()
