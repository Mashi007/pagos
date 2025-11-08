# 🔍 Revisión Integral: Conexiones a Tablas del Módulo Cobranzas

**Fecha:** 2025-11-XX  
**Módulo:** Cobranzas  
**Objetivo:** Documentar todas las tablas a las que está conectado el módulo de cobranzas

---

## 📋 Resumen Ejecutivo

El módulo de cobranzas está conectado a **5 tablas principales** de la base de datos, con múltiples relaciones y JOINs para obtener información consolidada sobre cuotas vencidas, clientes atrasados y análisis de mora.

---

## 🗄️ Tablas Conectadas

### 1. ✅ **Tabla: `cuotas`** (PRINCIPAL)

**Modelo:** `app.models.amortizacion.Cuota`  
**Tabla BD:** `cuotas`  
**Uso:** Tabla principal para determinar cuotas vencidas y calcular mora

#### Campos Utilizados:

| Campo | Tipo | Uso en Cobranzas |
|-------|------|------------------|
| `id` | INTEGER (PK) | Identificación única de cuota |
| `prestamo_id` | INTEGER (FK) | JOIN con tabla `prestamos` |
| `numero_cuota` | INTEGER | Identificación de número de cuota |
| `fecha_vencimiento` | DATE | **CRÍTICO:** Filtro principal para cuotas vencidas |
| `fecha_pago` | DATE | Fecha real de pago (si existe) |
| `monto_cuota` | NUMERIC(12,2) | **CRÍTICO:** Comparación con `total_pagado` |
| `monto_capital` | NUMERIC(12,2) | Información de capital |
| `monto_interes` | NUMERIC(12,2) | Información de interés |
| `total_pagado` | NUMERIC(12,2) | **CRÍTICO:** Criterio para determinar si está pagada |
| `capital_pagado` | NUMERIC(12,2) | Capital ya pagado |
| `interes_pagado` | NUMERIC(12,2) | Interés ya pagado |
| `mora_pagada` | NUMERIC(12,2) | Mora ya pagada |
| `estado` | VARCHAR(20) | Estado de la cuota (PENDIENTE, PAGADO, ATRASADO, etc.) |
| `dias_mora` | INTEGER | Días de mora acumulados |
| `monto_mora` | NUMERIC(12,2) | Monto de mora calculado |

#### Criterio de Cuota Vencida (UNIFICADO):

```python
# ✅ CRITERIO CORRECTO para cuota vencida:
Cuota.fecha_vencimiento < hoy AND Cuota.total_pagado < Cuota.monto_cuota
```

**Razón:** Una cuota está vencida si:
1. La fecha de vencimiento ya pasó (`fecha_vencimiento < hoy`)
2. El pago está incompleto (`total_pagado < monto_cuota`)

#### Endpoints que Usan Esta Tabla:

- ✅ `/api/v1/cobranzas/health` - Healthcheck
- ✅ `/api/v1/cobranzas/clientes-atrasados` - Lista de clientes atrasados
- ✅ `/api/v1/cobranzas/clientes-por-cantidad-pagos` - Filtro por cantidad
- ✅ `/api/v1/cobranzas/por-analista` - Estadísticas por analista
- ✅ `/api/v1/cobranzas/por-analista/{analista}/clientes` - Clientes de analista
- ✅ `/api/v1/cobranzas/montos-por-mes` - Montos vencidos por mes
- ✅ `/api/v1/cobranzas/resumen` - Resumen general
- ✅ `/api/v1/cobranzas/informes/clientes-atrasados` - Informe completo
- ✅ `/api/v1/cobranzas/informes/rendimiento-analista` - Rendimiento por analista
- ✅ `/api/v1/cobranzas/informes/montos-vencidos-periodo` - Montos por período
- ✅ `/api/v1/cobranzas/informes/por-categoria-dias` - Categorías de días
- ✅ `/api/v1/cobranzas/informes/antiguedad-saldos` - Antigüedad de saldos
- ✅ `/api/v1/cobranzas/informes/resumen-ejecutivo` - Resumen ejecutivo

**Total:** 13 endpoints utilizan esta tabla

---

### 2. ✅ **Tabla: `prestamos`** (SECUNDARIA - JOIN)

**Modelo:** `app.models.prestamo.Prestamo`  
**Tabla BD:** `prestamos`  
**Uso:** Información de préstamos y filtros por estado/analista

#### Campos Utilizados:

| Campo | Tipo | Uso en Cobranzas |
|-------|------|------------------|
| `id` | INTEGER (PK) | JOIN con `cuotas.prestamo_id` |
| `cliente_id` | INTEGER (FK) | Relación con `clientes` |
| `cedula` | VARCHAR(20) | JOIN con `clientes.cedula` |
| `nombres` | VARCHAR(100) | Información del cliente |
| `total_financiamiento` | NUMERIC(15,2) | Monto total del préstamo |
| `estado` | VARCHAR(20) | **CRÍTICO:** Filtro `estado IN ('APROBADO', 'ACTIVO')` |
| `usuario_proponente` | VARCHAR(100) | **CRÍTICO:** Filtro por analista y exclusión de admin |
| `fecha_registro` | TIMESTAMP | Fecha de creación |
| `fecha_aprobacion` | TIMESTAMP | Fecha de aprobación |

#### Filtros Aplicados:

```python
# Solo préstamos aprobados o activos
Prestamo.estado.in_(["APROBADO", "ACTIVO"])

# Excluir admin
Prestamo.usuario_proponente != settings.ADMIN_EMAIL
```

#### Relaciones:

- **JOIN con `cuotas`:** `Cuota.prestamo_id = Prestamo.id`
- **JOIN con `clientes`:** `Prestamo.cedula = Cliente.cedula`
- **JOIN con `users`:** `User.email = Prestamo.usuario_proponente`

#### Endpoints que Usan Esta Tabla:

- ✅ Todos los endpoints de cobranzas (13 endpoints)
- ✅ Usado en todos los JOINs para obtener información de préstamos

---

### 3. ✅ **Tabla: `clientes`** (SECUNDARIA - JOIN)

**Modelo:** `app.models.cliente.Cliente`  
**Tabla BD:** `clientes`  
**Uso:** Información de clientes atrasados

#### Campos Utilizados:

| Campo | Tipo | Uso en Cobranzas |
|-------|------|------------------|
| `id` | INTEGER (PK) | Relación con `prestamos.cliente_id` |
| `cedula` | VARCHAR(20) | **CRÍTICO:** JOIN con `prestamos.cedula` |
| `nombres` | VARCHAR(100) | Información del cliente |
| `telefono` | VARCHAR(15) | Contacto del cliente |
| `email` | VARCHAR(100) | Contacto del cliente |
| `estado` | VARCHAR(20) | Estado del cliente (ACTIVO, INACTIVO, FINALIZADO) |
| `activo` | BOOLEAN | Estado activo del cliente |

#### Relaciones:

- **JOIN con `prestamos`:** `Prestamo.cedula = Cliente.cedula`
- **Relación inversa:** `Cliente.prestamos` (backref desde Prestamo)

#### Endpoints que Usan Esta Tabla:

- ✅ `/api/v1/cobranzas/clientes-atrasados`
- ✅ `/api/v1/cobranzas/por-analista/{analista}/clientes`
- ✅ `/api/v1/cobranzas/informes/clientes-atrasados`
- ✅ `/api/v1/cobranzas/informes/rendimiento-analista`
- ✅ `/api/v1/cobranzas/informes/montos-vencidos-periodo`
- ✅ `/api/v1/cobranzas/informes/por-categoria-dias`
- ✅ `/api/v1/cobranzas/informes/antiguedad-saldos`
- ✅ `/api/v1/cobranzas/informes/resumen-ejecutivo`

**Total:** 8 endpoints utilizan esta tabla

---

### 4. ✅ **Tabla: `users`** (SECUNDARIA - JOIN OPCIONAL)

**Modelo:** `app.models.user.User`  
**Tabla BD:** `users`  
**Uso:** Filtrar y excluir usuarios administradores

#### Campos Utilizados:

| Campo | Tipo | Uso en Cobranzas |
|-------|------|------------------|
| `id` | INTEGER (PK) | Identificación de usuario |
| `email` | VARCHAR(100) | **CRÍTICO:** JOIN con `prestamos.usuario_proponente` |
| `is_admin` | BOOLEAN | **CRÍTICO:** Filtro para excluir admins |

#### Filtros Aplicados:

```python
# Excluir usuarios administradores
.outerjoin(User, User.email == Prestamo.usuario_proponente)
.filter(
    or_(User.is_admin.is_(False), User.is_admin.is_(None))
)
```

**Nota:** Se usa `outerjoin` porque no todos los préstamos tienen un usuario asociado en la tabla `users`.

#### Endpoints que Usan Esta Tabla:

- ✅ `/api/v1/cobranzas/clientes-atrasados`
- ✅ `/api/v1/cobranzas/por-analista`
- ✅ `/api/v1/cobranzas/por-analista/{analista}/clientes`
- ✅ `/api/v1/cobranzas/resumen`
- ✅ `/api/v1/cobranzas/informes/clientes-atrasados`
- ✅ `/api/v1/cobranzas/informes/rendimiento-analista`
- ✅ `/api/v1/cobranzas/informes/por-categoria-dias`
- ✅ `/api/v1/cobranzas/informes/resumen-ejecutivo`

**Total:** 8 endpoints utilizan esta tabla

---

### 5. ✅ **Tabla: `auditoria`** (SECUNDARIA - ESCRITURA)

**Modelo:** `app.models.auditoria.Auditoria`  
**Tabla BD:** `auditoria`  
**Uso:** Registrar exportaciones de informes (Excel/PDF)

#### Campos Utilizados:

| Campo | Tipo | Uso en Cobranzas |
|-------|------|------------------|
| `id` | INTEGER (PK) | Identificación única |
| `usuario_id` | INTEGER (FK) | Usuario que exportó |
| `accion` | VARCHAR(50) | Valor: `"EXPORT"` |
| `entidad` | VARCHAR(50) | Valor: `"COBRANZAS"` |
| `entidad_id` | INTEGER | NULL (no aplica) |
| `detalles` | TEXT | Descripción del informe exportado |
| `exito` | BOOLEAN | `True` si se exportó correctamente |
| `fecha_registro` | TIMESTAMP | Fecha de exportación |

#### Endpoints que Usan Esta Tabla:

- ✅ `/api/v1/cobranzas/informes/resumen-ejecutivo` (solo en formato Excel/PDF)

**Total:** 1 endpoint utiliza esta tabla (solo escritura)

---

## 🔗 Diagrama de Relaciones

```
┌─────────────┐
│   clientes  │
│             │
│  id (PK)    │
│  cedula     │◄──────┐
│  nombres    │       │
│  telefono   │       │
└─────────────┘       │
                      │
                      │ JOIN por cedula
                      │
┌─────────────┐       │
│  prestamos  │       │
│             │       │
│  id (PK)    │◄──────┼──┐
│  cliente_id │       │  │
│  cedula     │───────┘  │
│  estado     │          │
│  usuario_   │          │
│  proponente │          │
└─────────────┘          │
                         │
                         │ JOIN por prestamo_id
                         │
┌─────────────┐          │
│   cuotas    │          │
│             │          │
│  id (PK)    │          │
│  prestamo_id│──────────┘
│  fecha_     │
│  vencimiento│
│  monto_cuota│
│  total_     │
│  pagado     │
└─────────────┘

┌─────────────┐
│    users    │
│             │
│  id (PK)    │
│  email      │◄──────┐
│  is_admin   │       │
└─────────────┘       │
                      │
                      │ OUTER JOIN por email
                      │
┌─────────────┐       │
│  prestamos  │       │
│             │       │
│  usuario_   │───────┘
│  proponente │
└─────────────┘
```

---

## 📊 Resumen de Conexiones por Endpoint

| Endpoint | Tablas Utilizadas | Tipo de Operación |
|----------|-------------------|-------------------|
| `/health` | `cuotas` | Lectura |
| `/clientes-atrasados` | `cuotas`, `prestamos`, `clientes`, `users` | Lectura |
| `/clientes-por-cantidad-pagos` | `cuotas`, `prestamos`, `clientes` | Lectura |
| `/por-analista` | `cuotas`, `prestamos`, `clientes`, `users` | Lectura |
| `/por-analista/{analista}/clientes` | `cuotas`, `prestamos`, `clientes` | Lectura |
| `/montos-por-mes` | `cuotas` | Lectura |
| `/resumen` | `cuotas`, `prestamos`, `clientes`, `users` | Lectura |
| `/informes/clientes-atrasados` | `cuotas`, `prestamos`, `clientes`, `users` | Lectura |
| `/informes/rendimiento-analista` | `cuotas`, `prestamos`, `clientes`, `users` | Lectura |
| `/informes/montos-vencidos-periodo` | `cuotas`, `prestamos`, `clientes` | Lectura |
| `/informes/por-categoria-dias` | `cuotas`, `prestamos`, `clientes`, `users` | Lectura |
| `/informes/antiguedad-saldos` | `cuotas`, `prestamos`, `clientes` | Lectura |
| `/informes/resumen-ejecutivo` | `cuotas`, `prestamos`, `clientes`, `users`, `auditoria` | Lectura + Escritura |

---

## 🔍 Consultas SQL Típicas

### Consulta Base para Clientes Atrasados:

```sql
SELECT 
    c.cedula,
    c.nombres,
    c.telefono,
    p.usuario_proponente AS analista,
    p.id AS prestamo_id,
    COUNT(cu.id) AS cuotas_vencidas,
    SUM(cu.monto_cuota) AS total_adeudado,
    MIN(cu.fecha_vencimiento) AS fecha_primera_vencida
FROM cuotas cu
JOIN prestamos p ON cu.prestamo_id = p.id
JOIN clientes c ON p.cedula = c.cedula
LEFT OUTER JOIN users u ON u.email = p.usuario_proponente
WHERE 
    cu.fecha_vencimiento < CURRENT_DATE
    AND cu.total_pagado < cu.monto_cuota
    AND p.estado IN ('APROBADO', 'ACTIVO')
    AND p.usuario_proponente != 'admin@example.com'
    AND (u.is_admin = FALSE OR u.is_admin IS NULL)
GROUP BY 
    c.cedula, c.nombres, c.telefono, p.usuario_proponente, p.id
```

### Consulta para Resumen General:

```sql
SELECT 
    COUNT(cu.id) AS total_cuotas_vencidas,
    SUM(cu.monto_cuota) AS monto_total_adeudado,
    COUNT(DISTINCT p.cedula) AS clientes_atrasados
FROM cuotas cu
JOIN prestamos p ON cu.prestamo_id = p.id
LEFT OUTER JOIN users u ON u.email = p.usuario_proponente
WHERE 
    cu.fecha_vencimiento < CURRENT_DATE
    AND cu.total_pagado < cu.monto_cuota
    AND p.estado IN ('APROBADO', 'ACTIVO')
    AND p.usuario_proponente != 'admin@example.com'
    AND (u.is_admin = FALSE OR u.is_admin IS NULL)
```

---

## ⚠️ Consideraciones Importantes

### 1. **Criterio Unificado de Cuotas Vencidas**

**✅ CORRECTO:**
```python
Cuota.fecha_vencimiento < hoy AND Cuota.total_pagado < Cuota.monto_cuota
```

**❌ INCORRECTO (no usar):**
```python
Cuota.estado != "PAGADO"  # Puede incluir cuotas pagadas pero no conciliadas
```

### 2. **Filtro de Estados de Préstamos**

Solo se consideran préstamos con estado:
- `APROBADO`
- `ACTIVO`

Se excluyen:
- `DRAFT`
- `RECHAZADO`
- `FINALIZADO`

### 3. **Exclusión de Administradores**

Se excluyen préstamos del admin usando dos métodos:
1. Comparación directa: `Prestamo.usuario_proponente != settings.ADMIN_EMAIL`
2. Verificación en tabla users: `User.is_admin = False OR User.is_admin IS NULL`

### 4. **JOINs Optimizados**

- Se usa `outerjoin` para `users` porque no todos los préstamos tienen usuario asociado
- Se usa `join` para `prestamos` y `clientes` porque son relaciones obligatorias
- Se agrupan cuotas vencidas en subqueries para optimizar rendimiento

---

## 📈 Índices Recomendados

Para optimizar las consultas de cobranzas, se recomiendan los siguientes índices:

### Tabla `cuotas`:
- ✅ `fecha_vencimiento` (ya indexado)
- ✅ `prestamo_id` (ya indexado)
- ✅ `estado` (ya indexado)
- ⚠️ **Recomendado:** Índice compuesto `(fecha_vencimiento, total_pagado, monto_cuota)`

### Tabla `prestamos`:
- ✅ `id` (ya indexado)
- ✅ `cedula` (ya indexado)
- ✅ `estado` (ya indexado)
- ✅ `fecha_registro` (ya indexado)
- ⚠️ **Recomendado:** Índice compuesto `(estado, usuario_proponente)`

### Tabla `clientes`:
- ✅ `id` (ya indexado)
- ✅ `cedula` (ya indexado)
- ✅ `telefono` (ya indexado)
- ✅ `email` (ya indexado)
- ✅ `estado` (ya indexado)
- ✅ `activo` (ya indexado)

---

## ✅ Checklist de Verificación

- [x] Tabla `cuotas` identificada y documentada
- [x] Tabla `prestamos` identificada y documentada
- [x] Tabla `clientes` identificada y documentada
- [x] Tabla `users` identificada y documentada
- [x] Tabla `auditoria` identificada y documentada
- [x] Criterio de cuotas vencidas unificado
- [x] Filtros de estados documentados
- [x] Relaciones entre tablas documentadas
- [x] Consultas SQL de ejemplo proporcionadas
- [x] Índices recomendados documentados

---

## 📝 Notas Finales

1. **Total de Tablas:** 5 tablas conectadas
2. **Tabla Principal:** `cuotas` (usada en todos los endpoints)
3. **Tablas Secundarias:** `prestamos`, `clientes`, `users` (usadas en JOINs)
4. **Tabla de Auditoría:** `auditoria` (solo escritura en exportaciones)

5. **Criterio Crítico:** El módulo usa el criterio unificado `fecha_vencimiento < hoy AND total_pagado < monto_cuota` para determinar cuotas vencidas, asegurando consistencia con otros módulos del sistema.

---

**Última actualización:** 2025-11-XX  
**Revisado por:** Sistema de Auditoría Automática

