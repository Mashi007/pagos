# ANÁLISIS: Revisión Manual - Flujo Actual vs Flujo Esperado

## 🔴 PROBLEMA IDENTIFICADO

**El sistema ACTUAL:**
- ❌ No usa tabla temporal
- ❌ Guarda directamente a BD (tabla `revision_manual_prestamos`)
- ❌ Si validadores fallan, ya está modificado (riesgo de inconsistencia)
- ❌ No hay reversión segura si algo falla a mitad

**El flujo ESPERADO (según requisito):**
```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. EDICIÓN EN REVISIÓN MANUAL                                        │
│    - Cambios se almacenan en tabla TEMPORAL (seguro, reversible)    │
│    - Usuario ve preview/draft antes de confirmar                    │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 2. VALIDACIÓN DE VALIDADORES                                        │
│    - Cuando usuario presiona "Guardar y Procesar":                  │
│      ✓ ¿Estado de cuotas válido?                                    │
│      ✓ ¿Pagos conciliados?                                          │
│      ✓ ¿Datos coherentes?                                           │
│    - SI FALLA: temp NO se elimina, usuario corrige                 │
│    - SI OK: procede al siguiente paso                               │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 3. AUTOCONCILIACIÓN (CASCADA)                                       │
│    - Aplica pagos a cuotas automáticamente                          │
│    - Respeta cascada: por numero_cuota, por fecha_pago              │
│    - Genera cuotas_pagos si todo es válido                          │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 4. MIGRACIÓN BD PERMANENTE                                          │
│    - Copia datos de TEMPORAL a tablas reales:                       │
│      • prestamos → actualizar                                        │
│      • cuotas → reconstruir                                          │
│      • cuota_pagos → insertar con cascada                           │
│      • revision_manual_prestamos → marcar como "revisado"           │
│    - TRUNCATE tabla temporal                                         │
│    - COMMIT atómico o ROLLBACK                                       │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 5. CARGA A CÉDULA Y CUOTA CORRESPONDIENTE                           │
│    - Pago se asocia a:                                              │
│      • Cédula del cliente (prestamo.cedula)                         │
│      • Cuota específica (cuota_pagos.cuota_id)                      │
│    - Registro de auditoría registra TODO                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 TABLA TEMPORAL REQUERIDA

```sql
CREATE TABLE revision_manual_prestamos_temp (
    id VARCHAR(36) PRIMARY KEY,
    usuario_id INTEGER,
    prestamo_id INTEGER NOT NULL,
    
    -- CLIENTE (draft)
    cliente_datos_json TEXT,
    
    -- PRÉSTAMO (draft)
    prestamo_datos_json TEXT,
    
    -- CUOTAS (draft)
    cuotas_datos_json TEXT,
    
    -- PAGOS (draft)
    pagos_datos_json TEXT,
    
    -- ESTADO
    estado VARCHAR(20) DEFAULT 'borrador',
    validadores_resultado JSON,
    error_mensaje TEXT,
    
    creado_en DATETIME DEFAULT NOW(),
    actualizado_en DATETIME DEFAULT NOW(),
    
    FOREIGN KEY (prestamo_id) REFERENCES prestamos(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    INDEX idx_prestamo_id (prestamo_id),
    INDEX idx_usuario_id (usuario_id),
    INDEX idx_estado (estado)
);
```

---

## 🔍 DÓNDE IMPLEMENTAR

### Backend (Python/FastAPI)

**1. Crear migración Alembic:**
```
backend/alembic/versions/069_revision_manual_temporal.py
```

**2. Crear modelo:**
```
backend/app/models/revision_manual_prestamo_temporal.py
```

**3. Endpoints nuevos:**
```python
# backend/app/api/v1/endpoints/revision_manual/routes.py

@router.post("/prestamos/{id}/guardar-borrador")
def guardar_borrador_revision(prestamo_id, datos, db):
    """Guarda en tabla temporal, NO en BD real"""
    
@router.get("/prestamos/{id}/obtener-borrador")
def obtener_borrador(prestamo_id, db):
    """Lee desde temporal para preview"""
    
@router.post("/prestamos/{id}/validar-borrador")
def validar_borrador(prestamo_id, db):
    """Ejecuta validadores, retorna resultado"""
    
@router.post("/prestamos/{id}/confirmar-borrador")
def confirmar_borrador(prestamo_id, db):
    """Mueve de temporal a BD real si todo OK"""
    
@router.delete("/prestamos/{id}/descartar-borrador")
def descartar_borrador(prestamo_id, db):
    """Elimina borrador temporal sin guardar"""
```

### Frontend (React/TypeScript)

**1. Guardar cambios → tabla temporal (no directo a BD)**
**2. Validar antes de confirmar**
**3. Confirmar solo si validadores pasan**

---

## ✅ VALIDADORES A EJECUTAR

Antes de mover de temporal a BD:

- Coherencia cliente-préstamo
- Estados de cuota válidos
- Pagos conciliados y únicos
- Fechas coherentes
- Montos coherentes

---

## ⚠️ RIESGOS ACTUALES (SIN TABLA TEMPORAL)

1. Usuario presiona "Guardar" → Cambia BD directo
2. Si validadores fallan después → Datos ya están modificados
3. No hay reverción

---

## 📌 ACCIÓN RECOMENDADA

**Implementar tabla temporal en este orden:**

1. Migración Alembic
2. Modelo SQLAlchemy
3. Endpoints backend
4. Servicio frontend
5. UI: mostrar estado "Borrador" vs "Confirmado"
6. Limpieza: borradores viejos (>7 días) sin confirmar → DELETE

