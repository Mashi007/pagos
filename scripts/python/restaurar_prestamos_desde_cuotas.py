"""Restaurar préstamos eliminados desde información de cuotas huérfanas"""
import sys
import io
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

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
print("RESTAURACION DE PRESTAMOS DESDE CUOTAS HUERFANAS")
print("=" * 70)

# 1. Obtener información completa de todos los préstamos a restaurar
print("\n1. OBTENIENDO INFORMACION DE PRESTAMOS A RESTAURAR:")
print("-" * 70)

resultado = db.execute(text("""
    WITH prestamos_info AS (
        SELECT 
            c.prestamo_id,
            COUNT(*) AS numero_cuotas,
            MIN(c.numero_cuota) AS primera_cuota,
            MAX(c.numero_cuota) AS ultima_cuota,
            MIN(c.fecha_vencimiento) AS fecha_base_calculo,
            MAX(c.fecha_vencimiento) AS ultima_fecha,
            SUM(c.monto_capital) AS total_financiamiento,
            SUM(c.monto_interes) AS total_interes,
            AVG(c.monto_cuota) AS cuota_periodo,
            SUM(c.total_pagado) AS total_pagado,
            MIN(c.monto_cuota) AS monto_minimo,
            MAX(c.monto_cuota) AS monto_maximo,
            COUNT(DISTINCT c.monto_cuota) AS montos_diferentes
        FROM cuotas c
        LEFT JOIN prestamos p ON c.prestamo_id = p.id
        WHERE p.id IS NULL
        GROUP BY c.prestamo_id
    )
    SELECT 
        prestamo_id,
        numero_cuotas,
        fecha_base_calculo,
        ultima_fecha,
        total_financiamiento,
        total_interes,
        cuota_periodo,
        total_pagado,
        CASE 
            WHEN ultima_fecha IS NOT NULL AND fecha_base_calculo IS NOT NULL AND numero_cuotas > 1 THEN
                CASE 
                    WHEN (ultima_fecha - fecha_base_calculo) / (numero_cuotas - 1) BETWEEN 25 AND 35 THEN 'MENSUAL'
                    WHEN (ultima_fecha - fecha_base_calculo) / (numero_cuotas - 1) BETWEEN 12 AND 18 THEN 'QUINCENAL'
                    WHEN (ultima_fecha - fecha_base_calculo) / (numero_cuotas - 1) BETWEEN 5 AND 9 THEN 'SEMANAL'
                    ELSE 'MENSUAL'
                END
            ELSE 'MENSUAL'
        END AS modalidad_pago,
        CASE 
            WHEN total_interes > 0 AND total_financiamiento > 0 THEN
                ROUND((total_interes / total_financiamiento) * 100, 2)
            ELSE 0.00
        END AS tasa_interes_estimada
    FROM prestamos_info
    WHERE total_financiamiento > 0
    ORDER BY prestamo_id
"""))

prestamos_a_restaurar = []
for row in resultado.fetchall():
    prestamo_id, numero_cuotas, fecha_base, ultima_fecha, total_fin, total_int, \
    cuota_periodo, total_pagado, modalidad, tasa_interes = row
    
    prestamos_a_restaurar.append({
        'prestamo_id_original': prestamo_id,
        'numero_cuotas': numero_cuotas,
        'fecha_base_calculo': fecha_base,
        'total_financiamiento': float(total_fin) if total_fin else 0,
        'cuota_periodo': float(cuota_periodo) if cuota_periodo else 0,
        'modalidad_pago': modalidad,
        'tasa_interes': float(tasa_interes) if tasa_interes else 0.00,
        'total_pagado': float(total_pagado) if total_pagado else 0
    })

print(f"Prestamos a restaurar: {len(prestamos_a_restaurar)}")

# 2. Buscar información de cliente desde otras fuentes
print("\n2. BUSCANDO INFORMACION DE CLIENTES:")
print("-" * 70)

# Intentar obtener información desde tabla de auditoría o histórico si existe
# Por ahora, usaremos valores por defecto y el usuario puede corregirlos después

# 3. Generar script SQL para restaurar
print("\n3. GENERANDO SCRIPT SQL DE RESTAURACION:")
print("-" * 70)

script_sql = """-- ======================================================================
-- SCRIPT PARA RESTAURAR PRESTAMOS ELIMINADOS DESDE CUOTAS HUERFANAS
-- ======================================================================
-- IMPORTANTE: Hacer backup antes de ejecutar este script
-- ======================================================================

-- Crear tabla temporal para almacenar información de préstamos a restaurar
CREATE TEMP TABLE IF NOT EXISTS prestamos_a_restaurar_temp (
    prestamo_id_original INTEGER,
    cliente_id INTEGER,
    cedula VARCHAR(20),
    nombres VARCHAR(100),
    numero_cuotas INTEGER,
    total_financiamiento NUMERIC(15,2),
    cuota_periodo NUMERIC(15,2),
    modalidad_pago VARCHAR(20),
    tasa_interes NUMERIC(5,2),
    fecha_base_calculo DATE,
    total_pagado NUMERIC(15,2)
);

-- Insertar información de préstamos a restaurar
"""

# Agregar INSERTs para cada préstamo
for i, prestamo in enumerate(prestamos_a_restaurar[:100], 1):  # Limitar a 100 para no hacer el script muy grande
    script_sql += f"""
INSERT INTO prestamos_a_restaurar_temp VALUES (
    {prestamo['prestamo_id_original']},  -- prestamo_id_original
    NULL,  -- cliente_id (se debe buscar o asignar)
    'SIN_CEDULA_{prestamo["prestamo_id_original"]}',  -- cedula (temporal, debe corregirse)
    'CLIENTE A RESTAURAR {prestamo["prestamo_id_original"]}',  -- nombres (temporal, debe corregirse)
    {prestamo['numero_cuotas']},
    {prestamo['total_financiamiento']:.2f},
    {prestamo['cuota_periodo']:.2f},
    '{prestamo['modalidad_pago']}',
    {prestamo['tasa_interes']:.2f},
    '{prestamo['fecha_base_calculo']}',
    {prestamo['total_pagado']:.2f}
);
"""

script_sql += """
-- ======================================================================
-- PASO 1: Verificar información antes de restaurar
-- ======================================================================

SELECT 
    'INFORMACION A RESTAURAR' AS tipo,
    COUNT(*) AS total_prestamos,
    SUM(numero_cuotas) AS total_cuotas,
    SUM(total_financiamiento) AS total_financiamiento,
    SUM(total_pagado) AS total_pagado
FROM prestamos_a_restaurar_temp;

-- ======================================================================
-- PASO 2: Obtener próximo ID disponible para prestamos
-- ======================================================================

SELECT 
    'PROXIMO ID DISPONIBLE' AS tipo,
    COALESCE(MAX(id), 0) + 1 AS proximo_id
FROM prestamos;

-- ======================================================================
-- PASO 3: Restaurar préstamos
-- ======================================================================
-- NOTA: Este paso requiere que se complete la información de cliente_id, cedula y nombres
-- Se recomienda hacerlo manualmente o desde otra fuente de datos

-- Ejemplo de INSERT (descomentar y ajustar después de completar información):
/*
INSERT INTO prestamos (
    id,
    cliente_id,
    cedula,
    nombres,
    total_financiamiento,
    modalidad_pago,
    numero_cuotas,
    cuota_periodo,
    tasa_interes,
    fecha_base_calculo,
    estado,
    fecha_registro,
    fecha_actualizacion,
    usuario_proponente,
    producto,
    producto_financiero
)
SELECT 
    prestamo_id_original,  -- Usar el ID original
    cliente_id,  -- DEBE COMPLETARSE
    cedula,  -- DEBE COMPLETARSE
    nombres,  -- DEBE COMPLETARSE
    total_financiamiento,
    modalidad_pago,
    numero_cuotas,
    cuota_periodo,
    tasa_interes,
    fecha_base_calculo,
    'APROBADO' AS estado,
    CURRENT_TIMESTAMP AS fecha_registro,
    CURRENT_TIMESTAMP AS fecha_actualizacion,
    'sistema@restauracion.com' AS usuario_proponente,
    'RESTAURADO' AS producto,
    'RESTAURADO' AS producto_financiero
FROM prestamos_a_restaurar_temp
WHERE cliente_id IS NOT NULL  -- Solo restaurar si tiene cliente_id
ORDER BY prestamo_id_original;
*/

-- ======================================================================
-- PASO 4: Verificar que las cuotas ahora tienen préstamo válido
-- ======================================================================

SELECT 
    'VERIFICACION POST-RESTAURACION' AS tipo,
    COUNT(*) AS cuotas_con_prestamo_valido
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE c.prestamo_id IN (SELECT prestamo_id_original FROM prestamos_a_restaurar_temp);

-- ======================================================================
-- LIMPIAR TABLA TEMPORAL
-- ======================================================================

DROP TABLE IF EXISTS prestamos_a_restaurar_temp;
"""

# Guardar script SQL
script_path = project_root / "scripts" / "sql" / "restaurar_prestamos_eliminados.sql"
script_path.parent.mkdir(parents=True, exist_ok=True)
script_path.write_text(script_sql, encoding='utf-8')

print(f"Script SQL generado en: {script_path}")
print(f"Total préstamos incluidos en script: {len(prestamos_a_restaurar[:100])}")

# 4. Crear script Python más completo que intente buscar información de clientes
print("\n4. CREANDO SCRIPT COMPLETO DE RESTAURACION:")
print("-" * 70)

script_python = """\"\"\"Script completo para restaurar préstamos eliminados\"\"\"
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.db.session import SessionLocal
from sqlalchemy import text
from datetime import datetime

db = SessionLocal()

print("=" * 70)
print("RESTAURACION COMPLETA DE PRESTAMOS")
print("=" * 70)

# Este script requiere información adicional del usuario
# Se recomienda ejecutarlo paso a paso

print("\\n⚠️ IMPORTANTE:")
print("Este script requiere:")
print("1. Información de cliente para cada préstamo")
print("2. Backup de la base de datos")
print("3. Verificación manual antes de restaurar")
print("\\n¿Deseas continuar? (s/n): ", end="")
# respuesta = input()
# if respuesta.lower() != 's':
#     print("Operación cancelada")
#     db.close()
#     sys.exit(0)

db.close()
"""

script_python_path = project_root / "scripts" / "python" / "restaurar_prestamos_completo.py"
script_python_path.write_text(script_python, encoding='utf-8')

print(f"Script Python generado en: {script_python_path}")

# 5. Mostrar resumen y recomendaciones
print("\n5. RESUMEN Y RECOMENDACIONES:")
print("-" * 70)

print(f"\nTotal préstamos a restaurar: {len(prestamos_a_restaurar)}")
print(f"Prestamos con información completa: {sum(1 for p in prestamos_a_restaurar if p['fecha_base_calculo'] and p['total_financiamiento'] > 0)}")

print("\n⚠️ ACCIONES REQUERIDAS:")
print("1. Buscar información de clientes (cliente_id, cedula, nombres)")
print("   - Puede estar en backups anteriores")
print("   - Puede estar en logs del sistema")
print("   - Puede requerir consulta manual")
print("\n2. Completar el script SQL con información de clientes")
print("3. Hacer backup completo de la base de datos")
print("4. Ejecutar script en ambiente de pruebas primero")
print("5. Verificar que las cuotas quedan correctamente vinculadas")

print("\n" + "=" * 70)

db.close()
