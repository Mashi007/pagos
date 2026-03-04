# 📋 INVENTARIO COMPLETO DE ENDPOINTS - RAPICREDIT API

## 📊 RESUMEN GENERAL

```
Total de módulos: 28
Total de routers incluidos: 21
Total de endpoints (estimado): 150+
Status: OPERATIVO pero REQUIERE LIMPIEZA
```

---

## 🎯 ENDPOINTS POR CATEGORÍA

### 1️⃣ HEALTH & SYSTEM (4 Endpoints)

| Método | Ruta | Auth | Status | Descripción |
|--------|------|------|--------|------------|
| GET | `/` | No | ✓ | Root - Info proyecto |
| HEAD | `/` | No | ✓ | Root HEAD check |
| GET | `/health` | No | ✓ | Health check basico |
| HEAD | `/health` | No | ✓ | Health HEAD check |
| GET | `/health/db` | No | ✓ | Database health check |
| POST | `/api/admin/run-migration-auditoria-fk` | Secret | ✓ | Migración auditoria (ONE-TIME) |

---

### 2️⃣ AUTHENTICATION (3 Endpoints)

| Método | Ruta | Auth | Status | Descripción |
|--------|------|------|--------|------------|
| POST | `/auth/login` | No | ✓ | Login usuario |
| POST | `/auth/refresh` | Bearer | ✓ | Refresh token |
| GET | `/auth/me` | Bearer | ✓ | Info usuario actual |

---

### 3️⃣ CLIENTES (8 Endpoints) ⭐ CRÍTICOS

| Método | Ruta | Auth | Status | Descripción |
|--------|------|------|--------|------------|
| GET | `/clientes` | Bearer | ✓ | Listar clientes (paginado) |
| GET | `/clientes/{cliente_id}` | Bearer | ✓ | Get cliente by ID |
| POST | `/clientes` | Bearer | ✓ | Crear cliente |
| PUT | `/clientes/{cliente_id}` | Bearer | ✓ | Actualizar cliente |
| DELETE | `/clientes/{cliente_id}` | Bearer | ✓ | Eliminar cliente |
| **POST** | **`/clientes/upload-excel`** | Bearer | ✅ **NUEVO** | **Carga masiva clientes** |
| GET | `/clientes/revisar/lista` | Bearer | ✅ **NUEVO** | Listar clientes con errores |
| DELETE | `/clientes/revisar/{error_id}` | Bearer | ✅ **NUEVO** | Resolver error cliente |

---

### 4️⃣ PAGOS (8 Endpoints) ⭐ CRÍTICOS

| Método | Ruta | Auth | Status | Descripción |
|--------|------|------|--------|------------|
| GET | `/pagos` | Bearer | ✓ | Listar pagos (paginado) |
| GET | `/pagos/{pago_id}` | Bearer | ✓ | Get pago by ID |
| POST | `/pagos` | Bearer | ✓ | Crear pago individual |
| PUT | `/pagos/{pago_id}` | Bearer | ✓ | Actualizar pago |
| **POST** | **`/pagos/upload-excel`** | Bearer | ✓ | **Carga masiva pagos** |
| GET | `/pagos/con-errores` | Bearer | ✓ | **GET /pagos/con-errores/lista** |
| GET | `/pagos/revisar/lista` | Bearer | ✓ | Listar pagos con errores |
| DELETE | `/pagos/revisar/{error_id}` | Bearer | ✓ | Resolver error pago |

---

### 5️⃣ PRÉSTAMOS (9 Endpoints) ⭐ CRÍTICOS

| Método | Ruta | Auth | Status | Descripción |
|--------|------|------|--------|------------|
| GET | `/prestamos` | Bearer | ✓ | Listar préstamos (paginado) |
| GET | `/prestamos/{prestamo_id}` | Bearer | ✓ | Get préstamo by ID |
| POST | `/prestamos` | Bearer | ✓ | Crear préstamo |
| PUT | `/prestamos/{prestamo_id}` | Bearer | ✓ | Actualizar préstamo |
| DELETE | `/prestamos/{prestamo_id}` | Bearer | ✓ | Eliminar préstamo |
| **POST** | **`/prestamos/upload-excel`** | Bearer | ✅ **NUEVO** | **Carga masiva préstamos** |
| GET | `/prestamos/{prestamo_id}/cuotas` | Bearer | ✓ | Listar cuotas del préstamo |
| GET | `/prestamos/revisar/lista` | Bearer | ✅ **NUEVO** | Listar préstamos con errores |
| DELETE | `/prestamos/revisar/{error_id}` | Bearer | ✅ **NUEVO** | Resolver error préstamo |

---

### 6️⃣ DASHBOARD & KPIs (6 Endpoints)

| Método | Ruta | Auth | Status | Descripción |
|--------|------|------|--------|------------|
| GET | `/dashboard/opciones-filtros` | Bearer | ⚠️ | Filtros disponibles |
| GET | `/dashboard/kpis-principales` | Bearer | ⚠️ | KPIs del dashboard |
| GET | `/dashboard/admin` | Bearer | ⚠️ | Dashboard admin |
| GET | `/kpis/dashboard` | Bearer | ⚠️ | KPIs generales |
| GET | `/kpis/cartera` | Bearer | ⚠️ | KPIs cartera |
| GET | `/kpis/morosidad` | Bearer | ⚠️ | KPIs morosidad |

---

### 7️⃣ REPORTES (10+ Endpoints)

| Módulo | Rutas | Status | Descripción |
|--------|-------|--------|------------|
| Dashboard | `/reportes/dashboard/*` | ⚠️ | Reportes dashboard |
| Cedula | `/reportes/cedula/*` | ⚠️ | Reportes por cédula |
| Cliente | `/reportes/cliente/*` | ⚠️ | Reportes por cliente |
| Pagos | `/reportes/pagos/*` | ⚠️ | Reportes pagos |
| Cartera | `/reportes/cartera/*` | ⚠️ | Reportes cartera |
| Morosidad | `/reportes/morosidad/*` | ⚠️ | Reportes morosidad |
| Financiero | `/reportes/financiero/*` | ⚠️ | Reportes financieros |
| Conciliación | `/reportes/conciliacion/*` | ⚠️ | Reportes conciliación |
| Productos | `/reportes/productos/*` | ⚠️ | Reportes productos |
| Asesores | `/reportes/asesores/*` | ⚠️ | Reportes asesores |

---

### 8️⃣ CONFIGURACIÓN (5 Endpoints)

| Método | Ruta | Auth | Status | Descripción |
|--------|------|------|--------|------------|
| GET | `/configuracion` | Bearer | ✓ | Get config general |
| PUT | `/configuracion` | Bearer | ✓ | Update config |
| POST | `/configuracion/upload-logo` | Bearer | ✓ | Upload logo |
| GET | `/configuracion/logo/{filename}` | No | ✓ | Get logo público |
| GET | `/configuracion/informe-pagos/callback` | No | ✓ | Google OAuth callback |

---

### 9️⃣ VALIDADORES (5 Endpoints)

| Método | Ruta | Auth | Status | Descripción |
|--------|------|------|--------|------------|
| GET | `/validadores/cedula` | Bearer | ✓ | Validar cédula |
| GET | `/validadores/email` | Bearer | ✓ | Validar email |
| GET | `/validadores/telefono` | Bearer | ✓ | Validar teléfono |
| GET | `/validadores/fecha` | Bearer | ✓ | Validar fecha |
| POST | `/validadores/cedula` | Bearer | ✓ | Validar batch de cédulas |

---

### 🔟 NOTIFICACIONES (10+ Endpoints)

| Módulo | Rutas | Status | Descripción |
|--------|-------|--------|------------|
| General | `/notificaciones/*` | ⚠️ | Estadísticas, actualizar |
| Previas | `/notificaciones-previas/*` | ⚠️ | Notificaciones previas |
| Día Pago | `/notificaciones-dia-pago/*` | ⚠️ | Notificaciones día pago |
| Retrasadas | `/notificaciones-retrasadas/*` | ⚠️ | Notificaciones retrasadas |
| Prejudicial | `/notificaciones-prejudicial/*` | ⚠️ | Notificaciones prejudicial |
| Mora 90 | `/notificaciones-mora-90/*` | ⚠️ | Notificaciones mora >90d |

---

### 1️⃣1️⃣ COMUNICACIONES (3 Endpoints)

| Método | Ruta | Auth | Status | Descripción |
|--------|------|------|--------|------------|
| GET | `/comunicaciones/email` | Bearer | ⚠️ | Config email |
| POST | `/comunicaciones/email/test` | Bearer | ⚠️ | Enviar email test |
| POST | `/comunicaciones/whatsapp/test` | Bearer | ⚠️ | Enviar WhatsApp test |

---

### 1️⃣2️⃣ AUDITORIA (4 Endpoints)

| Método | Ruta | Auth | Status | Descripción |
|--------|------|------|--------|------------|
| GET | `/auditoria` | Bearer | ⚠️ | Listar auditoría |
| GET | `/auditoria/stats` | Bearer | ⚠️ | Estadísticas |
| POST | `/auditoria/registrar` | Bearer | ⚠️ | Registrar evento |
| GET | `/auditoria/exportar` | Bearer | ⚠️ | Exportar log |

---

### 1️⃣3️⃣ OTROS MÓDULOS

| Módulo | Endpoints | Status |
|--------|-----------|--------|
| Usuarios | 3-5 | ⚠️ |
| Tickets | 5-10 | ⚠️ |
| Tickets New | 5-10 | ⚠️ (¿DUPLICADO?) |
| WhatsApp | 5+ | ⚠️ |
| Concesionarios | 3-5 | ⚠️ |
| Analistas | 3-5 | ⚠️ |
| Modelos Vehículos | 3-5 | ⚠️ |
| Revisión Manual | 5-10 | ⚠️ |
| AI Training | 5+ | ⚠️ |
| Cobranzas | 5+ | ⚠️ |

---

## ⚠️ PROBLEMAS IDENTIFICADOS

### 🔴 CRÍTICOS

```
1. DUPLICADOS:
   ├─ revision_manual.py aparece 2 veces (línea 31, 196)
   ├─ prestamos.py aparece 2 veces
   ├─ pagos.py aparece 2 veces
   ├─ clientes.py aparece 2 veces
   └─ tickets.py vs tickets_new.py (¿AMBOS ACTIVOS?)

2. ENDPOINTS SIN AUTENTICACIÓN:
   ├─ / (GET) - ✓ OK (info proyecto)
   ├─ /health (GET) - ✓ OK (monitoreo)
   ├─ /configuracion/logo/{filename} (GET) - ✓ OK (logo público)
   ├─ /configuracion/informe-pagos/callback (GET) - ✓ OK (OAuth)
   └─ PERO: /auth/login también sin auth - ✓ OK

3. ENDPOINTS INNECESARIOS:
   ├─ pagos_con_errores.py (router por separado)
   │  → Debería estar en pagos.py
   └─ tickets_new.py
      → ¿Por qué existe si ya hay tickets.py?

4. RUTAS CONFUSAS:
   ├─ /pagos/con-errores vs /pagos/revisar/lista
   │  (¿dos endpoints para lo mismo?)
   ├─ /configuracion/informe-pagos/callback
   │  (callback de Google, pero en configuración)
   └─ /api/admin/run-migration-auditoria-fk
      (endpoint admin mezclado en main.py)
```

### 🟡 ADVERTENCIAS

```
1. ENDPOINTS STUB (probablemente sin BD real):
   ├─ /dashboard/* (comentario dice "stub")
   ├─ /kpis/* (comentario dice "stub")
   ├─ /auditoria/* (comentario dice "stub")
   ├─ /notificaciones/* (muy complejos, probablemente incompletos)
   └─ /ai/training/* (ML, probablemente sin datos)

2. RUTAS MAL ORGANIZADAS:
   ├─ /notificaciones-previas (debería ser /notificaciones/previas)
   ├─ /notificaciones-dia-pago (debería ser /notificaciones/dia-pago)
   ├─ /notificaciones-retrasadas (debería ser /notificaciones/retrasadas)
   ├─ /notificaciones-mora-90 (debería ser /notificaciones/mora-90)
   └─ Esto causa 5 routers para una sola funcionalidad

3. FALTA DE DOCUMENTACIÓN:
   ├─ Muchos endpoints sin docstring
   ├─ Parámetros no documentados
   └─ Respuestas no claramente especificadas
```

---

## ✅ ENDPOINTS QUE ESTÁN BIEN

### Críticos (Operativos y Bien Implementados)

```
✓ /auth/* (login, refresh, me)
✓ /clientes/* (completo con CRUD y carga masiva)
✓ /pagos/* (completo con CRUD y carga masiva)
✓ /prestamos/* (completo con CRUD y carga masiva)
✓ /health/* (salud del sistema)
✓ /validadores/* (validaciones básicas)
✓ /configuracion/* (config general)
```

### Secundarios (Operativos)

```
✓ /tickets/* (CRM, conectado a BD)
✓ /usuarios/* (gestión usuarios)
✓ /concesionarios/* (lectura desde prestamos)
✓ /analistas/* (lectura desde prestamos)
✓ /modelos-vehiculos/* (lectura desde prestamos)
✓ /whatsapp/* (integración WhatsApp)
✓ /comunicaciones/* (email/WhatsApp)
```

---

## 🔧 RECOMENDACIONES DE LIMPIEZA

### Prioritarios (Hacer AHORA)

```
1. ELIMINAR DUPLICADOS:
   ├─ Remover revision_manual.py duplicado
   ├─ Verificar si tickets_new.py es necesario (vs tickets.py)
   └─ Consolidar rutas de notificaciones bajo /notificaciones/*

2. ORGANIZAR RUTAS:
   ├─ Mover /pagos/con-errores → /pagos/errores
   ├─ Mover /configuracion/informe-pagos/callback → /auth/google/callback
   ├─ Mover /api/admin/* → /admin/*
   └─ Rutas notificaciones: usar nesting /notificaciones/{tab}

3. DOCUMENTAR:
   ├─ Agregar docstrings a todos los endpoints
   ├─ Especificar parámetros y respuestas
   └─ Crear OpenAPI spec completa
```

### Secundarios (Próximas semanas)

```
1. REVISAR STUBS:
   ├─ /dashboard/* - ¿Realmente necesarios?
   ├─ /kpis/* - Consolidar con /dashboard
   ├─ /auditoria/* - Implementar completamente o eliminar
   └─ /ai/training/* - En desarrollo, marcar como beta

2. CONSOLIDAR:
   ├─ notificaciones_tabs.py → notificaciones.py
   ├─ 5 routers en 1 (con nesting)
   └─ Reducir complejidad de la API

3. DEPRECATE:
   ├─ Endpoints obsoletos (buscar status 501)
   └─ Migraciones one-time (run-migration-auditoria-fk)
```

---

## 📊 ESTADÍSTICAS

| Métrica | Valor |
|---------|-------|
| Total Routers | 21 |
| Endpoints Críticos | 25 |
| Endpoints Operativos | ~100 |
| Endpoints Stub/Incomplete | ~25 |
| Duplicados Detectados | 2-3 |
| Rutas Mal Organizadas | 4-5 |
| Sin Autenticación (Correctos) | 4 |
| Falta Documentación | ~50% |

---

## ✅ REPORTE FINAL

```
┌─────────────────────────────────────────┐
│  ESTADO GENERAL: OPERATIVO              │
│  Completitud: 80%                       │
│  Organización: 60%                      │
│  Documentación: 40%                     │
│  Necesita Limpieza: SÍ                  │
└─────────────────────────────────────────┘

PRIORIDADES:
1. ⚡ CRÍTICO: Eliminar duplicados (revision_manual, tickets_new)
2. ⚡ CRÍTICO: Unificar rutas notificaciones
3. 🟡 IMPORTANTE: Documentar todos los endpoints
4. 🟡 IMPORTANTE: Revisar endpoints stub
5. 🟢 SECUNDARIO: Organizar rutas admin
```

---

**Revisión completada:** 04/03/2026  
**Recomendación:** Iniciar limpieza en la próxima iteración

