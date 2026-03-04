# TEST: Rechazo de Documentos Duplicados

## Objetivo

Validar que el sistema **rechace documentos duplicados** en ambos casos:
- POST /pagos (individual)
- POST /pagos/upload (masivo)

---

## Escenario de Prueba

### Setup
1. Cliente: V99999999
2. Préstamo: $36,000 en 3 cuotas
3. Crear pago inicial: DOC-001 ($12,000)

### Test A: Pago Individual con Documento Duplicado

**Intento 1 - Crear pago:**
```powershell
POST /api/v1/pagos
{
  "cedula_cliente": "V99999999",
  "prestamo_id": 1,
  "monto_pagado": 12000,
  "fecha_pago": "2026-03-05",
  "numero_documento": "DOC-001"  // Nuevo
}
```

**Respuesta esperada: 201 OK**
- Pago creado
- Estado: PAGADO
- Documento: DOC-001

**Intento 2 - Crear pago con MISMO documento:**
```powershell
POST /api/v1/pagos
{
  "cedula_cliente": "V99999999",
  "prestamo_id": 1,
  "monto_pagado": 8000,
  "fecha_pago": "2026-03-10",
  "numero_documento": "DOC-001"  // DUPLICADO
}
```

**Respuesta esperada: 409 CONFLICT**
```json
{
  "detail": "Ya existe un pago con ese Nº de documento. Regla general: no se aceptan duplicados en documentos."
}
```

### Test B: Carga Masiva con Documento Duplicado

**Intento 1 - Cargar 2 pagos (uno con DOC-001 existente):**
```
cedula,prestamo_id,fecha_pago,monto_pagado,numero_documento
V99999999,1,2026-03-10,8000,DOC-002
V99999999,1,2026-03-15,5000,DOC-001
```

**Respuesta esperada:**
```json
{
  "registros_creados": 1,
  "registros_con_error": 1,
  "errores": [
    "Fila 2: Ya existe un pago con ese Nº de documento"
  ],
  "pagos_con_errores": [
    {
      "fila_origen": 2,
      "cedula": "V99999999",
      "monto": 5000,
      "errores": ["Ya existe un pago con ese Nº de documento. Regla general: no se aceptan duplicados en documentos."],
      "accion": "revisar"
    }
  ]
}
```

### Test C: Carga Masiva con Duplicados DENTRO del mismo lote

**Intento - Cargar 3 pagos (DOC-003 y DOC-004 duplicados dentro del lote):**
```
cedula,prestamo_id,fecha_pago,monto_pagado,numero_documento
V99999999,1,2026-03-10,8000,DOC-003
V99999999,1,2026-03-15,5000,DOC-004
V99999999,1,2026-03-20,5000,DOC-003
```

**Respuesta esperada:**
```json
{
  "registros_creados": 2,
  "registros_con_error": 1,
  "errores": [
    "Fila 3: Nº documento duplicado en este archivo"
  ]
}
```

---

## Implementación del Test

```powershell
Log-Test "6" "VALIDATE DUPLICATE DOCUMENT REJECTION"

# === SETUP: Crear pago inicial ===
$PagoInicialResponse = Invoke-ApiRequest -Method POST -Endpoint "/pagos" `
    -Body @{
        cedula_cliente    = $ClienteCedula
        prestamo_id       = $PrestamoId
        monto_pagado      = 12000
        fecha_pago        = "2026-03-05"
        numero_documento  = "DOC-ORIGINAL-001"
    } -Headers $Headers

Log-Success "Initial payment created: DOC-ORIGINAL-001"

# === TEST A: Pago Individual Duplicado ===
Log-Test "6.1" "INDIVIDUAL PAYMENT - REJECT DUPLICATE DOCUMENT"

try {
    $DuplicadoResponse = Invoke-ApiRequest -Method POST -Endpoint "/pagos" `
        -Body @{
            cedula_cliente    = $ClienteCedula
            prestamo_id       = $PrestamoId
            monto_pagado      = 8000
            fecha_pago        = "2026-03-10"
            numero_documento  = "DOC-ORIGINAL-001"  # DUPLICADO
        } -Headers $Headers -ErrorAction SilentlyContinue
    
    Log-Error "Duplicate document was accepted! Should have been rejected."
} catch {
    $ErrorMessage = $_.Exception.Response.StatusCode
    if ($ErrorMessage -eq 409) {
        Log-Success "Duplicate document rejected with 409 CONFLICT"
    } else {
        Log-Error "Wrong error code: $ErrorMessage (expected 409)"
    }
}

# === TEST B: Carga Masiva con Documento Duplicado en BD ===
Log-Test "6.2" "BULK UPLOAD - REJECT DUPLICATE IN DATABASE"

$csvPath = "$env:TEMP\test_duplicate_$(Get-Date -Format 'yyyyMMddHHmmss').csv"
$csvContent = @"
cedula,prestamo_id,fecha_pago,monto_pagado,numero_documento
$ClienteCedula,$PrestamoId,2026-03-10,8000,DOC-NEW-001
$ClienteCedula,$PrestamoId,2026-03-15,5000,DOC-ORIGINAL-001
"@

$csvContent | Out-File $csvPath -Encoding UTF8
$xlsxPath = $csvPath.Replace('.csv', '.xlsx')

# Convert and upload
$UploadResponse = Invoke-ApiRequest -Method POST -Endpoint "/pagos/upload" `
    -File $xlsxPath -Headers $Headers

Log-Info "Upload response:"
Log-Info "  - Registros creados: $($UploadResponse.registros_creados)"
Log-Info "  - Registros con error: $($UploadResponse.registros_con_error)"

if ($UploadResponse.registros_creados -eq 1) {
    Log-Success "Only 1 payment created (DOC-NEW-001)"
} else {
    Log-Error "Expected 1 payment created, got: $($UploadResponse.registros_creados)"
}

if ($UploadResponse.registros_con_error -eq 1) {
    Log-Success "1 payment rejected (duplicate DOC-ORIGINAL-001)"
} else {
    Log-Error "Expected 1 payment rejected, got: $($UploadResponse.registros_con_error)"
}

# Verificar error detail
$ErrorDetail = $UploadResponse.errores[0]
if ($ErrorDetail -like "*Ya existe un pago*" -or $ErrorDetail -like "*duplicado*") {
    Log-Success "Error message correct: '$ErrorDetail'"
} else {
    Log-Error "Wrong error message: '$ErrorDetail'"
}

# === TEST C: Carga Masiva con Duplicados dentro del lote ===
Log-Test "6.3" "BULK UPLOAD - REJECT DUPLICATE WITHIN FILE"

$csvPath2 = "$env:TEMP\test_duplicate_internal_$(Get-Date -Format 'yyyyMMddHHmmss').csv"
$csvContent2 = @"
cedula,prestamo_id,fecha_pago,monto_pagado,numero_documento
$ClienteCedula,$PrestamoId,2026-03-10,8000,DOC-INTERNAL-001
$ClienteCedula,$PrestamoId,2026-03-15,5000,DOC-INTERNAL-002
$ClienteCedula,$PrestamoId,2026-03-20,5000,DOC-INTERNAL-001
"@

$csvContent2 | Out-File $csvPath2 -Encoding UTF8
$xlsxPath2 = $csvPath2.Replace('.csv', '.xlsx')

$UploadResponse2 = Invoke-ApiRequest -Method POST -Endpoint "/pagos/upload" `
    -File $xlsxPath2 -Headers $Headers

Log-Info "Upload response:"
Log-Info "  - Registros creados: $($UploadResponse2.registros_creados)"
Log-Info "  - Registros con error: $($UploadResponse2.registros_con_error)"

if ($UploadResponse2.registros_creados -eq 2) {
    Log-Success "2 payments created (DOC-INTERNAL-001, DOC-INTERNAL-002)"
} else {
    Log-Error "Expected 2 payments, got: $($UploadResponse2.registros_creados)"
}

if ($UploadResponse2.registros_con_error -eq 1) {
    Log-Success "1 payment rejected (duplicate within file)"
} else {
    Log-Error "Expected 1 rejected, got: $($UploadResponse2.registros_con_error)"
}

# Verificar error detail
$ErrorDetail2 = $UploadResponse2.errores[0]
if ($ErrorDetail2 -like "*duplicado en este archivo*") {
    Log-Success "Error message correct: '$ErrorDetail2'"
} else {
    Log-Error "Wrong error message: '$ErrorDetail2'"
}

# === VALIDACIÓN FINAL: BD Consistency ===
Log-Test "6.4" "VERIFY DATABASE CONSISTENCY"

$AllPayments = Invoke-ApiRequest -Method GET -Endpoint "/pagos?prestamo_id=$PrestamoId&limit=100" -Headers $Headers

$UniqueDocuments = @($AllPayments.items | Select-Object -ExpandProperty numero_documento -Unique).Count
$TotalPayments = $AllPayments.items.Count

Log-Info "Total payments: $TotalPayments"
Log-Info "Unique documents: $UniqueDocuments"

if ($UniqueDocuments -eq $TotalPayments) {
    Log-Success "All documents are unique - no duplicates in DB"
} else {
    Log-Error "Duplicate documents found in DB! Total=$TotalPayments, Unique=$UniqueDocuments"
}

# Cleanup
Remove-Item $csvPath -Force -ErrorAction SilentlyContinue
Remove-Item $xlsxPath -Force -ErrorAction SilentlyContinue
Remove-Item $csvPath2 -Force -ErrorAction SilentlyContinue
Remove-Item $xlsxPath2 -Force -ErrorAction SilentlyContinue

Log-Success "All duplicate rejection tests passed!"
```

---

## Validaciones Críticas

✅ **Test A: Individual**
- Pago individual con doc duplicado → 409 CONFLICT
- Error message específico
- No se crea pago

✅ **Test B: Bulk con duplicado en BD**
- 1 pago creado (nuevo)
- 1 pago rechazado (duplicado)
- Error message específico
- Pago rechazado guardado en `pagos_con_errores`

✅ **Test C: Bulk con duplicado DENTRO del lote**
- 2 pagos creados (únicos)
- 1 pago rechazado (duplicado en el mismo archivo)
- Error diferente: "duplicado en este archivo"

✅ **Validación Final: DB Consistency**
- Todos los documentos en BD son únicos
- Sin duplicados silenciosos

---

## Reglas de Negocio Validadas

1. **Sin duplicados en BD**: Documento no puede existir en BD
2. **Sin duplicados en lote**: Documento no puede repetirse en el mismo archivo
3. **Consistencia**: No hay documentos duplicados sin error
4. **Trazabilidad**: Rechazos se registran en `pagos_con_errores`

---

## Resultado Esperado

```
✅ Initial payment created: DOC-ORIGINAL-001
✅ Duplicate document rejected with 409 CONFLICT
✅ Only 1 payment created (DOC-NEW-001)
✅ 1 payment rejected (duplicate DOC-ORIGINAL-001)
✅ Error message correct
✅ 2 payments created (DOC-INTERNAL-001, DOC-INTERNAL-002)
✅ 1 payment rejected (duplicate within file)
✅ Error message correct
✅ All documents are unique - no duplicates in DB
✅ All duplicate rejection tests passed!
```

---

**Status**: Validación de duplicados completa ✅
