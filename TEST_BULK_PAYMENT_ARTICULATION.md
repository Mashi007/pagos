# Test: Carga Masiva de Pagos con Articulación Automática a Cuotas

## Flujo Completo

1. **Crear Cliente** → V99999999
2. **Crear Préstamo** → 12 cuotas de $8,333.33 cada una
3. **Cargar Pagos desde Excel**:
   - Pago 1: $8,333.33 (cuota 1)
   - Pago 2: $16,666.66 (cuota 2 + 3)
   - Pago 3: $8,333.33 (cuota 4)
4. **Validar Articulación**:
   - Respuesta incluya `pagos_articulados: 3`
   - Respuesta incluya `cuotas_aplicadas: 4`
   - Cuotas 1-4 estado PAGADO

## Endpoint Test

```powershell
POST /api/v1/pagos/upload
Content-Type: multipart/form-data

File: payments.xlsx
Headers: cedula | prestamo_id | fecha_pago | monto_pagado | numero_documento
```

## Excel Esperado

| cedula    | prestamo_id | fecha_pago | monto_pagado | numero_documento |
|-----------|-------------|------------|--------------|------------------|
| V99999999 | {loan_id}   | 2026-03-05 | 8333.33      | DOC-001          |
| V99999999 | {loan_id}   | 2026-03-12 | 16666.66     | DOC-002          |
| V99999999 | {loan_id}   | 2026-03-19 | 8333.33      | DOC-003          |

## Respuesta Esperada

```json
{
  "registros_creados": 3,
  "registros_con_error": 0,
  "cuotas_aplicadas": 4,
  "pagos_articulados": 3,  // [NUEVA] Se articularon 3 pagos
  "filas_omitidas": 0
}
```

## Validación en BD

```sql
-- Verificar cuotas están PAGADO
SELECT numero_cuota, estado, total_pagado, monto
FROM public.cuotas
WHERE prestamo_id = {loan_id}
ORDER BY numero_cuota;

-- Verificar pagos están PAGADO
SELECT id, monto_pagado, estado, numero_documento
FROM public.pagos
WHERE prestamo_id = {loan_id}
ORDER BY id;

-- Verificar articulación en cuota_pagos
SELECT cuota_id, pago_id, monto_aplicado, orden_aplicacion
FROM public.cuota_pagos
WHERE pago_id IN (SELECT id FROM public.pagos WHERE prestamo_id = {loan_id})
ORDER BY pago_id, orden_aplicacion;
```

## Implementación en Test Script

```powershell
# Después de crear préstamo y cuotas...

Log-Test "4.2" "UPLOAD BULK PAYMENTS AND VERIFY ARTICULATION"

# Crear archivo CSV temporal
$csvPath = "$env:TEMP\test_payments_$(Get-Date -Format 'yyyyMMddHHmmss').csv"
$csvContent = @"
cedula,prestamo_id,fecha_pago,monto_pagado,numero_documento
V99999999,$PrestamoId,2026-03-05,8333.33,DOC-001
V99999999,$PrestamoId,2026-03-12,16666.66,DOC-002
V99999999,$PrestamoId,2026-03-19,8333.33,DOC-003
"@

$csvContent | Out-File $csvPath -Encoding UTF8

# Convertir a Excel
$xlsxPath = $csvPath.Replace('.csv', '.xlsx')
# (Use Excel COM o convertir a XLSX)

# Upload
$uploadResponse = Invoke-ApiRequest -Method POST -Endpoint "/pagos/upload" `
    -File $xlsxPath -Headers $Headers

# Validaciones
if ($uploadResponse.pagos_articulados -eq 3) {
    Log-Success "All 3 payments articulated"
} else {
    Log-Error "Expected 3 payments articulated, got $($uploadResponse.pagos_articulados)"
}

if ($uploadResponse.cuotas_aplicadas -eq 4) {
    Log-Success "All 4 cuotas applied"
} else {
    Log-Error "Expected 4 cuotas applied, got $($uploadResponse.cuotas_aplicadas)"
}

# Verificar estados en BD
$QuotasResponse = Invoke-ApiRequest -Method GET -Endpoint "/prestamos/$PrestamoId/cuotas" -Headers $Headers

$PaidQuotas = @($QuotasResponse | Where-Object { $_.estado -eq "PAGADO" }).Count
if ($PaidQuotas -eq 4) {
    Log-Success "4 cuotas marked as PAGADO"
} else {
    Log-Error "Expected 4 PAGADO cuotas, got $PaidQuotas"
}

# Cleanup
Remove-Item $csvPath -Force -ErrorAction SilentlyContinue
Remove-Item $xlsxPath -Force -ErrorAction SilentlyContinue
```

## Validaciones Clave

- ✅ Pagos creados: 3
- ✅ Pagos articulados: 3
- ✅ Cuotas aplicadas: 4
- ✅ Estados: Cuotas 1-4 = PAGADO
- ✅ Articulación en cuota_pagos: orden_aplicacion incrementa
- ✅ FIFO: Se aplican a cuota más antigua primero

## Status

Esta es la **validación final** que cierra el ciclo completo:
Cliente → Préstamo → Cuotas → Pagos (Carga Excel) → Articulación → Cuotas Pagadas
