# 🔴 Error 500 en POST /pagos - Debugging Guide

## Análisis del Error

**Endpoint**: `POST /api/v1/pagos`  
**Status**: 500 Internal Server Error  
**Ocurre en**: Fase 4 del test E2E después de crear cliente y préstamo  

---

## Posibles Causas (en orden de probabilidad)

### 1. ❌ **FK Violation: cedula no existe en clientes** (ALTA PROBABILIDAD)

**Síntoma**: Error 500 sin detalles en respuesta

**Causa**: 
- El test crea un cliente con cédula dinámica (ej: V151800)
- Al crear el pago, intenta usar la misma cédula
- FK `fk_pagos_cedula` valida que cedula existe en clientes
- Si la cédula no se guardó correctamente o hay mismatch, FK violation → 500

**Verificación**:
```sql
-- Ejecutar en tu BD de Render
SELECT cedula FROM public.clientes WHERE cedula = 'V151800';
-- Si no retorna nada, la cédula no existe

SELECT cedula FROM public.pagos WHERE numero_documento = 'BNC-20260304-001';
-- Si retorna V151800 pero no existe en clientes → FK violation
```

**Solución**:
1. Asegurar que cliente se crea y se commitea **antes** de usar su cédula en pago
2. Verificar que la cédula en el pago coincida exactamente (case-sensitive)
3. Usar cédula conocida en test (ej: V12345678)

---

### 2. ⚠️ **Error en _aplicar_pago_a_cuotas_interno no capturado** (MEDIA PROBABILIDAD)

**Síntoma**: Error durante aplicación FIFO de pagos

**Causa**:
```python
try:
    _aplicar_pago_a_cuotas_interno(row, db)  # ← Error aquí
    row.estado = "PAGADO"
    db.commit()
except Exception as e:
    logger.warning("...")  # ← Debería capturat
```

Aunque hay try-except, algo podría escapar o haber error **antes** del try (en línea 1452 `db.commit()`)

**Debugging**:
- Revisar logs de Render para stack trace completo
- Buscar "Traceback" en Deploy logs

---

### 3. 📝 **Falta campo requerido en payload** (BAJA PROBABILIDAD)

**Schema esperado**:
```python
class PagoCreate(BaseModel):
    cedula_cliente: str  # ← Required!
    prestamo_id: Optional[int] = None
    fecha_pago: date  # ← Required!
    monto_pagado: Decimal  # ← Required!
    numero_documento: str  # ← Required!
    institucion_bancaria: Optional[str] = None
    notas: Optional[str] = None
    conciliado: Optional[bool] = None
```

**Verificación**: El test envía todos los campos requeridos, así que esto es **baja probabilidad**.

---

### 4. 🔗 **Relación prestamo_id inválida** (BAJA PROBABILIDAD)

**Causa**: 
- prestamo_id = 4760 no existe en BD
- FK `fk_pagos_prestamo` se viola

**Verificación**:
```sql
SELECT id FROM public.prestamos WHERE id = 4760;
-- Debe retornar el préstamo
```

El test muestra que el préstamo **se creó exitosamente**, así que esto es **baja probabilidad**.

---

## Plan de Debugging (Paso a Paso)

### Step 1: Verificar BD Post-Test
Después de ejecutar el test hasta el error, ejecuta en tu cliente psql:

```sql
-- Ver clientes creados
SELECT id, cedula, nombres FROM public.clientes 
WHERE cedula LIKE 'V15%' ORDER BY id DESC LIMIT 5;

-- Ver préstamos creados
SELECT id, cliente_id, total_financiamiento, estado FROM public.prestamos 
WHERE id > 4750 ORDER BY id DESC LIMIT 5;

-- Ver pagos creados (debería estar vacío)
SELECT id, cedula, prestamo_id, monto_pagado FROM public.pagos 
WHERE numero_documento LIKE 'BNC-202603%';

-- Ver si hay FKs activos
SELECT constraint_name, table_name, column_name
FROM information_schema.key_column_usage
WHERE table_name IN ('pagos', 'prestamos', 'cuotas')
ORDER BY table_name, column_name;
```

### Step 2: Revisar Logs de Render
1. Ve a https://dashboard.render.com
2. Selecciona tu servicio
3. Busca en logs el error exacto (Ctrl+F "500" o "Exception")
4. Busca "Traceback" completo

### Step 3: Test FK directamente
Ejecuta `test_fk_pagos_cedula.sql` en tu BD:

```sql
-- Esto te dirá exactamente si el FK es el problema
```

---

## Solución Rápida (Si es FK)

**Opción A: Usar cédula conocida en test**
```powershell
# En lugar de generar cédula dinámica:
$ClienteCedula = "V12345678"  # Cédula fija
```

**Opción B: Asegurar que cliente se guarda primero**
```python
# En endpoint
db.add(row)
db.flush()  # ← Asegurar que el cliente está en la sesión
db.commit()

# Ahora crear pago con esa cédula
pago = Pago(cedula_cliente=cliente.cedula, ...)
db.add(pago)
db.commit()
```

**Opción C: Deshabilitar FK temporalmente (debugging)**
```sql
ALTER TABLE pagos DISABLE TRIGGER ALL;
-- Crear pago
-- Ver si se crea
ALTER TABLE pagos ENABLE TRIGGER ALL;
```

---

## Siguiente Acción

1. **Ejecuta el test SQL** (`test_fk_pagos_cedula.sql`)
2. **Revisa los logs** de Render para el error completo
3. **Aplica solución** basada en lo que encuentres
4. **Re-ejecuta test** e2e

---

## Notas Técnicas

### FK Constraint Actual:
```sql
ALTER TABLE public.pagos
ADD CONSTRAINT fk_pagos_cedula
FOREIGN KEY (cedula)
REFERENCES public.clientes(cedula)
ON DELETE SET NULL
ON UPDATE CASCADE;
```

### Implicaciones:
- `cedula` en pagos debe existir en `clientes.cedula`
- Si no existe → **Violation** → 500
- ON DELETE SET NULL: Si cliente se elimina, pago.cedula → NULL (OK)
- ON UPDATE CASCADE: Si cedula cambia en cliente, se actualiza en pagos (OK)

---

## Prueba de Concepto

Para confirmar que es FK, corre esto:

```powershell
# En PowerShell
$password = "51290debb83a53b1b1c3bd476311fccc"
$email = "itmaster@rapicreditca.com"
$baseUrl = "https://rapicredit.onrender.com/api/v1"

# 1. Login
$login = @{
    email = $email
    password = $password
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "$baseUrl/auth/login" `
    -Method POST -ContentType "application/json" -Body $login

$token = $response.access_token
$headers = @{ "Authorization" = "Bearer $token" }

# 2. Crear cliente con cédula **CONOCIDA**
$cliente = @{
    cedula = "V99999999"
    nombres = "Test Pago"
    apellidos = "Test"
    email = "test@test.com"
    telefono = "04161234567"
    direccion = "Test"
    fecha_nacimiento = "1990-01-01"
    ocupacion = "Test"
    estado = "ACTIVO"
    usuario_registro = $email
    notas = "Test"
} | ConvertTo-Json

$clienteResp = Invoke-RestMethod -Uri "$baseUrl/clientes" `
    -Method POST -ContentType "application/json" -Body $cliente -Headers $headers

# 3. Crear pago con la **MISMA** cédula
$pago = @{
    cedula_cliente = "V99999999"  # ← IMPORTANTE: Debe coincidir
    monto_pagado = 1000
    fecha_pago = "2026-03-04"
    numero_documento = "TEST-001"
} | ConvertTo-Json

$pagoResp = Invoke-RestMethod -Uri "$baseUrl/pagos" `
    -Method POST -ContentType "application/json" -Body $pago -Headers $headers

Write-Host $pagoResp
```

Si esto funciona → FK está OK → Problema está en otra parte  
Si falla con 500 → FK es el culpable

---

## Conclusión

El error 500 **casi seguramente es una FK violation** en la cédula. La solución es:

1. **Usar cédula fija en test** (no generada)
2. **Verificar FK existe** y está activo
3. **Confirmar cliente está en BD** antes de crear pago
4. **Validar case-sensitivity** (V15 vs v15)
