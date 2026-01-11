# 📋 Guía de Ejecución: FASE 3 - Sincronización Modelo ORM vs BD

> **Sincronizar columnas faltantes entre modelos ORM y base de datos**  
> Última actualización: 2026-01-11

---

## 🎯 Objetivo

Sincronizar los modelos ORM (SQLAlchemy) con la base de datos real, agregando las columnas faltantes para que el código pueda acceder a todos los datos existentes en la BD.

---

## 📋 Problemas Identificados

### **Problema 3.1: Columnas ML en modelo Prestamo**
**Estado:** ✅ **YA RESUELTO**
- Las columnas ML ya existen en el modelo `Prestamo`
- Existe migración Alembic que las crea: `20251118_add_ml_impago_calculado_prestamos.py`
- No requiere acción adicional

### **Problema 3.2: Columnas en BD sin modelo ORM**
**Estado:** ⚠️ **PENDIENTE DE EJECUCIÓN**

**Tabla `pagos` (21 columnas faltantes):**
- banco, codigo_pago, comprobante, creado_en, descuento
- dias_mora, documento, fecha_vencimiento, hora_pago, metodo_pago
- monto, monto_capital, monto_cuota_programado, monto_interes
- monto_mora, monto_total, numero_operacion, observaciones
- referencia_pago, tasa_mora, tipo_pago

**Tabla `cuotas` (2 columnas faltantes):**
- creado_en, actualizado_en

---

## 📋 Secuencia de Ejecución

### **PASO 1: Diagnóstico** 🔍
**Script:** `FASE3_DIAGNOSTICO_COLUMNAS.sql`

**Qué hacer:**
1. Ejecutar el script de diagnóstico
2. Revisar qué columnas realmente existen en la BD
3. Verificar qué columnas faltan

**Resultado esperado:**
- Lista de columnas ML en prestamos (debe mostrar 4 columnas)
- Lista de columnas esperadas en pagos (21 columnas)
- Lista de columnas esperadas en cuotas (2 columnas)

---

### **PASO 2: Ejecutar Sincronización**

**Opción A: Usar Migración Alembic (Recomendado)**
```bash
cd backend
alembic upgrade head
```

**Opción B: Ejecutar Script SQL Directo**
**Script:** `FASE3_AGREGAR_COLUMNAS.sql`

**Qué hacer:**
1. Abrir DBeaver
2. Conectarse a la base de datos
3. Ejecutar el script `FASE3_AGREGAR_COLUMNAS.sql`
4. Revisar los mensajes de confirmación

**Resultado esperado:**
- Mensajes "✅ Columna X agregada a tabla Y" para cada columna
- Verificación final mostrando el conteo de columnas agregadas

---

### **PASO 3: Verificar Modelos ORM**

**Qué hacer:**
1. Verificar que los modelos `Pago` y `Cuota` tienen las nuevas columnas
2. Reiniciar la aplicación backend
3. Verificar que no hay errores de SQLAlchemy

**Archivos modificados:**
- ✅ `backend/app/models/pago.py` - 21 columnas agregadas
- ✅ `backend/app/models/amortizacion.py` - 2 columnas agregadas

---

## 📊 Resumen de Cambios

### **Modelo Pago - Columnas Agregadas (21):**

**Información bancaria:**
- `banco` (VARCHAR 100)
- `metodo_pago` (VARCHAR 50)
- `tipo_pago` (VARCHAR 50)

**Códigos y referencias:**
- `codigo_pago` (VARCHAR 30)
- `numero_operacion` (VARCHAR 50)
- `referencia_pago` (VARCHAR 100)
- `comprobante` (VARCHAR 200)
- `documento` (VARCHAR 50)

**Montos detallados:**
- `monto` (NUMERIC 12,2)
- `monto_capital` (NUMERIC 12,2)
- `monto_interes` (NUMERIC 12,2)
- `monto_cuota_programado` (NUMERIC 12,2)
- `monto_mora` (NUMERIC 12,2)
- `monto_total` (NUMERIC 12,2)
- `descuento` (NUMERIC 12,2)

**Mora y vencimiento:**
- `dias_mora` (INTEGER)
- `tasa_mora` (NUMERIC 5,2)
- `fecha_vencimiento` (TIMESTAMP)

**Fechas y observaciones:**
- `hora_pago` (VARCHAR 10)
- `creado_en` (TIMESTAMP)
- `observaciones` (TEXT)

### **Modelo Cuota - Columnas Agregadas (2):**
- `creado_en` (DATE)
- `actualizado_en` (DATE)

---

## ⚠️ Advertencias Importantes

1. **Backup:** Hacer backup de la base de datos antes de ejecutar
2. **Verificar diagnóstico:** Siempre ejecutar el PASO 1 primero
3. **Columnas existentes:** Los scripts usan `IF NOT EXISTS` para evitar errores
4. **Migración Alembic:** Si usas Alembic, ejecuta `alembic upgrade head`

---

## 🔄 Si algo sale mal

### **Rollback (si es necesario):**
```sql
-- Eliminar columnas de pagos (si es necesario)
ALTER TABLE pagos DROP COLUMN IF EXISTS banco;
ALTER TABLE pagos DROP COLUMN IF EXISTS metodo_pago;
-- ... (repetir para cada columna)

-- Eliminar columnas de cuotas
ALTER TABLE cuotas DROP COLUMN IF EXISTS creado_en;
ALTER TABLE cuotas DROP COLUMN IF EXISTS actualizado_en;
```

O usar Alembic:
```bash
alembic downgrade -1
```

---

## 📝 Checklist de Ejecución

- [ ] PASO 1 ejecutado (diagnóstico de columnas)
- [ ] Backup de base de datos realizado
- [ ] PASO 2 ejecutado (agregar columnas - Alembic o SQL)
- [ ] Verificación final ejecutada
- [ ] Modelos ORM verificados
- [ ] Aplicación backend reiniciada sin errores

---

## ✅ Beneficios de Completar FASE 3

1. **Acceso completo a datos:** Podrás leer/escribir todas las columnas desde Python
2. **API más completa:** Endpoints pueden usar todas las columnas disponibles
3. **Reportes más precisos:** Generar reportes usando todos los datos
4. **Migraciones seguras:** Alembic funcionará correctamente
5. **Mantenibilidad:** Código y BD sincronizados

---

**Última revisión:** 2026-01-11
