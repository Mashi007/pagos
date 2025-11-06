# 📋 INSTRUCCIONES PARA EJECUTAR RECONCILIACIÓN DE PAGOS

## 🚀 PASO 1: Preparar el entorno

### Opción A: Desde la raíz del proyecto (Recomendado)

```powershell
# 1. Ir a la raíz del proyecto
cd C:\Users\PORTATIL\Documents\GitHub\pagos

# 2. Activar entorno virtual (si tienes uno)
# Si usas venv:
.\venv\Scripts\Activate.ps1
# O si usas conda:
conda activate pagos

# 3. Verificar que tienes las variables de entorno configuradas
# El script necesita DATABASE_URL
# Puedes verificar con:
echo $env:DATABASE_URL

# 4. Ejecutar el script (DRY RUN - sin cambios)
# En Windows, puede ser 'python' o 'py':
python backend/scripts/reconciliar_pagos_cuotas.py
# O si 'python' no funciona:
py backend/scripts/reconciliar_pagos_cuotas.py
```

### Opción B: Desde el directorio backend

```powershell
# 1. Ir al directorio backend
cd C:\Users\PORTATIL\Documents\GitHub\pagos\backend

# 2. Activar entorno virtual (si tienes uno)
..\venv\Scripts\Activate.ps1

# 3. Ejecutar el script (DRY RUN - sin cambios)
# En Windows, puede ser 'python' o 'py':
python scripts/reconciliar_pagos_cuotas.py
# O si 'python' no funciona:
py scripts/reconciliar_pagos_cuotas.py
```

---

## 🔍 PASO 2: Ejecutar en modo DRY RUN (Recomendado primero)

**Modo DRY RUN:** Muestra lo que haría SIN hacer cambios en la base de datos.

```powershell
# Desde la raíz del proyecto:
# Opción 1: Si 'python' está en el PATH
python backend/scripts/reconciliar_pagos_cuotas.py

# Opción 2: Si 'python' no funciona, usar 'py' (launcher de Python en Windows)
py backend/scripts/reconciliar_pagos_cuotas.py

# O desde el directorio backend:
cd backend
python scripts/reconciliar_pagos_cuotas.py
# O:
py scripts/reconciliar_pagos_cuotas.py
```

**Salida esperada:**
```
🚀 Iniciando reconciliación de pagos con cuotas...
📊 Encontrados X pagos con prestamo_id y numero_cuota
✅ Estrategia 1: X pagos reconciliados
📊 Encontrados Y pagos sin prestamo_id o numero_cuota
✅ Estrategia 2: Y pagos reconciliados
📊 Verificando Z cuotas marcadas como PAGADO
✅ Cuotas corregidas: Z
🔍 DRY RUN: No se hicieron cambios. Ejecutar con dry_run=False para aplicar cambios.
================================================================================
📊 RESUMEN DE RECONCILIACIÓN
================================================================================
✅ Pagos reconciliados (Estrategia 1): X
✅ Pagos reconciliados (Estrategia 2): Y
✅ Cuotas corregidas: Z
✅ Total reconciliados: X+Y
================================================================================
```

---

## ✅ PASO 3: Aplicar cambios (Solo después de revisar DRY RUN)

**⚠️ IMPORTANTE:** Solo ejecutar después de revisar los resultados del DRY RUN.

```powershell
# Desde la raíz del proyecto:
# Opción 1: Si 'python' está en el PATH
python backend/scripts/reconciliar_pagos_cuotas.py --apply

# Opción 2: Si 'python' no funciona, usar 'py'
py backend/scripts/reconciliar_pagos_cuotas.py --apply

# O desde el directorio backend:
cd backend
python scripts/reconciliar_pagos_cuotas.py --apply
# O:
py scripts/reconciliar_pagos_cuotas.py --apply
```

**Salida esperada:**
```
🚀 Iniciando reconciliación de pagos con cuotas...
📊 Encontrados X pagos con prestamo_id y numero_cuota
✅ Estrategia 1: X pagos reconciliados
📊 Encontrados Y pagos sin prestamo_id o numero_cuota
✅ Estrategia 2: Y pagos reconciliados
📊 Verificando Z cuotas marcadas como PAGADO
✅ Cuotas corregidas: Z
✅ Cambios guardados en la base de datos
================================================================================
📊 RESUMEN DE RECONCILIACIÓN
================================================================================
✅ Pagos reconciliados (Estrategia 1): X
✅ Pagos reconciliados (Estrategia 2): Y
✅ Cuotas corregidas: Z
✅ Total reconciliados: X+Y
================================================================================
```

---

## 🔧 SOLUCIÓN DE PROBLEMAS

### Error: "ModuleNotFoundError: No module named 'app'"

**Causa:** El script no encuentra los módulos de la aplicación.

**Solución:**
```powershell
# Asegúrate de estar en la raíz del proyecto o tener PYTHONPATH configurado
cd C:\Users\PORTATIL\Documents\GitHub\pagos

# O configura PYTHONPATH:
$env:PYTHONPATH = "C:\Users\PORTATIL\Documents\GitHub\pagos\backend"
python backend/scripts/reconciliar_pagos_cuotas.py
```

### Error: "DATABASE_URL not found"

**Causa:** La variable de entorno `DATABASE_URL` no está configurada.

**Solución:**
```powershell
# Opción 1: Configurar temporalmente en PowerShell
$env:DATABASE_URL = "postgresql://usuario:password@host:puerto/database"

# Opción 2: Crear archivo .env en la raíz del proyecto
# DATABASE_URL=postgresql://usuario:password@host:puerto/database

# Opción 3: Usar el valor de Render (si estás en producción)
# Copia el DATABASE_URL de Render Dashboard
```

### Error: "Connection refused" o "Could not connect"

**Causa:** No puedes conectarte a la base de datos.

**Solución:**
1. Verifica que la base de datos esté corriendo
2. Verifica que `DATABASE_URL` sea correcta
3. Verifica que tengas acceso de red a la base de datos
4. Si es una base de datos remota, verifica firewall/VPN

### Error: "Permission denied" o "Access denied"

**Causa:** No tienes permisos para modificar la base de datos.

**Solución:**
1. Verifica que el usuario de la base de datos tenga permisos de escritura
2. Verifica que puedas hacer UPDATE/INSERT en las tablas `cuotas` y `pagos`

---

## 📊 VERIFICAR RESULTADOS

Después de ejecutar el script, verifica en SQL:

```sql
-- Verificar pagos vinculados después de reconciliación
SELECT 
    COUNT(*) as total_cuotas,
    COUNT(CASE WHEN total_pagado > 0 THEN 1 END) as cuotas_con_pagos,
    SUM(total_pagado) as monto_total_pagado
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO';

-- Verificar morosidad mensual con pagos
SELECT 
    TO_CHAR(DATE_TRUNC('month', c.fecha_vencimiento), 'YYYY-MM') as mes,
    SUM(c.monto_cuota) as monto_programado,
    SUM(COALESCE(c.total_pagado, 0)) as monto_pagado,
    SUM(c.monto_cuota) - SUM(COALESCE(c.total_pagado, 0)) as morosidad
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.fecha_vencimiento >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '12 months')
GROUP BY DATE_TRUNC('month', c.fecha_vencimiento)
ORDER BY mes DESC;
```

---

## ⚠️ IMPORTANTE

1. **Siempre ejecuta DRY RUN primero** para ver qué cambios se harían
2. **Haz backup de la base de datos** antes de ejecutar con `--apply`
3. **Revisa los resultados** del DRY RUN antes de aplicar cambios
4. **Verifica en el dashboard** después de aplicar cambios

---

## 📝 COMANDOS RÁPIDOS

```powershell
# DRY RUN (ver qué haría)
# Si 'python' está en el PATH:
python backend/scripts/reconciliar_pagos_cuotas.py
# O si no, usar 'py':
py backend/scripts/reconciliar_pagos_cuotas.py

# Aplicar cambios
python backend/scripts/reconciliar_pagos_cuotas.py --apply
# O:
py backend/scripts/reconciliar_pagos_cuotas.py --apply

# Ver ayuda
python backend/scripts/reconciliar_pagos_cuotas.py --help
# O:
py backend/scripts/reconciliar_pagos_cuotas.py --help
```

## 🔍 VERIFICAR PYTHON

Si no sabes qué comando usar, prueba:

```powershell
# Verificar si 'python' funciona:
python --version

# Si no funciona, probar 'py':
py --version

# Ver todas las versiones de Python instaladas:
py -0
```

