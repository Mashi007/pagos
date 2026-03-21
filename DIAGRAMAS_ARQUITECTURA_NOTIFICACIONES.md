# 📊 DIAGRAMA DE ARQUITECTURA Y FLUJOS

## 1. Arquitectura General del Sistema de Notificaciones

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          SISTEMA DE NOTIFICACIONES                       │
└─────────────────────────────────────────────────────────────────────────┘

                              FRONTEND (React)
                        ┌─────────────────────────┐
                        │  Notificaciones.tsx     │
                        │  (9 pestañas)           │
                        ├─────────────────────────┤
                        │ - Previas (5,3,1 días)  │
                        │ - Día 0 (vencimiento)   │
                        │ - Retrasadas            │
                        │ - Prejudicial           │
                        │ - Mora 90+              │
                        │ - Liquidados            │
                        │ - Configuración         │
                        └────────────┬────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
    ┌──────────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
    │ TasaCambioModal      │ │ TablesUI         │ │ ConfiguracionTab     │
    │ (Ingreso Tasa)       │ │ (DataGrid)       │ │ (Plantillas, etc)    │
    │                      │ │                  │ │                      │
    │ - Input Tasa        │ │ - Filtros        │ │ - CRUD Plantillas   │
    │ - Validación        │ │ - Búsqueda       │ │ - Adjuntos          │
    │ - Modal no cerrable │ │ - Descargar      │ │ - Variables         │
    └──────────┬───────────┘ └────────┬─────────┘ └──────────┬───────────┘
               │                      │                      │
               └──────────────────────┼──────────────────────┘
                                      │
                        ┌─────────────▼─────────────┐
                        │  API GATEWAY (FastAPI)    │
                        │  http://localhost:8000    │
                        └─────────────┬─────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌──────────────────────────┐ ┌──────────────────────┐ ┌──────────────────┐
│ /admin/tasas-cambio      │ │ /notificaciones      │ │ /notificaciones   │
│ (5 endpoints)            │ │ (67 endpoints)       │ │ /tabs (25 eps)    │
│                          │ │                      │ │                   │
│ - GET /hoy               │ │ - CRUD Plantillas   │ │ - GET /tabs-data  │
│ - GET /estado            │ │ - CRUD Variables    │ │ - POST /enviar-*  │
│ - POST /guardar          │ │ - Envío masivo      │ │ - Stats, Excel    │
│ - GET /historial         │ │ - Stats, Excel      │ │                   │
│ - GET /por-fecha         │ │                      │ │                   │
└──────────────────────────┘ └──────────────────────┘ └──────────────────┘
        │                             │                      │
        └─────────────────────────────┼──────────────────────┘
                                      │
                        ┌─────────────▼──────────────┐
                        │  SERVICIOS (Backend)       │
                        │ ┌────────────────────────┐ │
                        │ │tasa_cambio_service     │ │
                        │ ├────────────────────────┤ │
                        │ │notificacion_service    │ │
                        │ ├────────────────────────┤ │
                        │ │liquidado_notif_service │ │
                        │ ├────────────────────────┤ │
                        │ │notificacion_logging    │ │
                        │ └────────────────────────┘ │
                        └─────────────┬──────────────┘
                                      │
                        ┌─────────────▼────────────┐
                        │  SQLALCHEMY ORM           │
                        │  (Session Management)     │
                        └─────────────┬────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────┐
│ DATABASE (PostgreSQL)│ │ SERVICIOS EXTERNOS   │ │ ALMACENAMIENTO   │
│ ┌──────────────────┐ │ ┌──────────────────┐  │ ┌──────────────────┤
│ │ tasas_cambio_    │ │ │ SMTP (Email)     │  │ │ PDFs Generados   │
│ │ diaria           │ │ │ - Envío masivo   │  │ │ - Estado cuenta  │
│ ├──────────────────┤ │ ├──────────────────┤  │ │ - Recibos        │
│ │ plantillas_      │ │ │ WhatsApp API     │  │ │                  │
│ │ notificacion     │ │ │ - SMS/WhatsApp   │  │ └──────────────────┘
│ ├──────────────────┤ │ ├──────────────────┤  │
│ │ variables_       │ │ │ Webhook para PDF │  │
│ │ notificacion     │ │ │ - Generación     │  │
│ ├──────────────────┤ │ └──────────────────┘  │
│ │ envios_          │ │                       │
│ │ notificacion     │ │                       │
│ └──────────────────┘ │                       │
└──────────────────────┘ └──────────────────────┘

```

---

## 2. Flujo de Ingreso de Tasa de Cambio (Crítico)

```
HORA: 00:55 AM
┌──────────────────┐
│ Admin inicia     │
│ sesión           │
└────────┬─────────┘
         │
         ▼
    ┌──────────────────────────┐
    │ Frontend carga Layout    │
    │ con TasaCambio           │
    │ Notificacion.tsx         │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ useEffect: verificar cada    │
    │ 5 minutos si debe_ingresar  │
    │ GET /admin/tasas-cambio/    │
    │      estado                 │
    └────────┬─────────────────────┘
             │
             ▼ (HORA: 01:05 AM)
    ┌──────────────────────────────────────────┐
    │ RESPUESTA:                               │
    │ {                                        │
    │   "debe_ingresar": true,                │
    │   "tasa_ya_ingresada": false,           │
    │   "hora_obligatoria_desde": "01:00",    │
    │   "hora_obligatoria_hasta": "23:59"     │
    │ }                                        │
    └────────┬─────────────────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ Frontend muestra:             │
    │ - Banner sticky (ámbar)      │
    │ - Icono ⚠️                   │
    │ - Título obligatorio         │
    │ - Botón "Ingresar Tasa"      │
    │                              │
    │ Modal NO se puede cerrar     │
    └────────┬─────────────────────┘
             │
             ▼ (ADMIN HACE CLIC)
    ┌──────────────────────────────┐
    │ Modal de Entrada:             │
    │ - Input: "2850.50"           │
    │ - Validación: > 0 ✓          │
    │ - Botón: "Guardar Tasa"      │
    └────────┬─────────────────────┘
             │
             ▼
    ┌──────────────────────────────────────────┐
    │ POST /admin/tasas-cambio/guardar         │
    │ {                                        │
    │   "tasa_oficial": 2850.50               │
    │ }                                        │
    │                                          │
    │ Validaciones Backend:                    │
    │ - ✓ Usuario es admin                    │
    │ - ✓ Hora >= 01:00 AM                    │
    │ - ✓ Tasa > 0                            │
    └────────┬───────────────────────────────┘
             │
             ▼
    ┌──────────────────────────────────────────┐
    │ GUARDAR EN BD:                           │
    │ INSERT INTO tasas_cambio_diaria (        │
    │   fecha = TODAY,                         │
    │   tasa_oficial = 2850.50,               │
    │   usuario_id = 123,                      │
    │   usuario_email = 'admin@co.com',        │
    │   created_at = NOW()                     │
    │ )                                        │
    │ ON CONFLICT (fecha) UPDATE               │
    │   tasa_oficial = 2850.50                │
    └────────┬───────────────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ RESPUESTA 200 OK:             │
    │ {                             │
    │   "id": 567,                 │
    │   "fecha": "2026-03-20",      │
    │   "tasa_oficial": 2850.50,   │
    │   "usuario_email": "...",     │
    │   "created_at": "2026-03-20T01:05:00Z"  │
    │ }                             │
    └────────┬─────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ Frontend:                     │
    │ - Mostrar mensaje: ✓ "Tasa"  │
    │   "guardada exitosamente"    │
    │ - Esperar 1.5 segundos       │
    │ - Cerrar modal automático    │
    │ - Banner desaparece          │
    └────────┬─────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ Admin puede ahora:            │
    │ ✅ Procesar pagos en BS      │
    │ ✅ Enviar notificaciones      │
    │ ✅ Usar la aplicación        │
    │                              │
    │ La tasa se usa para:         │
    │ - Conversión BS → USD        │
    │ - Registros en notificaciones│
    │ - Reportes de conciliación   │
    └──────────────────────────────┘

RIESGOS IDENTIFICADOS EN ESTE FLUJO:
❌ Si no hay tasa ingresada:
   - Pagos en BS serán rechazados
   - Sin mensaje claro (ERROR)
   - Admin no entiende por qué

❌ Si tasa se ingresa fuera de horario:
   - Sistema rechaza pero frontend no sabe
   - Confusión de usuario

❌ Si reloj del servidor está desincronizado:
   - Puede rechazar tasa correcta
   - O aceptar en horario equivocado
```

---

## 3. Flujo de Envío de Notificaciones (Riesgos)

```
PASO 1: ADMIN SELECCIONA PESTAÑA
┌────────────────────────────────────────┐
│ Admin en Notificaciones.tsx             │
│ Click en pestaña: "Faltan 5 días"       │
└────────────┬─────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────┐
│ GET /notificaciones/tabs-data?tab=dias_5           │
│                                                    │
│ Backend:                                           │
│ 1. Query: SELECT * FROM cuotas WHERE:             │
│    - fecha_pago IS NULL                           │
│    - fecha_vencimiento = TODAY + 5 días           │
│    - prestamo.estado != LIQUIDADO                 │
│ 2. JOIN con clientes y préstamos                  │
│ 3. Cargar config de envío                         │
│ 4. Cargar plantilla                               │
└────────────┬───────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────┐
│ RESPUESTA: Array[{                                │
│   cliente_id: 123,                                │
│   cliente_nombre: "Juan García",                  │
│   cliente_email: "juan@example.com",  ← ❌ SIN VALIDACIÓN
│   cliente_telefono: "04121234567",    ← ❌ SIN VALIDACIÓN
│   cedula: "12345678",                            │
│   prestamo_id: 456,                              │
│   cuota_numero: 1,                               │
│   cuota_monto: 1500.00,                          │
│   fecha_vencimiento: "2026-03-25",               │
│   dias_hasta_vencimiento: 5,                     │
│   correo_enviado_antes: false,  ← ❌ SIN DEDUPLICACIÓN
│ }]                                               │
│                                                  │
│ Total encontrados: 247                           │
└────────────┬───────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────┐
│ Frontend muestra:                      │
│ - Tabla con 247 clientes               │
│ - Botón "Enviar todos"                 │
│ - Botón "Enviar seleccionados"         │
│ - Estadísticas de envío anterior       │
└────────────┬─────────────────────────────┘
             │
PASO 2: ADMIN HACE CLIC EN "ENVIAR TODOS"
└──────────────┬─────────────────────────────┘
               │
               ▼
       ┌──────────────────────────────┐
       │ POST /notificaciones/         │
       │ enviar-dias-5                │
       │ (SIN TRANSACCIÓN) ← ❌ CRÍTICO│
       └──────────┬───────────────────┘
                  │
                  ▼
       ┌──────────────────────────────────────────┐
       │ LOOP: Para cada cliente (247 total):     │
       │                                          │
       │ ❌ RIESGO 1: Sin validación de email    │
       │   if cliente.email:  # ¿Y si es None?   │
       │       ...                                │
       │                                          │
       │ ❌ RIESGO 2: Sin deduplicación          │
       │   send_email(cliente.email, plantilla)   │
       │   # ¿Si se envió ayer? ¿Doble envío?   │
       │                                          │
       │ ❌ RIESGO 3: Sin reintentos             │
       │   try:                                  │
       │       SMTP.send(email)                  │
       │   except:                               │
       │       next()  # Pierde email sin reintento
       │                                          │
       │ ❌ RIESGO 4: Sin transacción            │
       │   INSERT envios_notificacion (...)       │
       │   # Si falla aquí, BD inconsistente      │
       │                                          │
       │ PARA CADA INTENTO:                       │
       │ 1. Renderizar plantilla con variables   │
       │    - {{cliente_nombre}}                  │
       │    - {{fecha_vencimiento}}               │
       │    - {{numero_cuota}}                    │
       │ 2. Generar PDF (si aplica)              │
       │ 3. Enviar Email                         │
       │ 4. Registrar en BD                      │
       │ 5. Logging por fase                     │
       │                                          │
       │ POSIBLES FALLOS EN MITAD:               │
       │ - Intento #50: SMTP timeout             │
       │ - Intento #75: Conexión BD cae          │
       │ - Intento #100: Memoria insuficiente    │
       │                                          │
       │ ESTADO FINAL (INCORRECTO):              │
       │ - Email 1-49: ✓ Enviados y registrados  │
       │ - Email 50-247: ✗ Sin enviar, sin registro
       │ - BD INCONSISTENTE ← ❌ CRÍTICO         │
       └──────────────────────────────────────────┘
                  │
                  ▼
       ┌──────────────────────────────┐
       │ Frontend muestra:             │
       │ "✓ 49 enviados"              │
       │ "✗ 198 fallidos"             │
       │                              │
       │ Pero:                        │
       │ - Admin no sabe qué pasó    │
       │ - Reintentar = duplicados   │
       │ - BD inconsistente          │
       └──────────────────────────────┘

RIESGOS EN ESTE FLUJO:
🔴 R1: Email inválido → rebota silencioso
🔴 R2: Sin transacción → BD inconsistente
🔴 R3: Sin deduplicación → spam posible
🔴 R8: Sin reintentos → emails perdidos

SOLUCIÓN RECOMENDADA:
✅ Validar email ANTES
✅ Usar transacción explícita
✅ Reintentos con exponential backoff
✅ Cola asincrónica (Celery)
```

---

## 4. Matriz de Impacto de Riesgos

```
CRITICIDAD
    ↑
   10│                    🔴R3
    9│   🔴R1  🔴R2       (No hay tasa
    8│ (Email) (Tx)        = Pagos rechazan)
    7│
    6│        🟡R6      🟡R8
    5│      (Código)   (Reintentos)
    4│                🟡R11
    3│                (Cambio tasa)
    2│        🟡R13  🟢R15
    1│      (Historial)(Docs)
    └─┴───┴───┴───┴───┴───┴───┴───┴───→ PROBABILIDAD
     1   2   3   4   5   6   7   8   9  10

ESCALA:
- Arriba a la izquierda 🔴 = CRÍTICO
- Centro 🟡 = IMPORTANTE
- Abajo a la derecha 🟢 = MENOR

ACCIÓN INMEDIATA: Riesgos 🔴 en cuadrante superior izquierdo

Timeline:
Semana 1: 🔴🔴🔴🔴 (R1, R2, R3, R5)
Semana 2: 🔴🟡🟡    (R8, R6, R4)
Semana 3-4: 🟡🟢    (Mejoras)
```

---

## 5. Tabla De Integración Con Otros Módulos

```
┌──────────────────────────────────────────────────────────────────────────┐
│          NOTIFICACIONES ↔ OTROS MÓDULOS DEL SISTEMA                      │
└──────────────────────────────────────────────────────────────────────────┘

MÓDULO: PAGOS
└─────────────────────────────────────────────────────────────────────────
   DATOS CONSUMIDOS:
   - cuotas.fecha_pago (para verificar si está pagada)
   - cuotas.fecha_vencimiento (para calcular días de atraso)
   - clientes.email, clientes.telefono (para contacto)
   
   DATOS GENERADOS:
   - envios_notificacion.id (referencia de notificación)
   - Plantillas con variables de cuota
   
   RIESGO: ⚠️ Si cuota se paga MIENTRAS se envía notificación
   SOLUCIÓN: Usar transacción + lock de fila

MÓDULO: PRÉSTAMOS
└─────────────────────────────────────────────────────────────────────────
   DATOS CONSUMIDOS:
   - prestamos.estado (para filtrar LIQUIDADO)
   - prestamos.monto_total (para PDF estado de cuenta)
   - prestamos.fecha_desembolso (para cálculos)
   
   DATOS GENERADOS:
   - Notificación automática cuando estado = LIQUIDADO
   
   RIESGO: 🔴 Si prestamo está LIQUIDADO y llegan cuotas nuevas
   SOLUCIÓN: Validar estado al consultar cuotas

MÓDULO: TASAS DE CAMBIO
└─────────────────────────────────────────────────────────────────────────
   DATOS CONSUMIDOS:
   - tasas_cambio_diaria.tasa_oficial (para conversión BS→USD)
   - tasas_cambio_diaria.fecha
   
   DATOS GENERADOS:
   - Auditoría en envios_notificacion
   
   RIESGO: 🔴 Pago en BS sin tasa ingresada
   SOLUCIÓN: Validación explícita + mensaje claro

MÓDULO: CLIENTES
└─────────────────────────────────────────────────────────────────────────
   DATOS CONSUMIDOS:
   - clientes.email (para SMTP)
   - clientes.telefono (para WhatsApp)
   - clientes.nombre (para plantilla)
   - clientes.cedula (para auditoría)
   
   DATOS GENERADOS:
   - Flag cliente.ultima_notificacion_fecha (propuesto)
   
   RIESGO: ⚠️ Email/teléfono inválidos → rebotes
   SOLUCIÓN: Validación + limpieza de datos

MÓDULO: CONFIGURACIÓN
└─────────────────────────────────────────────────────────────────────────
   DATOS CONSUMIDOS:
   - config.notificaciones_envios (qué enviar, cuándo, plantillas)
   - config.smtp_* (credenciales email)
   - config.whatsapp_* (credenciales WhatsApp)
   
   DATOS GENERADOS:
   - Nuevas opciones de configuración
   
   RIESGO: ⚠️ Config inválida → falla silenciosa
   SOLUCIÓN: Validación en startup

MÓDULO: AUDITORÍA & LOGS
└─────────────────────────────────────────────────────────────────────────
   DATOS CONSUMIDOS:
   - (ninguno directo)
   
   DATOS GENERADOS:
   - envios_notificacion (auditoría completa)
   - Logs estructurados por fase
   
   BENEFICIO: ✅ Trazabilidad completa
   
MÓDULO: DASHBOARD & REPORTES
└─────────────────────────────────────────────────────────────────────────
   DATOS CONSUMIDOS:
   - envios_notificacion.estadisticas (% éxito, rebotes)
   - tasas_cambio_diaria (historial de tasas)
   
   DATOS GENERADOS:
   - KPIs para dashboard
   
   RIESGO: ⚠️ Dashboard muestra datos stale
   SOLUCIÓN: Caché con TTL de 5 minutos
```

---

## 6. Estados Posibles de Notificación

```
                        ┌─────────────────────────────────┐
                        │  CLIENTE CON CUOTA PENDIENTE    │
                        │  (fecha_pago = NULL)            │
                        └──────────────┬──────────────────┘
                                       │
                  ┌────────────────────┼────────────────────┐
                  │                    │                    │
                  ▼                    ▼                    ▼
        ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
        │ 5 DÍAS ANTES     │ │ 3 DÍAS ANTES     │ │ 1 DÍA ANTES      │
        │                  │ │                  │ │                  │
        │ - Notificación   │ │ - Recordatorio   │ │ - Urgencia       │
        │   Recordatoria   │ │   Segunda        │ │   tercera        │
        │ - Tono: Cortés   │ │ - Tono: Amable   │ │ - Tono: Urgente  │
        │ - CC: Gerencia   │ │ - CC: ninguno    │ │ - CC: Cobranza   │
        │                  │ │                  │ │                  │
        └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
                 │                    │                    │
                 └────────────────────┼────────────────────┘
                                      │
                                      ▼
                        ┌─────────────────────────────────┐
                        │  DÍA 0 (VENCIMIENTO)            │
                        │                                 │
                        │ - Notificación URGENTE          │
                        │ - Tono: Obligatorio pago        │
                        │ - CC: Cobranza, Gerencia        │
                        │ - WhatsApp + Email              │
                        │ - Con PDF de recibo             │
                        └──────────────┬──────────────────┘
                                       │
                                       ▼ (Si no se pagó)
                        ┌─────────────────────────────────┐
                        │ 1 A 5 DÍAS DE ATRASO            │
                        │                                 │
                        │ - Notificación COBRANZA         │
                        │ - Tono: Formal, Urgente        │
                        │ - CC: Cobranza, Abogado         │
                        │ - Llamadas telefónicas          │
                        │ - Acción: Visita personal       │
                        └──────────────┬──────────────────┘
                                       │
                                       ▼ (Si continúa atrasado)
                        ┌─────────────────────────────────┐
                        │ 30+ DÍAS DE ATRASO              │
                        │ (EN COBRANZA JUDICIAL)          │
                        │                                 │
                        │ - Notificación PREJUDICIAL      │
                        │ - Tono: Legal, Obligatorio      │
                        │ - CC: Abogado, Gerencia         │
                        │ - Acciones: Demanda, Embargo    │
                        └──────────────┬──────────────────┘
                                       │
                                       ▼ (Si continúa atrasado)
                        ┌─────────────────────────────────┐
                        │ 90+ DÍAS DE ATRASO              │
                        │ (MOROSO CRÓNICO)                │
                        │                                 │
                        │ - Notificación FINAL            │
                        │ - Tono: Máxima urgencia         │
                        │ - CC: Gerencia, Junta Directiva │
                        │ - Acciones: Venta de deuda      │
                        └─────────────────────────────────┘

CADA ESTADO PUEDE TENER VARIAS PLANTILLAS:
- Por tipo de préstamo (personal, vehicular, etc.)
- Por idioma (español, inglés)
- Por canal (email, SMS, WhatsApp)
- Personalizadas por cliente

PROBLEMA: Sin deduplicación o tracking
- ¿Se envió ya una notificación hoy?
- ¿Cómo evitar spam?
- ¿Cómo auditar quién recibió qué?

SOLUCIÓN:
✅ Guardar en envios_notificacion todas las acciones
✅ Verificar duplicados antes de enviar
✅ Dejar que admin decida reintentos manuales
```

---

**Diagramas de arquitectura completados: 20 de Marzo, 2026**
