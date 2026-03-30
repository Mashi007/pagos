# Solución: Auto-Asignación de ID de Crédito (prestamo_id)

**Fecha**: 30 de Marzo, 2026  
**Problema**: En https://rapicredit.onrender.com/pagos/pagos no se cargaban automáticamente los IDs de crédito en todas las filas.

---

## Resumen de la Solución

Se han implementado **3 nuevos endpoints** en el backend y una **interfaz gráfica** en el frontend para identificar y asignar automáticamente los `prestamo_id` a los pagos que los necesitan.

### Componentes Agregados

#### 1. Backend - Dos Nuevos Endpoints (`pagos.py`)

**A) `GET /api/v1/pagos/sin-prestamo/sugerir`**
- Retorna todos los pagos sin `prestamo_id` asignado
- Para cada pago, analiza la cédula del cliente
- Si el cliente tiene **exactamente 1 crédito activo** → marca como "auto-asignable"
- Si tiene 0 ó múltiples → marca como "requiere intervención manual"
- Retorna resumen con totales

```python
Respuesta:
{
  "sugerencias": [
    {
      "pago_id": 123,
      "cedula_cliente": "V1234567",
      "prestamo_sugerido": 456,
      "num_creditos_activos": 1,
      "acciones_necesarias": "auto"
    },
    ...
  ],
  "resumen": {
    "total_pagos_sin_prestamo": 50,
    "can_auto_asignar": 30,
    "requieren_manual": 20
  }
}
```

**B) `POST /api/v1/pagos/sin-prestamo/asignar-automatico`**
- Auto-asigna `prestamo_id` a todos los pagos where:
  - `prestamo_id IS NULL` Y
  - Cliente tiene exactamente 1 crédito activo (estado = "APROBADO")
- Realiza commit en BD
- Retorna cantidad de pagos actualizados

```python
Respuesta:
{
  "asignados": 30,
  "no_asignables": 20,
  "mensaje": "Se asignaron 30 pagos automáticamente. 20 requieren intervención manual.",
  "detalles_asignados": [...],
  "detalles_no_asignables": [...]
}
```

#### 2. Frontend - Nuevo Componente

**Archivo**: `frontend/src/components/pagos/AsignarPrestamoAutomaticoDialog.tsx`

Interfaz con 3 pasos:

1. **Paso 1 - Carga de Sugerencias**: 
   - Botón "Cargar Sugerencias"
   - Muestra resumen: Total sin préstamo, pueden auto-asignarse, requieren manual

2. **Paso 2 - Previsualización**:
   - Tabla con primeras 10 sugerencias
   - Columnas: ID Pago, Cédula, Créditos Activos, Sugerencia, Acción (Auto/Manual)
   - Botón "Asignar X Préstamos"

3. **Paso 3 - Resultado**:
   - Confirmación de asignación completada
   - Resumen final: Asignados vs. Requieren Manual
   - Mensaje de resultado

#### 3. Integración en UI

**En el menú "Agregar pago"** (PagosList.tsx):
- Nuevo botón: **"Auto-asignar Préstamos"** (color ámbar)
- Abre el diálogo de asignación automática
- Al completar, actualiza la tabla de pagos automáticamente

---

## Cómo Usar

### Paso 1: Ir a la Tabla de Pagos
- Navega a https://rapicredit.onrender.com/pagos/pagos
- Verás la lista de pagos

### Paso 2: Abrir el Diálogo de Auto-Asignación
- Click en botón **"Agregar pago"** (azul, arriba a la derecha)
- En el menú desplegable, click en **"Auto-asignar Préstamos"** (ámbar)

### Paso 3: Cargar Sugerencias
- En el diálogo, click en **"Cargar Sugerencias"**
- Espera a que cargue (muestra resumen de pagos sin préstamo)

### Paso 4: Revisar y Asignar
- Revisa la tabla de sugerencias
- Los pagos verdes ("Auto") se asignarán automáticamente
- Los pagos amarillos ("Manual") requieren intervención (múltiples créditos, sin créditos)
- Click en **"Asignar X Préstamos"** para ejecutar

### Paso 5: Confirmar
- Se asignarán los préstamos automáticamente
- Verás un resumen final
- La tabla de pagos se actualizará automáticamente

---

## Comportamiento

### Auto-Asignación Automática
Se asigna `prestamo_id` cuando:
- ✅ El pago tiene `prestamo_id = NULL` Y
- ✅ El cliente (por cédula) tiene **exactamente 1** crédito activo (estado="APROBADO")

### Requiere Intervención Manual
No se asigna cuando:
- ❌ El cliente tiene **0 créditos activos** → Error de datos (cliente sin crédito)
- ❌ El cliente tiene **2+ créditos activos** → Ambiguo (¿cuál elegir?)
- ❌ La cédula está vacía → No se puede identificar al cliente

### En BD
- **Antes**: Pagos con `prestamo_id = NULL` mostraban "Sin asignar" en la tabla
- **Después**: Solo pagos que realmente requieren intervención quedan sin asignar

---

## Flujo Técnico

```
GET /api/v1/pagos/sin-prestamo/sugerir
├── SELECT * FROM pagos WHERE prestamo_id IS NULL
├── Para cada pago:
│   ├── Obtener cédula normalizada
│   ├── SELECT prestamos WHERE cliente.cedula = cedula AND estado = "APROBADO"
│   └── Evaluar: auto/manual según cantidad de créditos
└── Retornar sugerencias + resumen

POST /api/v1/pagos/sin-prestamo/asignar-automatico
├── SELECT * FROM pagos WHERE prestamo_id IS NULL
├── Para cada pago:
│   ├── Si cliente tiene exactamente 1 crédito activo:
│   │   └── UPDATE pagos SET prestamo_id = that_credit WHERE id = pago.id
│   └── Si no: guardar en "no_asignables"
└── COMMIT + Retornar resumen
```

---

## Validación Post-Asignación

Puedes validar que la asignación funcionó:

### En la BD (SQL):
```sql
-- Ver pagos sin préstamo ANTES
SELECT COUNT(*) FROM pagos WHERE prestamo_id IS NULL;

-- Ver pagos sin préstamo DESPUÉS
-- (Debería haber menos, los auto-asignables habrán sido resueltos)
SELECT COUNT(*) FROM pagos WHERE prestamo_id IS NULL;
```

### En la UI:
- Recarga https://rapicredit.onrender.com/pagos/pagos
- Los pagos que fueron auto-asignados ahora mostrarán el ID de crédito
- Solo los que requieren intervención mostrarán "Sin asignar"

---

## Casos de Uso Comunes

### Caso 1: Cliente con 1 Crédito Activo
```
Pago: ID=100, Cédula=V1234567, prestamo_id=NULL
Cliente V1234567 tiene 1 crédito activo: ID=456

✅ Auto-Asignación:
UPDATE pagos SET prestamo_id=456 WHERE id=100
```

### Caso 2: Cliente con Múltiples Créditos
```
Pago: ID=101, Cédula=V7654321, prestamo_id=NULL
Cliente V7654321 tiene 3 créditos activos: ID=789, 790, 791

❌ No se asigna (requiere intervención manual)
Usuario debe elegir manualmente en el diálogo de editar pago
```

### Caso 3: Cliente sin Créditos Activos
```
Pago: ID=102, Cédula=V9999999, prestamo_id=NULL
Cliente V9999999 tiene 0 créditos activos

❌ No se asigna (error de datos)
```

---

## Logs y Debugging

### Ver logs del backend:
```
Buscar en logs:
- "Error en GET /pagos/sin-prestamo/sugerir"
- "Error en POST /pagos/sin-prestamo/asignar-automatico"
- "Auto-asignación de prestamos: X asignados, Y no asignables"
```

### Errores Comunes:

**Error 500 en auto-asignación**
- Probable causa: FK violation (prestamo_id inválido)
- Validar que los IDs de crédito existen en `prestamos`

**Pagos sin asignar después de ejecutar**
- Esperado: Si tienen múltiples créditos o sin créditos
- Requerirá intervención manual

---

## Próximos Pasos (Opcional)

1. **Mejorar UI para múltiples créditos**: 
   - En el diálogo, permitir seleccionar cuál crédito asignar para pagos ambiguos

2. **Batch assignment con confirmación**:
   - Permitir pre-seleccionar créditos antes de asignar

3. **Audit log**:
   - Registrar quién y cuándo asignó préstamos automáticamente

4. **Validación de Excel**:
   - Rechazar en upload si cliente tiene múltiples créditos (sin indicar ID)
   - Proponer auto-asignación inmediatamente después

---

## Archivos Modificados

### Backend
- `backend/app/api/v1/endpoints/pagos.py`: +190 líneas (2 nuevos endpoints)

### Frontend
- `frontend/src/components/pagos/PagosList.tsx`: Integración del diálogo
- `frontend/src/components/pagos/AsignarPrestamoAutomaticoDialog.tsx`: Nuevo componente
- `frontend/src/services/pagoService.ts`: 2 nuevos métodos

---

## Testing Recomendado

### Test 1: Verificar carga de sugerencias
```
GET /api/v1/pagos/sin-prestamo/sugerir?page=1&per_page=20
Validar: Retorna lista de sugerencias con acciones correctas
```

### Test 2: Auto-asignación
```
POST /api/v1/pagos/sin-prestamo/asignar-automatico
Validar: Se actualizan pagos en BD, retorna cantidad asignada
```

### Test 3: UI - Flow completo
1. Ir a /pagos/pagos
2. Click "Agregar pago" → "Auto-asignar Préstamos"
3. Click "Cargar Sugerencias"
4. Verificar tabla muestra datos correctamente
5. Click "Asignar"
6. Verificar confirmación y recarga de tabla

---

## Soporte y Troubleshooting

Si tienes dudas o encuentras errores:

1. **Verificar BD**: 
   - ¿Hay pagos con `prestamo_id = NULL`?
   - ¿El cliente tiene créditos activos?

2. **Revisar logs**:
   - Backend: Buscar "Auto-asignación"
   - Frontend: Abrir Console (F12)

3. **Validar APIs**:
   - Usar Postman o curl para probar endpoints

4. **Recargar página**:
   - Si la tabla no se actualiza después de asignar

---

**Fin del documento de implementación**
