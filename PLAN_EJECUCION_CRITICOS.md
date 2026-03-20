# 🔴 PROBLEMAS CRÍTICOS: Plan de Resolución y Ejecución

Fecha: 2026-03-20
Estado: DIAGNOSIS COMPLETADA → LISTA PARA CORRECCIÓN

---

## RESUMEN DE PROBLEMAS

### Problema 1: 14,127 pagos sin asignar (3,426,096.76 BS = 49.2%)
- **Causa**: Pagos ingresados sin relación a cuotas/préstamos
- **Impacto**: CRÍTICO - Casi 50% del dinero sin aplicar
- **Solución**: Asignar automáticamente por cédula + manual si es necesario

### Problema 2: Cuota 216933 sobre-aplicada (96 BS exceso)
- **Causa**: Múltiples pagos asignados sin validación
- **Impacto**: Inconsistencia de saldo
- **Solución**: Reducir último pago por el exceso exacto

### Problema 3: Estados inconsistentes (MORA no documentado)
- **Causa**: Estados no actualizados cuando hay pagos parciales
- **Impacto**: Reportes incorrectos, cobranza mal enfocada
- **Solución**: Recalcular todos los estados basado en aplicaciones + fecha vencimiento

---

## PLAN DE EJECUCIÓN

### Fase 1: DIAGNÓSTICO (YA COMPLETADO)
✅ Endpoints creados:
- GET /api/v1/criticos/diagnostico/pagos-sin-asignar
- GET /api/v1/criticos/diagnostico/cuota-sobre-aplicada/{cuota_id}
- GET /api/v1/criticos/diagnostico/estados-inconsistentes

✅ Servicio de diagnóstico:
- app/services/diagnostico_critico_service.py

### Fase 2: CORRECCIÓN (LISTA PARA EJECUTAR)

#### Opción A: Via SQL directamente (MÁS RÁPIDO)
1. Ejecutar: sql/03_correccion_critica.sql

Pasos:
- PASO 1: Asignar pagos huérfanos a préstamos por cédula
- PASO 2: Corregir cuota 216933 (reducir exceso)
- PASO 3: Actualizar todos los estados inconsistentes
- PASO 4: Verificar resultados

#### Opción B: Via endpoints REST (MÁS SEGURO - AUDITABLE)
1. POST /api/v1/criticos/corregir/cuota-sobre-aplicada/216933
2. POST /api/v1/criticos/corregir/estados-inconsistentes

### Fase 3: VALIDACIÓN (DESPUÉS DE CORRECCIÓN)
1. GET /api/v1/criticos/diagnostico/pagos-sin-asignar → debe retornar ~0 o bajo
2. GET /api/v1/criticos/diagnostico/cuota-sobre-aplicada/216933 → debe retornar exceso=0
3. GET /api/v1/criticos/diagnostico/estados-inconsistentes → debe retornar 0 inconsistencias

---

## INSTRUCCIONES PASO A PASO

### PASO 1: Ejecutar Diagnóstico Completo (Verificar Estado Actual)

#### En Render (producción):
\\\ash
# Terminal 1: Obtener ADMIN_TOKEN válido (usar login de admin)
curl -X POST "https://rapicredit.onrender.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"usuario": "admin", "contrasena": "***"}'
# Guardar el token retornado

# Terminal 2: Diagnóstico de pagos sin asignar
curl "https://rapicredit.onrender.com/api/v1/criticos/diagnostico/pagos-sin-asignar" \
  -H "Authorization: Bearer \" | jq '.' | tee pagos-sin-asignar-diag.json

# Terminal 3: Diagnóstico de cuota sobre-aplicada
curl "https://rapicredit.onrender.com/api/v1/criticos/diagnostico/cuota-sobre-aplicada/216933" \
  -H "Authorization: Bearer \" | jq '.' | tee cuota-216933-diag.json

# Terminal 4: Diagnóstico de estados inconsistentes
curl "https://rapicredit.onrender.com/api/v1/criticos/diagnostico/estados-inconsistentes" \
  -H "Authorization: Bearer \" | jq '.' | tee estados-incons-diag.json
\\\

### PASO 2: Revisar Diagnósticos

Verificar en los archivos JSON:
- pagos-sin-asignar-diag.json: ¿Cuántos pagos sin asignar?
- cuota-216933-diag.json: ¿Exceso exacto?
- estados-incons-diag.json: ¿Cuántas inconsistencias?

### PASO 3: Ejecutar Correcciones

#### OPCIÓN A: Via SQL (RECOMENDADO para Render)

Conectarse a BD de Render con pgAdmin o CLI:
\\\ash
# Opción 1: Via Render CLI
heroku pg:psql -a <RENDER_APP_NAME> < sql/03_correccion_critica.sql

# Opción 2: Via pgAdmin (Render dashboard)
# Copiar contenido de sql/03_correccion_critica.sql
# Pegar en Query editor
# Ejecutar

# Opción 3: Via psql
psql -h <RENDER_HOST> -U <USER> -d <DBNAME> -f sql/03_correccion_critica.sql
\\\

#### OPCIÓN B: Via Endpoints REST (Más auditable)

\\\ash
# Corrección 1: Cuota sobre-aplicada
curl -X POST "https://rapicredit.onrender.com/api/v1/criticos/corregir/cuota-sobre-aplicada/216933" \
  -H "Authorization: Bearer \" | jq '.'

# Corrección 2: Estados inconsistentes
curl -X POST "https://rapicredit.onrender.com/api/v1/criticos/corregir/estados-inconsistentes" \
  -H "Authorization: Bearer \" | jq '.'
\\\

### PASO 4: Validación Post-Corrección

Ejecutar diagnóstico nuevamente:
\\\ash
# Debe retornar 0 o muy bajo
curl "https://rapicredit.onrender.com/api/v1/criticos/diagnostico/pagos-sin-asignar" \
  -H "Authorization: Bearer \" | jq '.data.total_pagos'

# Debe retornar exceso = 0
curl "https://rapicredit.onrender.com/api/v1/criticos/diagnostico/cuota-sobre-aplicada/216933" \
  -H "Authorization: Bearer \" | jq '.data.exceso'

# Debe retornar inconsistencias = 0
curl "https://rapicredit.onrender.com/api/v1/criticos/diagnostico/estados-inconsistentes" \
  -H "Authorization: Bearer \" | jq '.data.inconsistencias'
\\\

---

## ARCHIVOS CREADOS PARA RESOLUCIÓN

### Servicios
- \pp/services/diagnostico_critico_service.py\
  - DiagnosticoCritico: diagnostica los 3 problemas
  - CorrectoresCriticos: corrige automáticamente

### Endpoints
- \pp/api/v1/endpoints/criticos.py\
  - 3 endpoints de diagnóstico
  - 2 endpoints de corrección

### SQL
- \sql/03_correccion_critica.sql\
  - Scripts prontos para ejecutar
  - Verificaciones pre y post

### Integración
- \pp/main.py\ (actualizado)
  - Router de críticos incluido

---

## RIESGOS Y MITIGACIONES

### Riesgo 1: Asignar pagos al préstamo equivocado
**Mitigación**: 
- Solo asignar si cliente tiene UN SOLO préstamo activo
- Registrar en auditoría TODAS las asignaciones
- Reversible si es necesario

### Riesgo 2: Reducir pago correcto de cuota 216933
**Mitigación**:
- Mostrar historial de pagos aplicados
- Reducir solo del ÚLTIMO pago (más reciente)
- Registrar corrección en auditoría
- Reversible: existe en cuota_pagos

### Riesgo 3: Cambiar estado de cuota incorrectamente
**Mitigación**:
- Usar lógica clara: PAGADO > PARCIAL > MORA > PENDIENTE
- Basado en hechos: monto aplicado + fecha vencimiento
- Reversible si hay inconsistencias

---

## ROLLBACK (Si es necesario)

### Rollback de Asignaciones Automáticas
\\\sql
-- Eliminar asignaciones automáticas de hoy
DELETE FROM cuota_pagos cp
WHERE cp.fecha_aplicacion > NOW() - INTERVAL '1 day'
  AND NOT EXISTS (
    SELECT 1 FROM auditoria_conciliacion_manual acm 
    WHERE acm.pago_id = cp.pago_id AND acm.tipo_asignacion = 'MANUAL'
  );

-- Limpiar auditoría
DELETE FROM auditoria_conciliacion_manual
WHERE fecha_asignacion > NOW() - INTERVAL '1 day'
  AND tipo_asignacion = 'AUTOMATICA';
\\\

### Rollback de Correcciones de Estados
\\\sql
-- Restaurar estados a anterior
-- (Requiere backup o versión control en BD)
-- Contactar con equipo si se necesita
\\\

---

## MÉTRICAS ESPERADAS POST-CORRECCIÓN

| Métrica | Antes | Después | Meta |
|---------|-------|---------|------|
| Pagos sin asignar | 14,127 | < 100 | < 1% |
| Monto sin asignar | 3,426,096.76 BS | < 50,000 BS | < 1% |
| Cuotas sobre-aplicadas | 1 | 0 | 0 |
| Estados inconsistentes | 100s | 0 | 0 |
| Tasa de asignación correcta | N/A | > 99% | > 99% |

---

## TIMELINE RECOMENDADO

### Opción 1: Ejecución Rápida (1 hora)
1. 10 min: Ejecutar diagnósticos
2. 40 min: Ejecutar correcciones SQL
3. 10 min: Validar resultados

### Opción 2: Ejecución Segura (3 horas)
1. 30 min: Ejecutar diagnósticos
2. 1 hora: Revisar detalladamente
3. 1 hora: Ejecutar correcciones por endpoint (más auditable)
4. 30 min: Validar y documentar

**RECOMENDACIÓN**: Opción 2 (más seguro y auditable)

---

## VERIFICACIÓN FINAL

Después de todas las correcciones:

\\\ash
# Dashboard de salud de conciliación
curl "https://rapicredit.onrender.com/api/v1/conciliacion/estados-cuotas" \
  -H "Authorization: Bearer \" | jq '.data.resumen'

# Auditoría de cambios
curl "https://rapicredit.onrender.com/api/v1/auditoria/conciliacion?dias=1" \
  -H "Authorization: Bearer \" | jq '.data.estadisticas'
\\\

---

## ESTADO FINAL ESPERADO

✅ 14,127 pagos asignados correctamente
✅ Cuota 216933 balanceada (0 exceso)
✅ Todos los estados consistentes
✅ Auditoría completa de cambios
✅ Sistema listo para operación normal

---

**Listo para ejecutar correcciones.**
