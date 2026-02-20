# INSTRUCCIONES DE USO - AUDITORÍA DE PAGOS CONCILIADOS

## 📋 Resumen

Esta carpeta contiene herramientas de diagnóstico para auditar por qué los pagos conciliados no aparecían en la tabla de amortización del préstamo #4601.

---

## 🛠️ Herramientas Disponibles

### 1. Script SQL de Diagnóstico
**Archivo:** `diagnostico_pagos_conciliados.sql`  
**Propósito:** Ejecutar queries directamente en PostgreSQL para diagnosticar el problema  
**Requisitos:** Acceso a la BD de Render  
**Tiempo:** ~2 minutos

#### Uso:
```bash
# Opción 1: Desde línea de comandos
psql $DATABASE_URL < backend/sql/diagnostico_pagos_conciliados.sql

# Opción 2: En pgAdmin o herramienta GUI
# 1. Copiar contenido del archivo
# 2. Pegar en la consola SQL
# 3. Ejecutar
```

#### Qué hace:
- ✅ Muestra información del préstamo #4601
- ✅ Lista todas las cuotas generadas
- ✅ Muestra todos los pagos registrados
- ✅ Analiza relación cuota-pago (JOIN por FK)
- ✅ Busca pagos por rango de fechas (como lo hace el nuevo endpoint)
- ✅ Calcula totales financieros
- ✅ Diagnostica la causa raíz del problema

#### Output Esperado:
```
1. Información del Préstamo
   → Cédula, nombres, estado, número de cuotas

2. Cuotas del Préstamo
   → Número de cuota, fecha vencimiento, monto, estado

3. Todos los Pagos
   → ID, monto, conciliado, verificado, referencia

4. Análisis Cuota-Pago (JOIN)
   → Muestra si pago_id está vinculado correctamente

5. Búsqueda por Rango de Fechas
   → Pagos encontrados en ±15 días del vencimiento

6. Conteos Resumen
   → Total de cuotas, pagos, pagos conciliados

7. Totales Financieros
   → Total financiamiento, pagos, saldos

8. Diagnóstico
   → Identifica la raíz del problema específicamente
```

---

### 2. Script Python de Auditoría
**Archivo:** `auditoria_pagos_conciliados.py`  
**Propósito:** Diagnóstico programático usando SQLAlchemy  
**Requisitos:** Python 3.7+, dependencias del proyecto  
**Tiempo:** ~1 minuto

#### Uso:
```bash
cd backend
python scripts/auditoria_pagos_conciliados.py 4601
```

#### Parámetros:
- `4601`: ID del préstamo a auditar (reemplazar según sea necesario)

#### Ejemplo:
```bash
# Auditar otro préstamo
python scripts/auditoria_pagos_conciliados.py 1234
```

#### Output:
```
================================================================================
AUDITORIA INTEGRAL - PRESTAMO #4601
================================================================================
Cliente: PEDRO ALEXANDER VILLARROEL RODRIGUEZ (Cédula: ...)
Total Financiamiento: $2160.00
Estado: DESEMBOLSADO
Número de Cuotas: 9
================================================================================

✓ CUOTAS ENCONTRADAS: 9
────────────────────────────────────────────────────────────────────────────────

📋 CUOTA #1
   Fecha Vencimiento: 2025-04-15
   Monto: $240.00
   Estado BD: PENDIENTE
   Total Pagado (cuota.total_pagado): $0.00
   ℹ️  Sin pago_id directo
   🔍 PAGOS ENCONTRADOS EN RANGO [2025-04-01 ... 2025-04-30]: 1
      • Pago 501: $240.00 - ✅ CONCILIADO 
        Fecha: 2025-04-16 10:30:00 | Referencia: REF-001

...

TOTALES:
  Total Financiamiento: $2160.00
  Total Pagos Conciliados: $480.00
  Saldo Pendiente: $1680.00
```

---

## 🚀 Casos de Uso

### Caso 1: Verificar si el problema sigue existiendo
```bash
# Ejecutar antes del deploy
python scripts/auditoria_pagos_conciliados.py 4601

# Verificar que:
# - Hay pagos conciliados en tabla pagos ✅
# - pago_id es NULL en cuotas ❌
# - Se encuentran pagos en rango de fechas ✅
```

### Caso 2: Diagnosticar por qué un préstamo no muestra pagos
```bash
# Para cualquier prestamo_id
python scripts/auditoria_pagos_conciliados.py <prestamo_id>

# Revisa el output:
# - Si tiene cuotas
# - Si tiene pagos
# - Si están vinculados
# - Si están conciliados
```

### Caso 3: Validar que la solución funcionó
```bash
# Después del deploy
# 1. Ejecutar script
python scripts/auditoria_pagos_conciliados.py 4601

# 2. Hacer GET al endpoint
curl -X GET "https://rapicredit.onrender.com/api/v1/prestamos/4601/cuotas" \
  -H "Authorization: Bearer <token>"

# 3. Verificar que pago_conciliado=true y pago_monto_conciliado > 0
```

---

## 📊 Interpretación de Resultados

### Buena Señal ✅
```
🔍 PAGOS ENCONTRADOS EN RANGO [...]: 1
   • Pago 501: $240.00 - ✅ CONCILIADO
```
→ El nuevo endpoint ENCONTRARÁ estos pagos

### Problema ❌
```
❌ NO HAY PAGOS en rango [...]
```
→ No hay pagos registrados para esta cuota

### Señal de Alerta ⚠️
```
✅ PAGO DIRECTO ENCONTRADO (pago_id=1)
   - Monto: $240.00
   - Conciliado: false  ⚠️
```
→ Pago vinculado pero NO conciliado

---

## 🔧 Troubleshooting

### Error: "Column does not exist"
```
ERROR: column p.monto_cuota does not exist
```
**Solución:** Estaba en versión anterior del script. Ya está corregido en commit `0a0c581a`.

### Error: "Connection refused"
```
psql: error: connection to server at "localhost" (127.0.0.1), port 5432 failed
```
**Causa:** No hay BD local, necesitas conectar a Render  
**Solución:** Usar `psql $DATABASE_URL` (no `psql` solo)

### Script Python falla con "ModuleNotFoundError"
```
ModuleNotFoundError: No module named 'sqlalchemy'
```
**Solución:**
```bash
# Instalar dependencias
pip install -r backend/requirements.txt

# O si estás en el contenedor Docker
docker-compose exec app pip install -r requirements.txt
```

---

## 📈 Métricas Clave

Al ejecutar la auditoría, verificar:

| Métrica | Esperado | Problema |
|---------|----------|---------|
| Cuotas generadas | > 0 | = 0 → No hay tabla amortización |
| Pagos registrados | > 0 | = 0 → No hay pagos en BD |
| Pagos conciliados | > 0 | = 0 → No hay pagos conciliados |
| pago_id vinculado | Opcional | N/A (el nuevo endpoint busca por rango) |
| Pagos en rango | > 0 | = 0 → Problema de fecha |

---

## 📝 Logs y Auditoría

### Dónde encontrar logs
```
Backend (FastAPI):
/var/log/rapicredit/backend.log

BD (PostgreSQL):
logs via pgAdmin o `SHOW log_directory`
```

### Verificar que el nuevo endpoint está activo
```bash
# Antes del deploy
curl https://rapicredit.onrender.com/api/v1/prestamos/4601/cuotas
# → Error 401 (sin token) o 404 (préstamo no existe)

# Después del deploy
curl -H "Authorization: Bearer <token>" \
  https://rapicredit.onrender.com/api/v1/prestamos/4601/cuotas
# → Array de cuotas con "pago_conciliado" y "pago_monto_conciliado"
```

---

## 🎯 Checklist de Validación Post-Deploy

- [ ] Ejecutar script de auditoría
- [ ] Verificar que hay pagos conciliados en tabla `pagos`
- [ ] Verificar que `pago_id` es NULL en cuotas
- [ ] Llamar endpoint `/cuotas` y verificar `pago_conciliado=true`
- [ ] Abrir frontend y verificar columna "Pago conciliado" muestra montos
- [ ] Exportar Excel y PDF, verificar que incluyen pagos conciliados
- [ ] No hay errores en consola del navegador
- [ ] No hay errores en logs del servidor

---

## 📞 Soporte

Si algo no funciona:

1. **Ejecutar script de auditoría** para diagnosticar
2. **Revisar logs** (backend y BD)
3. **Verificar que el endpoint está actualizado** (commit debe estar deployed)
4. **Confirmar que BD tiene datos** (cuotas y pagos)

---

**Última Actualización:** 2026-02-19  
**Commit Principal:** f4745897  
**Commit Corrección SQL:** 0a0c581a
