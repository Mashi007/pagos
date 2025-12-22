# 📋 INSTRUCCIONES PASOS DETALLADOS PARA DIAGNÓSTICO Y RECONCILIACIÓN

## 🎯 OBJETIVO
Diagnosticar y resolver el problema de pagos sin `prestamo_id` que impide la vinculación correcta entre pagos y cuotas.

---

## 📊 PASO 1: DIAGNÓSTICO INICIAL (SQL en DBeaver)

### 1.1. Ejecutar queries de diagnóstico

**Archivo:** `scripts/sql/PASOS_DIAGNOSTICO_Y_RECONCILIACION.sql`

**Queries a ejecutar:**
- **PASO 1.1:** Verificar pagos conciliados sin prestamo_id
- **PASO 1.2:** Verificar cuotas con pagos pero sin prestamo_id en pagos
- **PASO 1.3:** Ver ejemplos de pagos sin prestamo_id con préstamos coincidentes

**Resultado esperado:**
- Identificar cuántos pagos conciliados podrían vincularse por `cedula`
- Ver ejemplos concretos de pagos que necesitan `prestamo_id`

---

## 🔍 PASO 2: ANÁLISIS DETALLADO (SQL en DBeaver)

### 2.1. Ejecutar queries de análisis

**Queries a ejecutar:**
- **PASO 2.1:** Pagos con UN SOLO préstamo coincidente (fácil de asignar)
- **PASO 2.2:** Pagos con MÚLTIPLES préstamos coincidentes (requiere lógica adicional)
- **PASO 2.3:** Pagos SIN préstamos coincidentes (requiere investigación manual)

**Resultado esperado:**
- Clasificar los pagos según la complejidad de asignación
- Identificar cuántos pagos se pueden asignar automáticamente

---

## ⚙️ PASO 3: RECONCILIACIÓN AUTOMÁTICA (Python)

### 3.1. Preparar el entorno

```powershell
# 1. Ir a la raíz del proyecto
cd C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos

# 2. Activar entorno virtual (si tienes uno)
# Si usas venv:
.\venv\Scripts\Activate.ps1
# O si usas conda:
conda activate pagos

# 3. Verificar variables de entorno
echo $env:DATABASE_URL
```

### 3.2. Ejecutar en modo DRY RUN (sin cambios)

```powershell
# Ver qué haría el script sin hacer cambios
python backend/scripts/reconciliar_pagos_cuotas.py

# O si 'python' no funciona:
py backend/scripts/reconciliar_pagos_cuotas.py
```

**Revisar la salida:**
- ✅ Pagos reconciliados (Estrategia 1): X
- ✅ Pagos reconciliados (Estrategia 2): Y
- ✅ Cuotas corregidas: Z
- ✅ Total reconciliados: X+Y

**⚠️ IMPORTANTE:** Revisar cuidadosamente los números antes de aplicar cambios.

### 3.3. Aplicar cambios (solo después de revisar DRY RUN)

```powershell
# Aplicar cambios en la base de datos
python backend/scripts/reconciliar_pagos_cuotas.py --apply

# O si 'python' no funciona:
py backend/scripts/reconciliar_pagos_cuotas.py --apply
```

**⚠️ ADVERTENCIA:** 
- Hacer backup de la base de datos antes de ejecutar con `--apply`
- Solo ejecutar si los resultados del DRY RUN son correctos

---

## ✅ PASO 4: VERIFICACIÓN POST-RECONCILIACIÓN (SQL en DBeaver)

### 4.1. Ejecutar queries de verificación

**Queries a ejecutar:**
- **PASO 3.1:** Verificar cuántos pagos tienen prestamo_id después de reconciliación
- **PASO 3.2:** Verificar vinculación entre pagos y cuotas después de reconciliación

**Resultado esperado:**
- Ver incremento en pagos con `prestamo_id`
- Verificar que los pagos se vinculan correctamente con las cuotas

### 4.2. Ejecutar queries de integridad

**Queries a ejecutar:**
- **PASO 4.1:** Verificar pagos con prestamo_id inválido
- **PASO 4.2:** Verificar pagos con prestamo_id pero cédula no coincide

**Resultado esperado:**
- 0 pagos con prestamo_id inválido
- 0 pagos con prestamo_id pero cédula diferente

### 4.3. Ejecutar resumen final

**Query a ejecutar:**
- **RESUMEN FINAL:** Estado completo del sistema

**Resultado esperado:**
- Ver el estado completo después de la reconciliación
- Comparar con los valores iniciales del diagnóstico

---

## 🔄 PASO 5: EJECUTAR QUERIES DE VERIFICACIÓN COMPLETA

### 5.1. Ejecutar script completo de verificación

**Archivo:** `scripts/sql/verificar_vinculacion_pagos_cuotas.sql`

**Ejecutar todas las queries:**
- Queries de diagnóstico (ya ejecutadas)
- Queries de verificación principales (1-11)

**Resultado esperado:**
- Las queries ahora deberían devolver resultados (no vacías)
- Verificar que las reglas de negocio se cumplen correctamente

---

## 📝 CHECKLIST DE EJECUCIÓN

### Antes de empezar:
- [ ] Backup de la base de datos
- [ ] Variables de entorno configuradas (DATABASE_URL)
- [ ] Entorno virtual activado (si aplica)

### Diagnóstico:
- [ ] Ejecutar PASO 1.1, 1.2, 1.3 en DBeaver
- [ ] Ejecutar PASO 2.1, 2.2, 2.3 en DBeaver
- [ ] Revisar y documentar resultados

### Reconciliación:
- [ ] Ejecutar script Python en modo DRY RUN
- [ ] Revisar resultados del DRY RUN
- [ ] Si los resultados son correctos, ejecutar con `--apply`
- [ ] Documentar cambios aplicados

### Verificación:
- [ ] Ejecutar PASO 3.1, 3.2 en DBeaver
- [ ] Ejecutar PASO 4.1, 4.2 en DBeaver
- [ ] Ejecutar RESUMEN FINAL
- [ ] Ejecutar script completo de verificación (verificar_vinculacion_pagos_cuotas.sql)

### Validación final:
- [ ] Comparar resultados antes y después
- [ ] Verificar que las queries de verificación devuelven datos
- [ ] Documentar problemas encontrados (si los hay)

---

## 🚨 PROBLEMAS COMUNES Y SOLUCIONES

### Problema 1: Script Python no encuentra Python
**Solución:**
```powershell
# Probar con 'py' en lugar de 'python'
py backend/scripts/reconciliar_pagos_cuotas.py
```

### Problema 2: Error de conexión a base de datos
**Solución:**
- Verificar que DATABASE_URL está configurada correctamente
- Verificar que la base de datos está accesible
- Verificar credenciales

### Problema 3: Queries SQL devuelven errores
**Solución:**
- Verificar que estás conectado a la base de datos correcta
- Verificar que las tablas existen
- Revisar logs de error en DBeaver

### Problema 4: DRY RUN muestra números incorrectos
**Solución:**
- Revisar la lógica del script de reconciliación
- Verificar que los datos de entrada son correctos
- No ejecutar con `--apply` hasta resolver el problema

---

## 📊 INTERPRETACIÓN DE RESULTADOS

### Resultados esperados después de reconciliación:

1. **Pagos con prestamo_id:**
   - Antes: 0
   - Después: Debería ser > 0 (idealmente igual a pagos conciliados con préstamo coincidente)

2. **Pagos conciliados con prestamo_id:**
   - Antes: 0
   - Después: Debería ser > 0

3. **Cuotas con pagos aplicados:**
   - Antes: 2,081
   - Después: Debería mantenerse o aumentar ligeramente

4. **Queries de verificación:**
   - Antes: Todas vacías
   - Después: Deberían devolver resultados

---

## 📞 SOPORTE

Si encuentras problemas durante la ejecución:
1. Revisar los logs del script Python
2. Revisar los mensajes de error en DBeaver
3. Documentar el problema específico
4. Consultar la documentación del proyecto

---

## 📅 FECHA DE CREACIÓN
2025-01-XX

## ✅ ÚLTIMA ACTUALIZACIÓN
2025-01-XX
