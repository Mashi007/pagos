# ✅ IMPLEMENTACIÓN: Tabla Temporal para Revisión Manual

**Fecha**: 2026-05-01  
**Estado**: ✅ BACKEND COMPLETADO

---

## 📋 QUÉ SE IMPLEMENTÓ

### **1. Migración Alembic (069)**
📁 Archivo: `backend/alembic/versions/069_revision_manual_temporal.py`

```sql
CREATE TABLE revision_manual_prestamos_temp (
    id VARCHAR(36) PRIMARY KEY,
    usuario_id INTEGER FOREIGN KEY,
    prestamo_id INTEGER FOREIGN KEY,
    
    cliente_datos_json TEXT,
    prestamo_datos_json TEXT,
    cuotas_datos_json TEXT,
    pagos_datos_json TEXT,
    
    estado VARCHAR(20) DEFAULT 'borrador',
    validadores_resultado TEXT,
    error_mensaje TEXT,
    
    creado_en DATETIME DEFAULT NOW(),
    actualizado_en DATETIME DEFAULT NOW(),
    
    INDEXES: prestamo_usuario, estado, creado_en
);
```

---

### **2. Modelo SQLAlchemy**
📁 Archivo: `backend/app/models/revision_manual_prestamo_temporal.py`

```python
class RevisionManualPrestamoTemp(Base):
    __tablename__ = "revision_manual_prestamos_temp"
    
    # Campos principales...
```

✅ Registrado en: `backend/app/models/__init__.py`

---

### **3. Cinco Endpoints Backend**

Todos en: `backend/app/api/v1/endpoints/revision_manual/routes.py`

#### **Endpoint 1: POST /prestamos/{id}/guardar-borrador**
```
Guarda cambios en tabla temporal (NO afecta BD real).
- Crea o actualiza fila en revision_manual_prestamos_temp
- Estado: 'borrador'
- Respuesta: { borrador_id, estado }
```

#### **Endpoint 2: GET /prestamos/{id}/obtener-borrador**
```
Lee borrador temporal para preview.
- Retorna: cliente_datos, prestamo_datos, cuotas_datos, pagos_datos
- Estado actual
- Resultado de validación (si existe)
```

#### **Endpoint 3: POST /prestamos/{id}/validar-borrador**
```
Ejecuta VALIDADORES sobre el borrador.
Retorna: { valido, errores[], advertencias[] }

Validadores:
✓ Coherencia cliente-préstamo
✓ Estados de cuota válidos
✓ Pagos conciliados
✓ Fechas coherentes

Si VALIDO:
  - estado → 'validado'
  - Sin error_mensaje
  
Si INVALIDO:
  - estado → 'error'
  - error_mensaje lleno
  - validadores_resultado con detalles
```

#### **Endpoint 4: POST /prestamos/{id}/confirmar-borrador**
```
Mueve borrador validado a BD real (transacción atómica).

FLUJO:
1. Verifica estado='validado'
2. Aplica cambios de prestamo_datos a tabla prestamos
3. Reconstruye cuotas (cascada, con aplicación de pagos)
4. Registra en tabla auditoria
5. COMMIT atómico
6. DELETE borrador (confirmado/consumido)

Respuesta: { 
  cuotas_creadas, 
  pagos_aplicados, 
  cambios: { campo: {anterior, nuevo} } 
}

Si ERROR: ROLLBACK, borrador SE QUEDA para reintento
```

#### **Endpoint 5: DELETE /prestamos/{id}/descartar-borrador**
```
Descarta borrador sin guardar.
- Elimina fila de tabla temporal
- BD real intacta
- Cambios perdidos (confirm)
```

---

## 🔄 FLUJO COMPLETO

```
┌─ USUARIO EDITA EN REVISIÓN MANUAL ─────────────────────┐
│ (cambios en memoria/UI React)                           │
└───────────────────────────────────────────────────────┬─┘
                                                         │
                    POST /guardar-borrador
                                                         ▼
┌─ TABLA TEMPORAL (SEGURA, REVERSIBLE) ──────────────────┐
│ revision_manual_prestamos_temp                          │
│ - cliente_datos_json: "{...}"                           │
│ - prestamo_datos_json: "{...}"                          │
│ - cuotas_datos_json: "[...]"                            │
│ - estado: 'borrador'                                    │
└───────────────────────────────────────────────────────┬─┘
                                                         │
        Usuario presiona "Validar y Confirmar"           │
        POST /validar-borrador                           ▼
┌─ EJECUTAR VALIDADORES ─────────────────────────────────┐
│ ✓ ¿Coherencia cliente?                                 │
│ ✓ ¿Estados válidos?                                    │
│ ✓ ¿Pagos conciliados?                                  │
└───────────────────────────────────────────────────────┬─┘
                                                         │
        SI FALLO: estado='error', temp SE QUEDA         ▽
        Usuario corrige y vuelve a validar              ┌──┐
                                                         │  │ REINTENTO
                                                         └──┘
                                                         │
        SI OK: estado='validado'                         │
        Mostrar preview                                  ▼
        Usuario presiona "Confirmar"                 ┌──────────────┐
        POST /confirmar-borrador                    │ ATÓMICO: SÍ o │
                                                     │ ROLLBACK      │
                                                     └──────────────┘
                                                         │
                                ┌───────────────────────┘
                                ▼
┌─ BD REAL (TRANSACCIÓN ATÓMICA) ────────────────────────┐
│ 1. UPDATE prestamos (campos desde borrador)             │
│ 2. DELETE cuotas viejas                                 │
│ 3. INSERT cuotas nuevas (recalculadas)                  │
│ 4. INSERT cuota_pagos (cascada automática)              │
│ 5. INSERT auditoria (registro completo)                 │
│ 6. COMMIT (TODO o NADA)                                 │
│ 7. DELETE borrador (confirmado)                         │
└───────────────────────────────────────────────────────┬─┘
                                                         │
                                                         ▼
                    ✅ COMPLETADO
                    Cédula actualizada
                    Cuotas cargadas
                    Pagos aplicados
```

---

## 📊 ESTADOS DEL BORRADOR

```
'borrador'   → Inicial, sin validar
    ↓ POST /validar-borrador
'validado'   → Pasó validadores, listo para confirmar
    ↓ POST /confirmar-borrador
(ELIMINADO)  → Confirmado y movido a BD real
```

O si falla validación:
```
'error'      → Validadores encontraron problemas
    ↓ Usuario corrige y POST /validar-borrador de nuevo
'validado'   → Ahora OK
```

---

## 🎯 VENTAJAS DE ESTA IMPLEMENTACIÓN

✅ **SEGURIDAD**: 
- Cambios en tabla temporal (separada)
- BD real intacta hasta confirmación
- Reversión simple (DELETE borrador)

✅ **TRANSACCIONALIDAD**: 
- Cascada atómica (todo o nada)
- Si COMMIT falla → ROLLBACK, tabla temporal SE QUEDA
- Usuario puede reintentarlo

✅ **AUDITORÍA**: 
- Cada acción registrada en tabla auditoria
- Validadores trackeados en validadores_resultado
- Error log con detalles

✅ **USUARIO FRIENDLY**: 
- Preview antes de confirmar
- Corrige errores sin perder BD real
- Feedback claro de validadores

---

## 🚀 PRÓXIMO PASO: FRONTEND

**Pendiente**: Cambiar servicio frontend para usar los 5 nuevos endpoints.

**Archivo a modificar**: 
`frontend/src/services/revisionManualService.ts`

**Cambios necesarios**:
```typescript
// ANTES: Guardaba directo a BD
await PUT /api/v1/revision-manual/prestamos/{id}

// DESPUÉS: Guardar a tabla temporal
await POST /api/v1/revision-manual/prestamos/{id}/guardar-borrador

// Luego validar
await POST /api/v1/revision-manual/prestamos/{id}/validar-borrador

// Si OK, confirmar
await POST /api/v1/revision-manual/prestamos/{id}/confirmar-borrador
```

---

## 📝 SQL MANUAL (si necesitas migrar manualmente)

```sql
-- Crear tabla
CREATE TABLE revision_manual_prestamos_temp (
    id VARCHAR(36) PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    prestamo_id INTEGER NOT NULL REFERENCES prestamos(id) ON DELETE CASCADE,
    cliente_datos_json TEXT,
    prestamo_datos_json TEXT,
    cuotas_datos_json TEXT,
    pagos_datos_json TEXT,
    estado VARCHAR(20) NOT NULL DEFAULT 'borrador',
    validadores_resultado TEXT,
    error_mensaje TEXT,
    creado_en DATETIME NOT NULL DEFAULT NOW(),
    actualizado_en DATETIME NOT NULL DEFAULT NOW()
);

-- Índices
CREATE INDEX ix_revision_manual_temp_prestamo_usuario 
    ON revision_manual_prestamos_temp(prestamo_id, usuario_id);
CREATE INDEX ix_revision_manual_temp_estado 
    ON revision_manual_prestamos_temp(estado);
CREATE INDEX ix_revision_manual_temp_creado 
    ON revision_manual_prestamos_temp(creado_en);

-- Limpiar borradores viejos (operación de mantenimiento)
DELETE FROM revision_manual_prestamos_temp 
WHERE estado = 'borrador' AND creado_en < DATE_SUB(NOW(), INTERVAL 7 DAY);
```

---

## ✅ CHECKLIST DE VALIDACIÓN

- [x] Migración Alembic creada
- [x] Modelo SQLAlchemy definido
- [x] Imports actualizados (__init__.py)
- [x] 5 endpoints implementados
- [x] Sintaxis Python verificada
- [x] Validadores incluidos
- [x] Transaccionalidad atómica
- [x] Logging completo
- [x] Auditoría registrada
- [ ] Frontend: Cambiar a usar tabla temporal
- [ ] Tests unitarios (opcional)
- [ ] Documentación de API (swagger)

---

## 🔗 REFERENCIAS DE CÓDIGO

**Tabla temporal**: `revision_manual_prestamos_temp`
**Modelo**: `RevisionManualPrestamoTemp`
**Endpoints**: `/api/v1/revision-manual/prestamos/{id}/...`

**Estados**: 'borrador' → 'validado' → (CONFIRMADO/ELIMINADO)

---

## 📌 NOTAS IMPORTANTES

1. **Datos en JSON**: 
   - cliente_datos, prestamo_datos, cuotas_datos, pagos_datos se almacenan como JSON strings
   - Permite cambios parciales sin schema breaking

2. **Foreign Keys**:
   - prestamo_id: CASCADE (si se elimina préstamo, se borra borrador)
   - usuario_id: SET NULL (si se elimina usuario, se queda el borrador)

3. **Limpieza**:
   - Borradores viejos (>7 días, estado='borrador') pueden limpiarse
   - Borradores confirmados se eliminan automáticamente

4. **Concurrencia**:
   - Un usuario solo puede tener UN borrador por préstamo
   - Múltiples usuarios = múltiples borradores (cada uno su préstamo)

---

**Estado**: ✅ IMPLEMENTACIÓN BACKEND COMPLETADA  
**Siguiente**: Frontend changes (revisionManualService.ts)

