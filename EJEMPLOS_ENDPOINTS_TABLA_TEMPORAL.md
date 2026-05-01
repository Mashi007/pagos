# 📚 EJEMPLOS DE USO: 5 Endpoints de Tabla Temporal

## 1️⃣ GUARDAR BORRADOR
**POST** `/api/v1/revision-manual/prestamos/123/guardar-borrador`

### Request
```json
{
  "cliente_datos": {
    "nombres": "Juan Pérez García",
    "telefono": "5551234567",
    "email": "juan@example.com"
  },
  "prestamo_datos": {
    "total_financiamiento": 50000,
    "numero_cuotas": 24,
    "fecha_aprobacion": "2026-05-01"
  },
  "cuotas_datos": [
    {
      "numero_cuota": 1,
      "monto": 2083.33,
      "fecha_vencimiento": "2026-06-01"
    }
  ],
  "pagos_datos": [
    {
      "id": 456,
      "monto_pagado": 2083.33,
      "estado": "CONCILIADO",
      "fecha_pago": "2026-05-28"
    }
  ]
}
```

### Response (200 OK)
```json
{
  "mensaje": "Borrador guardado exitosamente",
  "borrador_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "prestamo_id": 123,
  "estado": "borrador"
}
```

---

## 2️⃣ OBTENER BORRADOR
**GET** `/api/v1/revision-manual/prestamos/123/obtener-borrador`

### Response (200 OK)
```json
{
  "mensaje": "Borrador obtenido",
  "prestamo_id": 123,
  "borrador_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "estado": "borrador",
  "cliente_datos": {
    "nombres": "Juan Pérez García",
    "telefono": "5551234567",
    "email": "juan@example.com"
  },
  "prestamo_datos": {
    "total_financiamiento": 50000,
    "numero_cuotas": 24,
    "fecha_aprobacion": "2026-05-01"
  },
  "cuotas_datos": [
    {
      "numero_cuota": 1,
      "monto": 2083.33,
      "fecha_vencimiento": "2026-06-01"
    }
  ],
  "pagos_datos": [
    {
      "id": 456,
      "monto_pagado": 2083.33,
      "estado": "CONCILIADO",
      "fecha_pago": "2026-05-28"
    }
  ],
  "validadores_resultado": {},
  "creado_en": "2026-05-01T09:10:30",
  "actualizado_en": "2026-05-01T09:15:45"
}
```

---

## 3️⃣ VALIDAR BORRADOR
**POST** `/api/v1/revision-manual/prestamos/123/validar-borrador`

### Response (200 OK) - SIN ERRORES
```json
{
  "valido": true,
  "errores": [],
  "advertencias": [],
  "timestamp": "2026-05-01T09:16:00"
}
```

### Response (200 OK) - CON ERRORES
```json
{
  "valido": false,
  "errores": [
    "Cuota 1: estado 'INVALIDO' inválido",
    "Pago 456: estado 'PENDIENTE' no conciliado"
  ],
  "advertencias": [
    "Fecha de aprobación es posterior a fecha actual"
  ],
  "timestamp": "2026-05-01T09:16:00"
}
```

---

## 4️⃣ CONFIRMAR BORRADOR
**POST** `/api/v1/revision-manual/prestamos/123/confirmar-borrador`

**Precondición**: Estado debe ser 'validado' (sin errores)

### Response (200 OK) - CONFIRMACIÓN EXITOSA
```json
{
  "mensaje": "Borrador confirmado y migrado a BD real",
  "prestamo_id": 123,
  "cuotas_creadas": 24,
  "pagos_aplicados": 1,
  "cambios": {
    "total_financiamiento": {
      "anterior": 45000,
      "nuevo": 50000
    },
    "numero_cuotas": {
      "anterior": 20,
      "nuevo": 24
    },
    "fecha_aprobacion": {
      "anterior": "2026-04-20",
      "nuevo": "2026-05-01"
    }
  }
}
```

### Response (400 BAD REQUEST) - ESTADO INVALIDO
```json
{
  "detail": "Borrador no está listo para confirmar (estado: error)"
}
```

### Response (500 ERROR) - FALLA EN TRANSACCIÓN
```json
{
  "detail": "Error al confirmar borrador"
}
```

---

## 5️⃣ DESCARTAR BORRADOR
**DELETE** `/api/v1/revision-manual/prestamos/123/descartar-borrador`

### Response (200 OK)
```json
{
  "mensaje": "Borrador descartado (cambios no guardados)",
  "prestamo_id": 123,
  "borrador_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

---

## 🔄 FLUJO COMPLETO DE USUARIO

### Paso 1: Usuario abre préstamo #123 y edita
```
UI: Cambios sin confirmar (Guardar)
→ POST /guardar-borrador
← Guardar exitoso ✅
```

### Paso 2: Usuario hace más cambios y valida
```
UI: Presiona "Validar y Confirmar"
→ POST /validar-borrador
← Resultado: { valido: true, errores: [] } ✅
→ Mostrar preview
```

### Paso 3: Usuario confirma cambios
```
UI: Presiona "Confirmar Cambios"
→ POST /confirmar-borrador
← Migrado a BD real ✅
  Cuotas: 24 creadas
  Pagos: 1 aplicado
  Cédula: actualizada
  Auditoría: registrada
```

---

## ⚠️ MANEJO DE ERRORES

### Si validador falla:
```
POST /validar-borrador
→ { valido: false, errores: [...] }
→ Tabla temporal SE QUEDA con estado='error'
→ Usuario corrige en UI
→ POST /validar-borrador (reintento)
```

### Si confirmación falla:
```
POST /confirmar-borrador
→ HTTPException 500
→ ROLLBACK automático
→ Tabla temporal SE QUEDA (usuario puede reintentarlo)
```

### Si usuario cancela:
```
DELETE /descartar-borrador
→ Tabla temporal eliminada
→ BD real intacta
→ Cambios perdidos (confirm)
```

---

## 📊 ESTADOS EN TIEMPO REAL

**Via GET /obtener-borrador**, puedes ver en cualquier momento:

| Campo | Significado |
|-------|------------|
| `estado` | 'borrador' / 'validado' / 'error' |
| `validadores_resultado` | JSON con resultado de validación |
| `error_mensaje` | Concatenación de errores (si status='error') |
| `actualizado_en` | Timestamp de última actualización |

---

## 🎯 INTEGRACIÓN FRONTEND

En `revisionManualService.ts`, los métodos quedarían:

```typescript
// 1. Guardar cambios a tabla temporal
async guardarBorrador(prestamoId: number, datos: any): Promise<any> {
  return await apiClient.post(
    `/api/v1/revision-manual/prestamos/${prestamoId}/guardar-borrador`,
    datos
  );
}

// 2. Obtener preview
async obtenerBorrador(prestamoId: number): Promise<any> {
  return await apiClient.get(
    `/api/v1/revision-manual/prestamos/${prestamoId}/obtener-borrador`
  );
}

// 3. Validar
async validarBorrador(prestamoId: number): Promise<any> {
  return await apiClient.post(
    `/api/v1/revision-manual/prestamos/${prestamoId}/validar-borrador`
  );
}

// 4. Confirmar
async confirmarBorrador(prestamoId: number): Promise<any> {
  return await apiClient.post(
    `/api/v1/revision-manual/prestamos/${prestamoId}/confirmar-borrador`
  );
}

// 5. Descartar
async descartarBorrador(prestamoId: number): Promise<any> {
  return await apiClient.delete(
    `/api/v1/revision-manual/prestamos/${prestamoId}/descartar-borrador`
  );
}
```

---

**Documentación completada** ✅

