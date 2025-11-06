# 📋 INSTRUCCIONES: Generar Cuotas Faltantes

## Problema Identificado

### 1. Préstamo Crítico
- **ID:** 3708
- **Problema:** Sin cuotas (0 de 12 esperadas)
- **Impacto:** ❌ No se pueden registrar pagos, no aparece en dashboard

### 2. Préstamos con Cuotas Incompletas
- **Cantidad:** ~200+ préstamos
- **Problema:** Tienen menos cuotas de las esperadas
- **Impacto:** ⚠️ Cálculos de morosidad y proyecciones incorrectas

---

## Solución: Script Python

**Archivo:** `backend/scripts/generar_cuotas_faltantes.py`

### Funcionalidades

1. **Generar cuotas para préstamos sin cuotas** (crítico)
2. **Completar cuotas faltantes** para préstamos con cuotas incompletas
3. **Regenerar todas las cuotas** (opción para mantener consistencia)

---

## Uso del Script

### Opción 1: Procesar Préstamo Específico (Recomendado para Pruebas)

```bash
# Desde el directorio raíz del proyecto
cd backend

# Generar cuotas para préstamo crítico (ID 3708)
py scripts/generar_cuotas_faltantes.py --prestamo-id 3708

# Regenerar TODAS las cuotas de un préstamo (útil si tiene cuotas incompletas)
py scripts/generar_cuotas_faltantes.py --prestamo-id 3708 --regenerar
```

### Opción 2: Simular Sin Hacer Cambios (DRY RUN)

```bash
# Ver qué haría el script sin hacer cambios
py scripts/generar_cuotas_faltantes.py --prestamo-id 3708 --dry-run

# Ver qué haría para todos los préstamos problemáticos
py scripts/generar_cuotas_faltantes.py --dry-run
```

### Opción 3: Procesar Todos los Préstamos Problemáticos

```bash
# ⚠️ ADVERTENCIA: Esto procesará ~200+ préstamos
# Se recomienda hacer primero un DRY RUN

# 1. Primero simular
py scripts/generar_cuotas_faltantes.py --dry-run

# 2. Si todo se ve bien, ejecutar
py scripts/generar_cuotas_faltantes.py --regenerar
```

---

## Parámetros del Script

| Parámetro | Descripción | Ejemplo |
|-----------|-------------|---------|
| `--prestamo-id` | ID del préstamo específico a procesar | `--prestamo-id 3708` |
| `--dry-run` | Simular sin hacer cambios en BD | `--dry-run` |
| `--regenerar` | Regenerar TODAS las cuotas (elimina existentes) | `--regenerar` |

---

## Ejemplos de Uso

### Ejemplo 1: Generar Cuotas para Préstamo Crítico

```bash
# Paso 1: Verificar qué haría
py scripts/generar_cuotas_faltantes.py --prestamo-id 3708 --dry-run

# Paso 2: Generar cuotas
py scripts/generar_cuotas_faltantes.py --prestamo-id 3708
```

**Salida esperada:**
```
✅ Préstamo 3708: 12 cuotas generadas (faltantes: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
```

### Ejemplo 2: Regenerar Cuotas de Préstamo con Cuotas Incompletas

```bash
# Regenerar todas las cuotas (útil si tiene cuotas incompletas)
py scripts/generar_cuotas_faltantes.py --prestamo-id 1624 --regenerar
```

**Salida esperada:**
```
✅ Préstamo 1624: 12 cuotas regeneradas (tenía 9, ahora tiene 12)
```

### Ejemplo 3: Procesar Todos los Préstamos Problemáticos

```bash
# Paso 1: Ver qué haría
py scripts/generar_cuotas_faltantes.py --dry-run

# Paso 2: Procesar todos (regenerar cuotas incompletas)
py scripts/generar_cuotas_faltantes.py --regenerar
```

**Salida esperada:**
```
Identificando préstamos con problemas...
Préstamos sin cuotas: 1
Préstamos con cuotas incompletas: 200+
Procesando préstamo 3708 (sin cuotas)...
✅ Préstamo 3708: 12 cuotas generadas
Procesando préstamo 1624 (cuotas incompletas)...
✅ Préstamo 1624: 12 cuotas regeneradas
...
======================================================================
RESUMEN:
  Total procesados: 201
  Exitosos: 201
  Fallidos: 0
  Total cuotas generadas: 2,412
======================================================================
```

---

## ⚠️ ADVERTENCIAS IMPORTANTES

### 1. Préstamos con Cuotas Incompletas

**Problema:** Si un préstamo tiene cuotas existentes pero incompletas, el script **regenerará TODAS las cuotas** para mantener consistencia en los cálculos de saldo de capital.

**Impacto:**
- ✅ Las cuotas existentes se eliminarán y se recrearán
- ✅ Los pagos registrados en cuotas existentes **NO se perderán** (están en tabla `pagos`)
- ⚠️ Los campos `total_pagado`, `capital_pagado`, etc. en las cuotas se resetearán a 0
- ⚠️ Necesitarás **reconciliar los pagos** después de regenerar cuotas

**Recomendación:**
- Si el préstamo tiene pagos registrados, considera reconciliar los pagos después de regenerar cuotas
- O espera a que se implemente una función que preserve los pagos al regenerar

### 2. Backup de Base de Datos

**Recomendación:** Hacer backup antes de ejecutar masivamente:

```bash
# Ejemplo de backup (ajustar según tu configuración)
pg_dump -h localhost -U usuario -d nombre_bd > backup_antes_cuotas.sql
```

### 3. Validación Post-Ejecución

Después de ejecutar, verificar:

```sql
-- Verificar que el préstamo crítico ahora tiene cuotas
SELECT 
    p.id,
    p.cedula,
    p.numero_cuotas as esperadas,
    COUNT(c.id) as generadas
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
WHERE p.id = 3708
GROUP BY p.id, p.cedula, p.numero_cuotas;

-- Verificar préstamos con cuotas incompletas
SELECT 
    p.id,
    p.cedula,
    p.numero_cuotas as esperadas,
    COUNT(c.id) as generadas,
    (p.numero_cuotas - COUNT(c.id)) as faltantes
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND p.fecha_base_calculo IS NOT NULL
GROUP BY p.id, p.cedula, p.numero_cuotas
HAVING COUNT(c.id) < p.numero_cuotas
ORDER BY faltantes DESC;
```

---

## Solución Alternativa: Usar Endpoint del Backend

Si prefieres usar el endpoint del backend:

```bash
# Generar cuotas para préstamo específico
curl -X POST "http://localhost:8000/api/v1/prestamos/3708/generar-amortizacion" \
  -H "Authorization: Bearer TU_TOKEN"
```

**Ventajas:**
- ✅ Usa la misma lógica que el sistema
- ✅ Validaciones integradas
- ✅ Logs en el sistema

**Desventajas:**
- ❌ Solo procesa un préstamo a la vez
- ❌ Requiere autenticación

---

## Próximos Pasos Después de Generar Cuotas

1. ✅ **Verificar en DBeaver** que las cuotas se generaron correctamente
2. ✅ **Validar dashboard** que ahora muestra datos correctos
3. ✅ **Reconciliar pagos** si es necesario (para préstamos con cuotas regeneradas)
4. ✅ **Implementar validación preventiva** en el código del backend

---

## Troubleshooting

### Error: "Préstamo no encontrado"
- Verificar que el ID del préstamo existe
- Verificar que estás conectado a la base de datos correcta

### Error: "Préstamo no está APROBADO"
- El préstamo debe estar en estado APROBADO
- Verificar estado: `SELECT id, estado FROM prestamos WHERE id = 3708;`

### Error: "Préstamo no tiene fecha_base_calculo"
- El préstamo debe tener `fecha_base_calculo` establecida
- Verificar: `SELECT id, fecha_base_calculo FROM prestamos WHERE id = 3708;`

### Error de Conexión a Base de Datos
- Verificar variables de entorno: `DATABASE_URL`
- Verificar que la base de datos esté accesible

---

**Estado:** ✅ **SCRIPT LISTO PARA USO**

