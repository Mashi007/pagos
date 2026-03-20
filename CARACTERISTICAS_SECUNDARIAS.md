# Caracteristicas Secundarias: Conciliación y Auditoría de Pagos

## 1. Automatizar Asignación de Pagos No Conciliados

### Descripción
Sistema automático que asigna pagos sin cuotas a cuotas pendientes usando FIFO (First In, First Out). Valida en cada paso para evitar sobre-aplicaciones.

### Características
- **FIFO**: Los pagos se asignan a cuotas en orden de fecha de pago
- **Validación**: Cada asignación se valida antes de aplicar
- **Auditoría**: Cada asignación se registra en tabla de auditoría
- **Tolerancia**: 0.01 para diferencias de redondeo

### Endpoint
\\\
POST /api/v1/conciliacion/asignar-pagos-automatico
Headers: Authorization: Bearer <ADMIN_TOKEN>
Query Parameters:
  - prestamo_id (opcional): Limitar a un préstamo específico
\\\

### Respuesta
\\\json
{
  "status": "success",
  "message": "Asignación completada: 45 exitosas, 2 fallidas",
  "data": {
    "exitosas": 45,
    "fallidas": 2,
    "total_monto_asignado": 12450.50,
    "asignaciones": [
      {
        "pago_id": 1001,
        "cuota_id": 5042,
        "monto": 500.00
      }
    ],
    "errores": [
      "Pago 1002: No tiene prestamo_id asignado.",
      "Pago 1003 -> Cuota 5043: Sobre-aplicación detectada"
    ]
  }
}
\\\

---

## 2. Validación en Tiempo Real para Evitar Sobre-Aplicaciones

### Descripción
Middleware + servicio que valida cada intento de aplicar dinero a una cuota. Impide que el monto total aplicado exceda el monto de la cuota.

### Componentes

#### ValidadorSobreAplicacion (Servicio)
Ubicación: \pp/services/conciliacion_automatica_service.py\

Métodos:
- \obtener_monto_aplicado_actual(db, cuota_id)\: Retorna monto ya aplicado
- \alidar_aplicacion(db, cuota, monto_a_aplicar)\: Valida antes de aplicar
- \calcular_estado_actualizado(db, cuota_id)\: Calcula estado según aplicaciones

#### ValidadorSobreAplicacionMiddleware
Ubicación: \pp/middleware/validador_sobre_aplicacion.py\

Intercepta requests POST/PUT a \/aplicar-cuota*\ y valida antes de ejecutar.

### Validaciones Implementadas
1. **Monto Total**: No exceda \monto_cuota + 0.01\
2. **Monto Positivo**: El monto a aplicar > 0
3. **Estado Válido**: No aplicar a cuota CANCELADA
4. **Existencia**: Cuota existe en BD

### Respuesta de Error
\\\json
{
  "status_code": 422,
  "detail": "Validación fallida",
  "errores": [
    "Sobre-aplicación detectada: 450.00 + 75.50 > 500.00",
    "Monto a aplicar debe ser positivo: -50.00"
  ]
}
\\\

---

## 3. Documentación de Estados de Cuota

### Estados Válidos

#### PAGADO
- **Condición**: Monto aplicado >= Monto de cuota (con tolerancia ±0.01)
- **Color**: Verde (#10b981)
- **Requiere Cobranza**: No
- **Transiciones**: → CANCELADA
- **Significado**: Cuota completamente pagada, acreedor satisfecho

#### PENDIENTE
- **Condición**: Sin pagos aplicados o con vencimiento futuro
- **Color**: Amarillo (#f59e0b)
- **Requiere Cobranza**: No
- **Transiciones**: → PAGADO, MORA, PARCIAL, CANCELADA
- **Significado**: Cuota aún no vencida, deudor tiene tiempo

#### MORA
- **Condición**: Vencida (fecha_vencimiento < hoy) y sin pagar completamente
- **Color**: Rojo (#ef4444)
- **Requiere Cobranza**: Sí ⚠️
- **Transiciones**: → PAGADO, PARCIAL, CANCELADA
- **Significado**: Cuota atrasada, activa alertas de cobranza

#### PARCIAL
- **Condición**: Monto aplicado < Monto de cuota (y > 0)
- **Color**: Púrpura (#8b5cf6)
- **Requiere Cobranza**: Sí
- **Transiciones**: → PAGADO, MORA, CANCELADA
- **Significado**: Pago parcial realizado, falta saldo

#### CANCELADA
- **Condición**: Anulada por decisión administrativa
- **Color**: Gris (#6b7280)
- **Requiere Cobranza**: No
- **Transiciones**: (ninguna)
- **Significado**: Cuota no vigente, no requiere pago

### Ciclo de Vida Típico
\\\
PENDIENTE (fecha vencimiento > hoy)
    ↓ (pasa fecha vencimiento)
MORA (sin pagar)
    ↓ (recibe pago parcial)
PARCIAL (pago 50%)
    ↓ (recibe pago resto)
PAGADO (pago 100%)
    ↓ (opcional)
CANCELADA
\\\

### Endpoint de Referencia
\\\
GET /api/v1/referencia/estados-cuota
Headers: Authorization: Bearer <USER_TOKEN>
\\\

Retorna documentación completa, colores, iconos, transiciones permitidas y ciclo de vida.

---

## 4. Auditoría de Conciliación Manual

### Descripción
Sistema de auditoría que registra TODAS las asignaciones de pagos a cuotas (manuales y automáticas). Permite trazabilidad completa y análisis de operaciones.

### Tabla de Auditoría
Ubicación: \uditoria_conciliacion_manual\

Columnas:
- \id\: PK
- \pago_id\: FK a pagos
- \cuota_id\: FK a cuotas
- \usuario_id\: FK a usuarios (quién ejecutó)
- \monto_asignado\: Cantidad aplicada
- \	ipo_asignacion\: MANUAL o AUTOMATICA
- \motivo\: Razón de la asignación (opcional)
- \esultado\: EXITOSA o FALLIDA
- \echa_asignacion\: Timestamp de la operación
- \creado_en\ / \ctualizado_en\: Trazabilidad

### Endpoints de Auditoría

#### Obtener Historial
\\\
GET /api/v1/auditoria/conciliacion
Headers: Authorization: Bearer <ADMIN_TOKEN>
Query Parameters:
  - dias: 1-365 (default: 7)
  - tipo_asignacion: MANUAL o AUTOMATICA
  - resultado: EXITOSA o FALLIDA
  - usuario_id: ID del usuario (opcional)
\\\

Respuesta:
\\\json
{
  "status": "success",
  "data": {
    "estadisticas": {
      "total_registros": 1250,
      "exitosas": 1205,
      "fallidas": 45,
      "tasa_exito": "96.4%",
      "monto_total_asignado": 450000.00
    },
    "por_tipo": {
      "AUTOMATICA": {
        "cantidad": 900,
        "monto": 350000.00,
        "exitosas": 890,
        "fallidas": 10
      },
      "MANUAL": {
        "cantidad": 350,
        "monto": 100000.00,
        "exitosas": 315,
        "fallidas": 35
      }
    },
    "registros": [
      {
        "id": 1,
        "pago_id": 5001,
        "cuota_id": 2345,
        "monto": 500.00,
        "tipo": "AUTOMATICA",
        "resultado": "EXITOSA",
        "usuario_id": null,
        "fecha": "2026-03-20T15:30:45.123Z"
      }
    ]
  }
}
\\\

#### Resumen Diario
\\\
GET /api/v1/auditoria/conciliacion/resumen-diario
Headers: Authorization: Bearer <ADMIN_TOKEN>
Query Parameters:
  - dias: 1-365 (default: 30)
\\\

Retorna resumen agrupado por día:
\\\json
{
  "data": {
    "por_dia": {
      "2026-03-20": {
        "automaticas": 45,
        "manuales": 12,
        "exitosas": 52,
        "fallidas": 5,
        "monto_total": 15000.00
      },
      "2026-03-19": {
        "automaticas": 38,
        "manuales": 8,
        "exitosas": 43,
        "fallidas": 3,
        "monto_total": 12500.00
      }
    }
  }
}
\\\

---

## Vistas SQL para Análisis

### v_auditoria_conciliacion
Resumen diario de auditoría:
- Fecha
- Tipo de asignación
- Cantidad de asignaciones
- Monto total asignado
- Exitosas vs Fallidas

### v_pagos_sin_asignar_detalle
Pagos que no están asignados a ninguna cuota:
- Información del pago
- Días sin asignar
- Categoría de antigüedad (NUEVO, RECIENTE, ANTIGUO, MUY_ANTIGUO)

### v_cuotas_sobre_aplicadas
Cuotas con sobre-aplicación (dinero aplicado > monto cuota):
- ID de cuota y préstamo
- Monto de cuota
- Total aplicado
- Exceso

### v_estadisticas_estados_cuota
Estadísticas agregadas por estado:
- Cantidad de cuotas
- Monto total
- Monto promedio
- Cuotas en mora

---

## Flujo de Integración

### 1. Asignación Automática (Diaria a las 9 PM)
\\\
scheduler.actualizar_prestamos_liquidado()
  → ConciliacionAutomaticaService.asignar_pagos_no_conciliados()
    → ValidadorSobreAplicacion.validar_aplicacion()
    → Registra en auditoria_conciliacion_manual
    → Calcula nuevos estados de cuota
    → Genera alertas si hay errores
\\\

### 2. Asignación Manual (Endpoint Admin)
\\\
POST /api/v1/conciliacion/asignar-pagos-automatico
  → ValidadorSobreAplicacionMiddleware (valida request)
  → ConciliacionAutomaticaService.asignar_pagos_no_conciliados()
  → Retorna resultado detallado
\\\

### 3. Consulta de Estados
\\\
GET /api/v1/referencia/estados-cuota
  → Retorna documentación y ciclo de vida
GET /api/v1/conciliacion/estados-cuotas
  → Retorna estadísticas actuales
GET /api/v1/conciliacion/cuotas-sobre-aplicadas
  → Identifica problemas de validación
\\\

### 4. Auditoría
\\\
GET /api/v1/auditoria/conciliacion
  → Historial completo con filtros
GET /api/v1/auditoria/conciliacion/resumen-diario
  → Tendencias diarias
\\\

---

## Testing

### Test de Asignación Automática
\\\ash
curl -X POST "https://rapicredit.onrender.com/api/v1/conciliacion/asignar-pagos-automatico" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
\\\

### Test de Validación
\\\ash
# Intenta sobre-aplicar (debe fallar)
curl -X POST "https://rapicredit.onrender.com/api/v1/cuotas/5000/aplicar-cuota" \
  -H "Authorization: Bearer <USER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"cuota_id": 5000, "monto_aplicado": 10000, "pago_id": 1001}'
\\\

### Test de Documentación
\\\ash
curl "https://rapicredit.onrender.com/api/v1/referencia/estados-cuota" \
  -H "Authorization: Bearer <USER_TOKEN>"
\\\

### Test de Auditoría
\\\ash
curl "https://rapicredit.onrender.com/api/v1/auditoria/conciliacion?dias=30" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"

curl "https://rapicredit.onrender.com/api/v1/auditoria/conciliacion/resumen-diario?dias=30" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
\\\

---

## Archivos Creados/Modificados

### Nuevos Servicios
- \pp/services/conciliacion_automatica_service.py\ (463 líneas)

### Nuevos Modelos
- \pp/models/auditoria_conciliacion_manual.py\ (32 líneas)

### Nuevos Middleware
- \pp/middleware/validador_sobre_aplicacion.py\ (68 líneas)

### Nuevos Endpoints
- \pp/api/v1/endpoints/conciliacion.py\ (77 líneas)
- \pp/api/v1/endpoints/referencia_estados_cuota.py\ (114 líneas)
- \pp/api/v1/endpoints/auditoria_conciliacion.py\ (156 líneas)

### SQL
- \sql/02_auditoria_conciliacion.sql\ (82 líneas)
  - Tabla auditoria_conciliacion_manual
  - 4 vistas para análisis

### Modificados
- \pp/main.py\ (agregados routers + middleware)

---

## Resumen de Validaciones

### Validaciones de Sobre-Aplicación
✅ Monto total aplicado ≤ monto cuota + 0.01
✅ Monto a aplicar > 0
✅ Cuota no está CANCELADA
✅ Cuota existe en BD

### Validaciones de Estados
✅ Solo ESTADOS_VALIDOS permitidos
✅ Transiciones válidas según estado
✅ Cálculo automático de estado según aplicaciones
✅ Tolerancia de 0.01 para redondeo

### Auditoría Completa
✅ Toda asignación registrada
✅ Trazabilidad de usuario
✅ Timestamp preciso
✅ Resultado (exitosa/fallida)
✅ Tipo (manual/automática)

---

## Estado: ✅ COMPLETADO

Todas las 4 características secundarias están implementadas:
1. ✅ Asignación automática de pagos
2. ✅ Validación en tiempo real
3. ✅ Documentación de estados
4. ✅ Auditoría de conciliación

**Listo para producción.**
