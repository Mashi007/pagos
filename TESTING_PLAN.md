# Plan de Testing - Funcionalidades Clave

**Fecha**: 2026-03-04
**Base URL**: https://rapicredit.onrender.com/api/v1

## 1. LOGIN (✅ Ya funciona)

```bash
curl -X POST https://rapicredit.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "itmaster@rapicreditca.com",
    "password": "<ADMIN_PASSWORD>"
  }'
```

**Respuesta esperada**: 
- `access_token`: token JWT válido
- `user`: objeto con datos del usuario
- `token_type`: "bearer"

---

## 2. CREAR PRÉSTAMO

Endpoint: `POST /prestamos`

```json
{
  "cedula_cliente": "V12345678",
  "monto": 50000,
  "tasa_interes": 5.5,
  "plazo_meses": 24,
  "tipo_amortizacion": "FRANCESA",
  "modelo_vehiculo": "Toyota Corolla 2020",
  "concesionario": "Automotriz Central",
  "analista": "Juan Pérez"
}
```

**Verificar**:
- ✅ Préstamo creado con `estado = 'DRAFT'`
- ✅ `usuario_proponente = current_user.email` (campos de auditoría)
- ✅ Cuotas generadas automáticamente (24 cuotas)
- ✅ Cada cuota con `estado = 'PENDIENTE'`

---

## 3. CREAR PAGO

Endpoint: `POST /pagos`

```json
{
  "cedula": "V12345678",
  "prestamo_id": 1,
  "monto_pagado": 2500.50,
  "fecha_pago": "2026-03-04",
  "numero_documento": "BNC-20260304-001"
}
```

**Verificar**:
- ✅ Pago creado con `estado = 'PAGADO'`
- ✅ `usuario_registro = current_user.email` (auditoría)
- ✅ Pago aplicado automáticamente a cuota más antigua (FIFO)
- ✅ Entrada en tabla `cuota_pagos` con `orden_aplicacion = 1`

---

## 4. VERIFICAR APLICACIÓN DE PAGO A CUOTA

Después de crear el pago, verificar que:

```sql
-- Verificar cuota actualizada
SELECT id, numero_cuota, estado, total_pagado, monto_cuota FROM public.cuotas 
WHERE prestamo_id = 1 AND numero_cuota = 1;

-- Debe mostrar:
-- id | numero_cuota | estado | total_pagado | monto_cuota
-- XX |            1 | PAGADO |      2500.50 |     2500.50
```

---

## 5. VERIFICAR AUDITORÍA

```sql
-- Verificar registros de auditoría
SELECT usuario_id, accion, entidad, fecha_hora FROM public.auditoria 
WHERE entidad IN ('Prestamo', 'Pago') 
ORDER BY fecha_hora DESC LIMIT 10;

-- Debe mostrar: acciones POST para crear préstamo y pago
```

---

## 6. VERIFICAR ESTADOS Y TRANSICIONES

### Cuota:
- ✅ `PENDIENTE` → `PAGADO` (cuando total_pagado >= monto_cuota)
- ✅ `PAGADO` → `PAGO_ADELANTADO` (cuando se paga más)
- ✅ `PENDIENTE` → `VENCIDO` (después de fecha_vencimiento, sin pago)
- ✅ `VENCIDO` → `MORA` (después de 15 días sin pago)

### Préstamo:
- ✅ `DRAFT` → `EN_REVISION` (al aprobar)
- ✅ `EN_REVISION` → `APROBADO` (al aprobar manual)
- ✅ `APROBADO` → `DESEMBOLSADO` (al registrar desembolso)

---

## 7. PRUEBAS ADICIONALES

### Cargar pagos masivos
- Endpoint: `POST /pagos/upload`
- Archivo: Excel con columnas [cedula, prestamo_id, monto_pagado, fecha_pago, numero_documento]
- Verificar: Todos los pagos se registren con `usuario_registro` correcto

### Rechazar préstamo
- Endpoint: `POST /prestamos/{id}/rechazar`
- Payload: `{"motivo_rechazo": "Análisis rechazado"}`
- Verificar: Estado cambie a `RECHAZADO` y se registre en auditoría

---

## Checklist de Testing

- [ ] Login exitoso (token válido)
- [ ] Crear préstamo (estado DRAFT, usuario_proponente registrado)
- [ ] Crear pago (usuario_registro registrado, aplicado a cuota)
- [ ] Cuota actualiza a PAGADO
- [ ] Auditoría registra ambas acciones
- [ ] Estados y transiciones son correctas
- [ ] Cargar pagos masivos funciona
- [ ] Rechazar préstamo funciona

---

## Notas Importantes

1. **Auditoría**: Todos los cambios deben estar registrados en `public.auditoria`
2. **Usuario**: El campo `usuario_registro` (pagos) y `usuario_proponente` (prestamos) deben tener el email actual
3. **FIFO**: Los pagos se aplican a la cuota más antigua sin pagar
4. **Transiciones de estado**: Revisar que sean correctas según la lógica de negocio
5. **BD limpia**: Solo 29 tablas necesarias, sin backups ni temporales

---

## Troubleshooting

Si algo falla:
1. Revisar logs en Render dashboard
2. Ejecutar: `SELECT COUNT(*) FROM public.cuota_pagos;` (debe haber registros)
3. Verificar: `SELECT * FROM public.auditoria ORDER BY id DESC LIMIT 5;`
4. Confirmar: Variables de entorno en Render (DATABASE_URL, ADMIN_EMAIL, etc.)
