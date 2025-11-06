# 📋 Procedimiento de Registro de Pagos Individuales

## 📍 Ubicación

### Frontend
- **Componente:** `frontend/src/components/pagos/RegistrarPagoForm.tsx`
- **Página:** `frontend/src/pages/PagosPage.tsx`
- **Servicio:** `frontend/src/services/pagoService.ts`

### Backend
- **Endpoint:** `POST /api/v1/pagos/`
- **Archivo:** `backend/app/api/v1/endpoints/pagos.py` (función `crear_pago`, línea 596)
- **Schema:** `backend/app/schemas/pago.py` (clase `PagoCreate`)

---

## 🔄 Flujo Completo del Procedimiento

### 1. Frontend: Interfaz de Usuario

**Componente:** `RegistrarPagoForm.tsx`

#### Campos del Formulario:
1. **Cédula Cliente** (requerido)
   - Input de texto
   - Busca automáticamente préstamos cuando se ingresa la cédula (con debounce de 500ms)
   - Muestra cantidad de préstamos encontrados

2. **ID Crédito** (requerido si hay préstamos)
   - Select dropdown si hay préstamos disponibles
   - Input numérico si no hay préstamos
   - Auto-selecciona si solo hay 1 préstamo

3. **Fecha de Pago** (requerido)
   - Input tipo date
   - No permite fechas futuras
   - Valor por defecto: fecha actual

4. **Monto Pagado** (requerido)
   - Input numérico con decimales
   - Debe ser > 0
   - Validación: máximo $1,000,000

5. **Número de Documento** (requerido)
   - Input de texto
   - Se normaliza (trim espacios) antes de guardar

6. **Institución Bancaria** (opcional)
   - Input de texto

7. **Notas** (opcional)
   - Textarea

#### Validaciones en Frontend:
- ✅ Cédula requerida
- ✅ Si hay préstamos disponibles, ID de préstamo es obligatorio
- ✅ Cédula del pago debe coincidir con cédula del préstamo seleccionado
- ✅ Monto debe ser > 0 y < $1,000,000
- ✅ Número de documento requerido
- ✅ Fecha de pago no puede ser futura

---

### 2. Frontend: Servicio (`pagoService.ts`)

**Función:** `createPago(data: PagoCreate)`

```typescript
async createPago(data: PagoCreate): Promise<Pago> {
  const response = await apiClient.post<Pago>('/api/v1/pagos/', data)
  return response
}
```

**Endpoint llamado:** `POST /api/v1/pagos/`

**Datos enviados:**
```json
{
  "cedula": "V12345678",
  "prestamo_id": 123,
  "fecha_pago": "2025-01-15",
  "monto_pagado": 500.00,
  "numero_documento": "DOC001",
  "institucion_bancaria": "Banco de Venezuela",
  "notas": "Pago parcial"
}
```

---

### 3. Backend: Endpoint (`pagos.py`)

**Función:** `crear_pago()` (línea 596)

#### Paso 1: Validación de Cliente
```python
cliente = db.query(Cliente).filter(Cliente.cedula == pago_data.cedula).first()
if not cliente:
    raise HTTPException(status_code=404, detail="Cliente no encontrado")
```

#### Paso 2: Preparación de Datos
```python
pago_dict = pago_data.model_dump()
pago_dict["usuario_registro"] = current_user.email
pago_dict["fecha_registro"] = datetime.now()

# Filtrar campos válidos
campos_validos = [col.key for col in Pago.__table__.columns]
pago_dict = {k: v for k, v in pago_dict.items() if k in campos_validos}
```

#### Paso 3: Crear Registro en Tabla `pagos`
```python
nuevo_pago = Pago(**pago_dict)
db.add(nuevo_pago)
db.commit()
db.refresh(nuevo_pago)
```

**Resultado:** Se crea **1 registro** en la tabla `pagos` con:
- `id`: Auto-incrementado
- `cedula`: Del formulario
- `prestamo_id`: Del formulario (puede ser NULL)
- `fecha_pago`: Del formulario
- `monto_pagado`: Del formulario
- `numero_documento`: Del formulario (normalizado, sin espacios)
- `usuario_registro`: Email del usuario autenticado
- `fecha_registro`: Fecha/hora actual
- `estado`: "PAGADO" (por defecto)
- `conciliado`: False (por defecto)
- `activo`: True (por defecto)

#### Paso 4: Registrar Auditoría
```python
registrar_auditoria_pago(
    pago_id=nuevo_pago.id,
    usuario=current_user.email,
    accion="CREATE",
    campo_modificado="pago_completo",
    valor_anterior="N/A",
    valor_nuevo=f"Pago de {pago_data.monto_pagado} registrado",
    db=db,
)
```

#### Paso 5: Aplicar Pago a Cuotas
```python
try:
    cuotas_completadas = aplicar_pago_a_cuotas(nuevo_pago, db, current_user)
    logger.info(f"✅ [crear_pago] Pago ID {nuevo_pago.id}: {cuotas_completadas} cuota(s) completada(s)")
except Exception as e:
    logger.error(f"❌ [crear_pago] Error aplicando pago a cuotas: {str(e)}")
    # No fallar el registro del pago si falla la aplicación a cuotas
    cuotas_completadas = 0
```

**Función `aplicar_pago_a_cuotas()`:**
- Verifica que la cédula del pago coincida con la cédula del préstamo
- Busca cuotas pendientes del préstamo (ordenadas por fecha de vencimiento, más antiguas primero)
- Aplica el monto a las cuotas más antiguas primero
- Actualiza `cuotas.total_pagado`, `cuotas.capital_pagado`, `cuotas.interes_pagado`
- Actualiza `cuotas.estado` (PAGADO, PARCIAL, PENDIENTE, ATRASADO, ADELANTADO)
- Si el monto cubre una cuota completa y sobra, aplica el exceso a la siguiente cuota

#### Paso 6: Actualizar Estado del Pago
```python
if nuevo_pago.prestamo_id and cuotas_completadas == 0:
    nuevo_pago.estado = "PARCIAL"  # Abono parcial
elif nuevo_pago.prestamo_id and cuotas_completadas > 0:
    nuevo_pago.estado = "PAGADO"  # Completó al menos una cuota
# Si no tiene prestamo_id, mantener "PAGADO" (por defecto)
```

#### Paso 7: Confirmar y Retornar
```python
db.commit()
db.refresh(nuevo_pago)
return nuevo_pago
```

---

## 📊 Resumen del Procedimiento

```
1. Usuario abre formulario de registro de pago
   └─> Componente: RegistrarPagoForm.tsx

2. Usuario completa formulario
   ├─> Cédula → Busca préstamos automáticamente
   ├─> Selecciona préstamo (si hay)
   ├─> Ingresa fecha, monto, número de documento
   └─> Validaciones en frontend

3. Usuario hace clic en "Registrar Pago"
   └─> pagoService.createPago(formData)

4. Frontend envía POST /api/v1/pagos/
   └─> Backend: crear_pago()

5. Backend valida y crea registro
   ├─> Valida cliente existe
   ├─> Crea registro en tabla pagos
   ├─> Registra auditoría
   ├─> Aplica pago a cuotas (si tiene prestamo_id)
   └─> Actualiza estado del pago

6. Backend retorna pago creado
   └─> Frontend muestra mensaje de éxito

7. Frontend cierra formulario y actualiza lista
   └─> onSuccess() → Refresca lista de pagos
```

---

## ✅ Características Importantes

### 1. Registro Individual
- **Cada pago = 1 registro** en la tabla `pagos`
- **NO se agrupan** pagos por cédula
- **NO se suman** montos de la misma cédula

### 2. Aplicación Automática a Cuotas
- Si el pago tiene `prestamo_id`, se aplica automáticamente a las cuotas
- Se aplica a las cuotas más antiguas primero
- Se distribuye proporcionalmente entre capital e interés
- Si cubre una cuota completa y sobra, el exceso va a la siguiente cuota

### 3. Validaciones
- **Frontend:** Validaciones de UI (campos requeridos, formatos, rangos)
- **Backend:** Validación de existencia de cliente
- **Backend:** Validación de coincidencia de cédulas (pago vs préstamo)

### 4. Manejo de Errores
- Si falla la aplicación a cuotas, el pago **SÍ se registra** pero las cuotas no se actualizan
- El usuario puede aplicar el pago manualmente después usando el endpoint `POST /pagos/{pago_id}/aplicar-cuotas`

---

## 🔗 Endpoints Relacionados

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/pagos/` | POST | Registrar pago individual |
| `/api/v1/pagos/{pago_id}/aplicar-cuotas` | POST | Aplicar pago a cuotas manualmente |
| `/api/v1/pagos/{pago_id}` | PUT | Actualizar pago |
| `/api/v1/pagos/` | GET | Listar pagos (con filtros) |

---

## 📝 Ejemplo de Uso

### Request (Frontend → Backend)
```json
POST /api/v1/pagos/
{
  "cedula": "V12345678",
  "prestamo_id": 123,
  "fecha_pago": "2025-01-15",
  "monto_pagado": 500.00,
  "numero_documento": "DOC001",
  "institucion_bancaria": "Banco de Venezuela",
  "notas": "Pago parcial de cuota 1"
}
```

### Response (Backend → Frontend)
```json
{
  "id": 456,
  "cedula": "V12345678",
  "prestamo_id": 123,
  "fecha_pago": "2025-01-15T00:00:00",
  "monto_pagado": 500.00,
  "numero_documento": "DOC001",
  "institucion_bancaria": "Banco de Venezuela",
  "notas": "Pago parcial de cuota 1",
  "estado": "PARCIAL",
  "conciliado": false,
  "usuario_registro": "usuario@example.com",
  "fecha_registro": "2025-01-15T10:30:00",
  "activo": true
}
```

---

## 🎯 Conclusión

**Los pagos individuales se registran:**
1. **Frontend:** Componente `RegistrarPagoForm.tsx` en la página `PagosPage`
2. **Backend:** Endpoint `POST /api/v1/pagos/` (función `crear_pago()`)
3. **Base de Datos:** Tabla `pagos` (1 registro por pago)

**El procedimiento es:**
- Usuario completa formulario → Frontend valida → Backend valida y crea registro → Backend aplica a cuotas → Retorna resultado

