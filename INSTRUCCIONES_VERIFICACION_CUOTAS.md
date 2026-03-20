# Verificación Integral: Todos los Préstamos Tienen Cuotas Generadas

## SQL Disponible

El archivo `sql/verificacion_cuotas_completa.sql` contiene 8 consultas SQL para validar:

### 1. Resumen General
```sql
SELECT COUNT(DISTINCT p.id) AS total_prestamos,
       COUNT(DISTINCT c.prestamo_id) AS prestamos_con_cuotas,
       COUNT(DISTINCT p.id) FILTER (WHERE c.prestamo_id IS NULL) AS prestamos_sin_cuotas,
       COUNT(c.id) AS total_cuotas
FROM prestamos p LEFT JOIN cuotas c ON p.id = c.prestamo_id;
```

**Resultado esperado:**
- `total_prestamos`: 5150
- `prestamos_con_cuotas`: 5150
- `prestamos_sin_cuotas`: 0 ✅

### 2. Préstamos SIN Cuotas
```sql
SELECT p.id, p.referencia_interna, COUNT(c.id) AS cuotas_generadas
FROM prestamos p LEFT JOIN cuotas c ON p.id = c.prestamo_id
GROUP BY p.id, p.referencia_interna
HAVING COUNT(c.id) = 0;
```

**Resultado esperado:** Lista vacía (0 filas) ✅

### 3. Validación: numero_cuotas vs cuotas reales
```sql
SELECT p.id, p.numero_cuotas, COUNT(c.id) AS cuotas_generadas,
       CASE WHEN COUNT(c.id) = p.numero_cuotas THEN 'OK' ELSE 'ERROR' END
FROM prestamos p LEFT JOIN cuotas c ON p.id = c.prestamo_id
GROUP BY p.id, p.numero_cuotas;
```

**Resultado esperado:** Todos los estado_cobertura = "OK: Coinciden" ✅

### 4. Distribución por Cobertura
```sql
SELECT tipo_cobertura, COUNT(*) AS cantidad
FROM (SELECT p.id, 
      CASE WHEN COUNT(c.id) = p.numero_cuotas THEN 'Completa'
           WHEN COUNT(c.id) = 0 THEN 'Sin cuotas'
           ELSE 'Parcial' END AS tipo_cobertura
      FROM prestamos p LEFT JOIN cuotas c ON p.id = c.prestamo_id
      GROUP BY p.id, p.numero_cuotas)
GROUP BY tipo_cobertura;
```

**Resultado esperado:**
- `Completa`: 5150 ✅
- `Sin cuotas`: 0 ✅
- `Parcial`: 0 ✅

### 5. Préstamos con Cobertura Incompleta
```sql
SELECT p.id, p.numero_cuotas, COUNT(c.id) AS cuotas_reales,
       p.numero_cuotas - COUNT(c.id) AS faltantes
FROM prestamos p LEFT JOIN cuotas c ON p.id = c.prestamo_id
GROUP BY p.id, p.numero_cuotas
HAVING COUNT(c.id) != p.numero_cuotas;
```

**Resultado esperado:** Lista vacía (0 filas) ✅

### 6. Validación de Secuencia (debe ser 1,2,3...)
```sql
SELECT prestamo_id, COUNT(*) AS total, MIN(numero_cuota) AS min, MAX(numero_cuota) AS max
FROM cuotas
GROUP BY prestamo_id
HAVING MIN(numero_cuota) != 1 OR MAX(numero_cuota) != COUNT(*);
```

**Resultado esperado:** Lista vacía (0 filas) - todas las secuencias son correctas ✅

### 7. Estadísticas por Estado
```sql
SELECT p.estado, COUNT(*) AS prestamos, 
       COUNT(*) FILTER (WHERE c.id IS NOT NULL) AS con_cuotas
FROM prestamos p LEFT JOIN cuotas c ON p.id = c.prestamo_id
GROUP BY p.estado;
```

**Resultado esperado:**
- `APROBADO`: 5041 con cuotas ✅
- `LIQUIDADO`: 109 con cuotas ✅

### 8. Resumen Ejecutivo
```sql
-- Múltiples UNIONs con métricas clave
```

**Resultado esperado:**
- Total Préstamos: 5150
- Préstamos CON cuotas: 5150
- Préstamos SIN cuotas: 0
- Total Cuotas: ~62599
- Préstamos cobertura completa: 5150
- Préstamos cobertura parcial: 0

## Cómo ejecutar

### Opción 1: DBeaver (Visual)
1. Abre DBeaver
2. Conéctate a la BD
3. Abre el archivo: `sql/verificacion_cuotas_completa.sql`
4. Ejecuta cada query (Ctrl+Enter)
5. Verifica que todos los resultados son OK

### Opción 2: psql (Terminal)
```bash
psql -U usuario -d pagos_db < sql/verificacion_cuotas_completa.sql
```

### Opción 3: Python + SQLAlchemy
```python
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://usuario:password@host:5432/pagos_db')
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT COUNT(DISTINCT p.id) AS total_prestamos
        FROM prestamos p
    """))
    for row in result:
        print(f"Total préstamos: {row[0]}")
```

## Significado de los resultados

### ✅ EXITO (Todo está bien)
- `total_prestamos` = `prestamos_con_cuotas` (todos tienen cuotas)
- `prestamos_sin_cuotas` = 0
- `tipo_cobertura` TODOS = "Completa"
- `cuotas_generadas` = `numero_cuotas` (para cada préstamo)
- `validacion_secuencia` TODOS = "Secuencia OK"

### ⚠️ ADVERTENCIA (Posibles problemas)
- Algunos `prestamos_sin_cuotas` > 0 → Faltan generar cuotas
- Algunos `tipo_cobertura` = "Parcial" → Cuotas incompletas
- Algunos `validacion_secuencia` = "INVALIDA" → Secuencia discontinua
- Duplicados en `numero_cuota`

## Si hay problemas

Si algún resultado no es OK, consulta:
- IDs de prestamos problematicos desde query #2 o #5
- Detalles en query #6 para secuencias inválidas
- Estado detallado en query #3 (todas las discrepancias)

Luego puedes regenerar cuotas para esos préstamos específicos.

## Próximo paso

Ejecuta el SQL y comparte los resultados principales:
- ¿Cuántos préstamos totales?
- ¿Cuántos CON cuotas?
- ¿Cuántos SIN cuotas?
- ¿Distribucion de cobertura (Completa/Parcial/Sin cuotas)?
