# TABLA DE AUDITORÍA - REVISIÓN MANUAL

## 📋 Resumen Ejecutivo

Sistema completo de auditoría en PostgreSQL para registrar **CADA CAMBIO INDIVIDUAL** realizado en la interfaz de revisión manual:
- ✅ Cliente (nombres, telefono, email, etc.)
- ✅ Préstamo (total, cuotas, tasa, etc.)
- ✅ Cuotas (fecha pago, monto, estado)
- ✅ Trazabilidad completa (quién, cuándo, qué, por qué)

---

## 🗄️ TABLAS CREADAS

### **1. `auditoria_revision_manual`** (PRINCIPAL)

**Propósito**: Registrar cada cambio individual

**Estructura**:
```sql
CREATE TABLE public.auditoria_revision_manual (
    id                          SERIAL PRIMARY KEY,
    prestamo_id                 INTEGER NOT NULL (FK → prestamos),
    cliente_id                  INTEGER (FK → clientes),
    cuota_id                    INTEGER (FK → cuotas),
    tipo_cambio                 VARCHAR(50),      -- 'cliente','prestamo','cuota'
    tabla_afectada              VARCHAR(50),      -- 'clientes','prestamos','cuotas'
    campo_modificado            VARCHAR(100),     -- nombre del campo
    valor_anterior              TEXT,             -- valor antes
    valor_nuevo                 TEXT,             -- valor después
    usuario_email               VARCHAR(255),     -- quién hizo el cambio
    usuario_id                  INTEGER,          -- ID del usuario
    ip_address                  VARCHAR(45),      -- IP de origen
    fecha_cambio                TIMESTAMP,        -- CURRENT_TIMESTAMP
    revision_manual_id          INTEGER,          -- FK → revision_manual_prestamos
    estado_revision_en_momento  VARCHAR(20),      -- Estado al momento del cambio
    observaciones               TEXT              -- Notas adicionales
);
```

**Índices**:
- `idx_auditoria_prestamo_id` → Búsquedas por préstamo (RÁPIDO)
- `idx_auditoria_fecha` → Búsquedas por fecha (DESC)
- `idx_auditoria_usuario` → Búsquedas por usuario
- `idx_auditoria_prestamo_fecha` → Compuesto (preferido)

---

### **2. `sesion_revision_manual`** (OPCIONAL PERO RECOMENDADA)

**Propósito**: Registrar sesiones de edición completas

**Estructura**:
```sql
CREATE TABLE public.sesion_revision_manual (
    id                  SERIAL PRIMARY KEY,
    usuario_email       VARCHAR(255) NOT NULL,
    usuario_id          INTEGER,
    prestamo_id         INTEGER NOT NULL (FK),
    fecha_inicio        TIMESTAMP,
    fecha_fin           TIMESTAMP,
    duracion_minutos    NUMERIC(10, 2),
    ip_address          VARCHAR(45),
    navegador           VARCHAR(255),
    dispositivo         VARCHAR(100),
    estado_final        VARCHAR(20),      -- 'revisando','revisado','cancelado'
    cambios_totales     INTEGER
);
```

---

## 📊 VISTAS CREADAS

### **Vista 1: `v_auditoria_revision_prestamo`**

Muestra auditoría formateada y legible:

```sql
SELECT 
    cambio_id,
    prestamo_id,
    cedula,
    nombres,
    tipo_cambio,          -- cliente/prestamo/cuota
    campo_modificado,     -- nombres/telefono/total_financiamiento/etc
    valor_anterior,       -- valor viejo
    valor_nuevo,          -- valor nuevo
    usuario_email,        -- quién
    fecha_cambio,         -- cuándo
    estado_revision,      -- estado en ese momento
    operacion             -- CREADO/MODIFICADO/ELIMINADO
FROM v_auditoria_revision_prestamo
ORDER BY fecha_cambio DESC;
```

### **Vista 2: `v_auditoria_usuario`**

Estadísticas de cambios por usuario:

```sql
SELECT 
    usuario_email,
    total_cambios,
    prestamos_modificados,
    primer_cambio,
    ultimo_cambio,
    tipos_cambios
FROM v_auditoria_usuario
ORDER BY total_cambios DESC;
```

---

## 🔧 FUNCIONES SQL CREADAS

### **Función 1: `fn_registrar_cambio_revision_manual()`**

Registra un cambio automáticamente:

```sql
SELECT public.fn_registrar_cambio_revision_manual(
    p_prestamo_id := 1,
    p_cliente_id := 1,
    p_cuota_id := NULL,
    p_tipo_cambio := 'cliente',
    p_tabla_afectada := 'clientes',
    p_campo_modificado := 'nombres',
    p_valor_anterior := 'Juan García',
    p_valor_nuevo := 'Juan García Pérez',
    p_usuario_email := 'admin@rapicredit.com',
    p_usuario_id := 1,
    p_revision_manual_id := 1,
    p_estado_revision := 'revisando',
    p_observaciones := 'Cambio de nombre'
);
```

**Retorna**: ID del registro de auditoría creado

### **Función 2: `fn_obtener_cambios_prestamo()`**

Obtiene todos los cambios de un préstamo:

```sql
SELECT * FROM public.fn_obtener_cambios_prestamo(1);

Retorna:
┌──────────┬──────────────┬──────────┬───────────┬──────────┬─────────────────┬──────────────┬────────────┐
│ cambio_id│ tipo_cambio  │ campo    │ anterior  │ nuevo    │ usuario         │ fecha        │ operacion  │
├──────────┼──────────────┼──────────┼───────────┼──────────┼─────────────────┼──────────────┼────────────┤
│ 3        │ cliente      │ nombres  │ Juan      │ Juan Pz  │ admin@...       │ 2026-02-20   │ MODIFICADO │
│ 2        │ prestamo     │ total    │ 1000.00   │ 1050.00  │ admin@...       │ 2026-02-20   │ MODIFICADO │
│ 1        │ cuota        │ estado   │ pendiente │ pagado   │ admin@...       │ 2026-02-20   │ MODIFICADO │
└──────────┴──────────────┴──────────┴───────────┴──────────┴─────────────────┴──────────────┴────────────┘
```

### **Función 3: `fn_resumen_cambios_revision()`**

Resumen ejecutivo de cambios:

```sql
SELECT * FROM public.fn_resumen_cambios_revision(1);

Retorna:
┌───────────────┬─────────────────┬──────────────────┬────────────────┬──────────────────────┬─────────────┬──────────────┐
│ total_cambios │ cambios_cliente │ cambios_prestamo │ cambios_cuotas │ usuarios_modificadores   │ primer_cambio  │ ultimo_cambio  │
├───────────────┼─────────────────┼──────────────────┼────────────────┼──────────────────────┼─────────────┼──────────────┤
│ 15            │ 3               │ 5                │ 7              │ {admin@...}          │ 2026-02-20  │ 2026-02-20   │
└───────────────┴─────────────────┴──────────────────┴────────────────┴──────────────────────┴─────────────┴──────────────┘
```

---

## 🔄 CÓMO SE INTEGRA CON EL FRONTEND

### **Desde EditarRevisionManual.tsx**

Cuando se guarda un cambio, el backend debe llamar a la función:

```python
# Backend (revision_manual.py)
def editar_cliente_revision(...):
    # 1. Guardar cambio en tabla clientes
    cliente.nombres = update_data.nombres
    db.commit()
    
    # 2. Registrar en auditoría
    db.execute(text("""
        SELECT public.fn_registrar_cambio_revision_manual(
            :prestamo_id, :cliente_id, NULL,
            'cliente', 'clientes', 'nombres',
            :valor_anterior, :valor_nuevo,
            :usuario_email, :usuario_id, :revision_id,
            :estado_revision, :observaciones
        )
    """), {
        'prestamo_id': prestamo_id,
        'cliente_id': cliente_id,
        'valor_anterior': cliente_viejo.nombres,
        'valor_nuevo': cliente.nombres,
        'usuario_email': current_user['email'],
        'usuario_id': current_user['id'],
        'revision_id': rev_manual.id,
        'estado_revision': rev_manual.estado_revision,
        'observaciones': f"Cambio parcial: {type(cambio).__name__}"
    })
    
    return {"mensaje": "Guardado + auditado"}
```

---

## 📈 QUERIES ÚTILES

### **Ver todos los cambios de un préstamo**
```sql
SELECT 
    id as cambio_id,
    tipo_cambio,
    campo_modificado,
    valor_anterior,
    valor_nuevo,
    usuario_email,
    fecha_cambio
FROM public.auditoria_revision_manual
WHERE prestamo_id = 1
ORDER BY fecha_cambio DESC;
```

### **Ver cambios últimas 24 horas**
```sql
SELECT 
    prestamo_id,
    usuario_email,
    tipo_cambio,
    campo_modificado,
    fecha_cambio
FROM public.auditoria_revision_manual
WHERE fecha_cambio >= NOW() - INTERVAL '24 hours'
ORDER BY fecha_cambio DESC;
```

### **Ver cambios por usuario**
```sql
SELECT 
    usuario_email,
    COUNT(*) as total_cambios,
    COUNT(DISTINCT prestamo_id) as prestamos_tocados,
    MIN(fecha_cambio) as primer_cambio,
    MAX(fecha_cambio) as ultimo_cambio
FROM public.auditoria_revision_manual
GROUP BY usuario_email
ORDER BY total_cambios DESC;
```

### **Ver cambios en formato JSON**
```sql
SELECT 
    prestamo_id,
    json_agg(json_build_object(
        'campo', campo_modificado,
        'anterior', valor_anterior,
        'nuevo', valor_nuevo,
        'usuario', usuario_email,
        'fecha', fecha_cambio,
        'tipo', tipo_cambio
    ) ORDER BY fecha_cambio DESC) as cambios
FROM public.auditoria_revision_manual
WHERE prestamo_id = 1
GROUP BY prestamo_id;
```

### **Comparar antes/después**
```sql
SELECT 
    campo_modificado,
    valor_anterior,
    valor_nuevo,
    usuario_email,
    TO_CHAR(fecha_cambio, 'YYYY-MM-DD HH:MI:SS') as fecha
FROM public.auditoria_revision_manual
WHERE prestamo_id = 1 AND tipo_cambio = 'cliente'
ORDER BY fecha_cambio DESC;
```

---

## 📊 EJEMPLO DE REGISTRO

### Cuando edita un cliente:

```
ID: 1
prestamo_id: 1
cliente_id: 1
cuota_id: NULL
tipo_cambio: 'cliente'
tabla_afectada: 'clientes'
campo_modificado: 'nombres'
valor_anterior: 'Juan García'
valor_nuevo: 'Juan García Pérez'
usuario_email: 'admin@rapicredit.com'
usuario_id: 1
fecha_cambio: 2026-02-20 14:30:45
revision_manual_id: 1
estado_revision_en_momento: 'revisando'
observaciones: 'Corrección de nombre'
```

### Cuando edita un préstamo:

```
ID: 2
prestamo_id: 1
cliente_id: NULL
cuota_id: NULL
tipo_cambio: 'prestamo'
tabla_afectada: 'prestamos'
campo_modificado: 'total_financiamiento'
valor_anterior: '1000.00'
valor_nuevo: '1050.00'
usuario_email: 'admin@rapicredit.com'
usuario_id: 1
fecha_cambio: 2026-02-20 14:31:15
revision_manual_id: 1
estado_revision_en_momento: 'revisando'
observaciones: 'Ajuste de total'
```

### Cuando edita una cuota:

```
ID: 3
prestamo_id: 1
cliente_id: NULL
cuota_id: 5
tipo_cambio: 'cuota'
tabla_afectada: 'cuotas'
campo_modificado: 'fecha_pago'
valor_anterior: '2026-03-01'
valor_nuevo: '2026-03-15'
usuario_email: 'admin@rapicredit.com'
usuario_id: 1
fecha_cambio: 2026-02-20 14:32:00
revision_manual_id: 1
estado_revision_en_momento: 'revisando'
observaciones: 'Reprogramación de pago'
```

---

## ✅ BENEFICIOS

✅ **Trazabilidad completa**: Quién, qué, cuándo, dónde
✅ **Antes/Después**: Compara valores antiguos vs nuevos
✅ **Por préstamo**: Todos los cambios de un préstamo en una query
✅ **Por usuario**: Auditoría de actividad de usuarios
✅ **Timestamps**: Registro preciso de cada momento
✅ **Reversión**: Puedes reconstruir estados anteriores
✅ **Análisis**: Queries complejas para reportes
✅ **Cumplimiento**: Auditoría para regulaciones

---

## 📋 Checklist de Implementación

- ✅ Tabla `auditoria_revision_manual` creada
- ✅ Tabla `sesion_revision_manual` opcional
- ✅ Índices creados (8 índices)
- ✅ Vistas creadas (2 vistas)
- ✅ Funciones SQL creadas (3 funciones)
- ✅ Foreign keys configuradas
- ✅ Comentarios y documentación
- ✅ Queries de ejemplo

---

## 🚀 Cómo Usar

### 1. Crear las tablas (ejecutar SQL)
```bash
psql -U usuario -d base_datos -f auditoria_revision_manual.sql
```

### 2. Desde Backend Python
```python
# Registrar cambio
db.execute(text("""
    SELECT public.fn_registrar_cambio_revision_manual(...)
"""))
```

### 3. Consultar desde Backend
```python
# Obtener cambios
cambios = db.execute(text("""
    SELECT * FROM public.fn_obtener_cambios_prestamo(:id)
"""), {"id": prestamo_id}).fetchall()
```

### 4. Desde Frontend
```typescript
// Obtener cambios de un préstamo
GET /api/v1/revision-manual/prestamos/{id}/auditoria
```

---

## 📄 Archivo SQL

El archivo completo está en:
```
backend/sql/auditoria_revision_manual.sql
```

Contiene:
- Tablas con comentarios
- Índices optimizados
- Vistas con JOINS
- Funciones reutilizables
- Queries de ejemplo

---

Documento: TABLA_AUDITORIA_REVISION_MANUAL.md  
Fecha: 2026-02-20  
Estado: ✅ Implementado (SQL listo para ejecutar)
