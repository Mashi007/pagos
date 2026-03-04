# 📋 INSTRUCCIONES DE EJECUCIÓN - CARGA MASIVA DE CLIENTES

## 1️⃣ REQUISITOS PREVIOS

### Backend
- [x] FastAPI running
- [x] SQLAlchemy ORM
- [x] openpyxl library (`pip install openpyxl`)
- [x] Database configurado

### Frontend
- [x] React 18+
- [x] TypeScript
- [x] react-query
- [x] lucide-react
- [x] sonner (toasts)

---

## 2️⃣ PREPARAR BASE DE DATOS

### Opción A: Ejecutar migración SQL manual

En **psql**, **DBeaver** o **SQL Editor Render**:

```sql
-- Archivo: backend/scripts/024_create_clientes_con_errores.sql
-- Copiar y pegar contenido completo

CREATE TABLE IF NOT EXISTS public.clientes_con_errores (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(20),
    nombres VARCHAR(100),
    telefono VARCHAR(100),
    email VARCHAR(100),
    direccion TEXT,
    fecha_nacimiento VARCHAR(50),
    ocupacion VARCHAR(100),
    estado VARCHAR(30) DEFAULT 'PENDIENTE',
    errores_descripcion TEXT,
    observaciones TEXT,
    fila_origen INTEGER,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usuario_registro VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_clientes_con_errores_cedula 
    ON public.clientes_con_errores(cedula);
CREATE INDEX IF NOT EXISTS idx_clientes_con_errores_email 
    ON public.clientes_con_errores(email);
CREATE INDEX IF NOT EXISTS idx_clientes_con_errores_estado 
    ON public.clientes_con_errores(estado);

-- Verificar creación
SELECT COUNT(*) as tabla_creada FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'clientes_con_errores';
-- Resultado esperado: 1
```

### Opción B: SQLAlchemy auto-create (en desarrollo)

```python
from app.core.database import engine, Base
from app.models.cliente_con_error import ClienteConError

# En desarrollo/testing:
Base.metadata.create_all(bind=engine)
```

---

## 3️⃣ VERIFICAR INSTALACIÓN

### Verificar tabla existe:
```sql
SELECT * FROM information_schema.columns 
WHERE table_name = 'clientes_con_errores';
```

### Verificar endpoint:
```bash
# En backend folder
curl -X GET "https://tu-api/clientes/revisar/lista" \
  -H "Authorization: Bearer $TOKEN"
# Respuesta esperada: {"total": 0, "page": 1, "items": []}
```

---

## 4️⃣ PREPARAR ARCHIVO EXCEL PARA TESTING

### Formato requerido (7 columnas):

```
| Cédula      | Nombres              | Dirección         | Fecha Nacimiento | Ocupación  | Correo            | Teléfono     |
|-------------|----------------------|-------------------|------------------|------------|-------------------|--------------|
| V19567663   | Juan García López    | Calle 1 #100      | 1990-05-15       | Abogado    | juan@example.com  | +58-414-555  |
| E12345678   | María Rodríguez      | Av. 2 #200        | 1985-12-20       | Ingeniera  | maria@example.com | +58-416-666  |
| J98765432   | Carlos Mendez        | Calle 3 #300      | 1992-03-10       | Contador   | carlos@example.com| +58-424-777  |
| INVALIDA    | DUPLICADO_CEDULA     | Apto 4            | 1995-01-01       | Otros      | otro@example.com  | +58-414-888  |
| V19567663   | Mismo Cliente        | Otra Dirección    | 2000-06-06       | Vendedor   | otro2@example.com | +58-414-999  |
```

### Crear archivo de test (PowerShell):

```powershell
# test_clientes_upload.ps1
$excel = New-Object -ComObject Excel.Application
$workbook = $excel.Workbooks.Add()
$sheet = $workbook.ActiveSheet

# Headers
$sheet.Cells.Item(1, 1) = "Cédula"
$sheet.Cells.Item(1, 2) = "Nombres"
$sheet.Cells.Item(1, 3) = "Dirección"
$sheet.Cells.Item(1, 4) = "Fecha Nacimiento"
$sheet.Cells.Item(1, 5) = "Ocupación"
$sheet.Cells.Item(1, 6) = "Correo"
$sheet.Cells.Item(1, 7) = "Teléfono"

# Datos de prueba
$data = @(
    @("V19567663", "Juan García López", "Calle 1 #100", "1990-05-15", "Abogado", "juan.garcia@test.com", "+58-414-555-0001"),
    @("E12345678", "María Rodríguez", "Av. 2 #200", "1985-12-20", "Ingeniera", "maria.rodriguez@test.com", "+58-416-666-0002"),
    @("J98765432", "Carlos Mendez", "Calle 3 #300", "1992-03-10", "Contador", "carlos.mendez@test.com", "+58-424-777-0003"),
    @("INVALIDA", "Error Cedula", "Apto 4", "1995-01-01", "Otros", "error@test.com", "+58-414-888-0004"),
    @("V19567663", "Cedula Duplicada", "Otra Dirección", "2000-06-06", "Vendedor", "duplicada@test.com", "+58-414-999-0005")
)

$row = 2
foreach ($d in $data) {
    for ($col = 1; $col -le 7; $col++) {
        $sheet.Cells.Item($row, $col) = $d[$col - 1]
    }
    $row++
}

$workbook.SaveAs("$PSScriptRoot\test_clientes.xlsx")
$excel.Quit()
```

---

## 5️⃣ TESTING MANUAL

### Paso 1: Ir a la UI

```
URL: https://rapicredit.onrender.com/pagos/clientes
```

### Paso 2: Click en "Nuevo Cliente" (dropdown)

```
Menu aparece:
├─ Crear cliente manual
└─ Cargar desde Excel  ← Click aquí
```

### Paso 3: Upload archivo

```
- Arrastra archivo Excel o hace click
- Selecciona test_clientes.xlsx
- Sistema procesa
```

### Paso 4: Verificar resultado

```
Esperado:
✓ Clientes creados: 3
⚠️ Con errores: 2

Botón: "Ver clientes con error"
```

### Paso 5: Revisar errores

```
Tab "Con errores" muestra:
- Fila 4: INVALIDA | Error Cedula | Error: Cédula debe ser V|E|J|Z + 6-11 dígitos
- Fila 5: V19567663 | Cedula Duplicada | Error: Cédula duplicada (existe en BD...)
```

---

## 6️⃣ TESTING API DIRECTO (curl)

### Test 1: Upload exitoso

```bash
TOKEN="tu_token_aqui"
API="https://pagos-backend-ov5f.onrender.com/api/v1"

curl -X POST "$API/clientes/upload-excel" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_clientes.xlsx"

# Respuesta esperada:
# {
#   "registros_creados": 3,
#   "registros_con_error": 2,
#   "mensaje": "Se crearon 3 cliente(s) y 2 con error(es)"
# }
```

### Test 2: Listar clientes con errores

```bash
curl -X GET "$API/clientes/revisar/lista?page=1&per_page=20" \
  -H "Authorization: Bearer $TOKEN"

# Respuesta:
# {
#   "total": 2,
#   "page": 1,
#   "per_page": 20,
#   "items": [
#     {
#       "id": 1,
#       "cedula": "INVALIDA",
#       "nombres": "Error Cedula",
#       "email": "error@test.com",
#       "errores": "Cédula debe ser V|E|J|Z + 6-11 dígitos",
#       "fila_origen": 4,
#       "estado": "PENDIENTE"
#     },
#     ...
#   ]
# }
```

### Test 3: Resolver error (eliminar de tabla)

```bash
ERROR_ID=1  # Del resultado anterior

curl -X DELETE "$API/clientes/revisar/$ERROR_ID" \
  -H "Authorization: Bearer $TOKEN"

# Status: 204 No Content
```

---

## 7️⃣ CASOS DE TEST AUTOMATIZADO

### Archivo: `test_carga_masiva_clientes.ps1`

```powershell
# ============================================================================
# E2E Test: Carga Masiva de Clientes desde Excel
# ============================================================================

$API = "https://pagos-backend-ov5f.onrender.com/api/v1"
$TOKEN = "tu_token_aqui"

# Helper: REST API call
function Invoke-ApiCall {
    param(
        [string]$Method,
        [string]$Endpoint,
        [hashtable]$Headers = @{},
        [object]$Body = $null,
        [string]$FilePath = $null
    )
    
    $Headers["Authorization"] = "Bearer $TOKEN"
    
    if ($FilePath) {
        # Multipart form data para archivo
        $response = Invoke-RestMethod `
            -Uri "$API$Endpoint" `
            -Method $Method `
            -Headers $Headers `
            -Form @{file = Get-Item $FilePath }
    } else {
        $params = @{
            Uri = "$API$Endpoint"
            Method = $Method
            Headers = $Headers
        }
        if ($Body) {
            $params["ContentType"] = "application/json"
            $params["Body"] = $Body | ConvertTo-Json -Depth 10
        }
        $response = Invoke-RestMethod @params
    }
    
    return $response
}

# SETUP: Crear archivo de test
Write-Host "=== SETUP: Creando archivo Excel de test ===" -ForegroundColor Cyan

$excelPath = "$PSScriptRoot\test_clientes_auto.xlsx"

# Crear Excel (requiere COM - en Windows es nativo)
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$workbook = $excel.Workbooks.Add()
$sheet = $workbook.ActiveSheet

# Headers
$sheet.Cells.Item(1, 1) = "Cédula"
$sheet.Cells.Item(1, 2) = "Nombres"
$sheet.Cells.Item(1, 3) = "Dirección"
$sheet.Cells.Item(1, 4) = "Fecha Nacimiento"
$sheet.Cells.Item(1, 5) = "Ocupación"
$sheet.Cells.Item(1, 6) = "Correo"
$sheet.Cells.Item(1, 7) = "Teléfono"

# Datos válidos
$testData = @(
    @("V99000001", "Cliente Test 1", "Calle 1", "1990-01-01", "Vendedor", "cliente1@test.com", "+58-414-001"),
    @("E99000002", "Cliente Test 2", "Calle 2", "1991-02-02", "Ejecutivo", "cliente2@test.com", "+58-414-002"),
    @("J99000003", "Cliente Test 3", "Calle 3", "1992-03-03", "Abogado", "cliente3@test.com", "+58-414-003"),
    @("INVALIDA", "Cedula Mala", "Calle 4", "1993-04-04", "Contador", "invalido@test.com", "+58-414-004"),
    @("V99000001", "Duplicado Cedula", "Calle 5", "1994-05-05", "Otros", "dup@test.com", "+58-414-005")
)

$row = 2
foreach ($d in $testData) {
    for ($col = 1; $col -le 7; $col++) {
        $sheet.Cells.Item($row, $col) = $d[$col - 1]
    }
    $row++
}

$workbook.SaveAs($excelPath)
$excel.Quit()

Write-Host "✓ Archivo creado: $excelPath" -ForegroundColor Green

# TEST 1: Upload Excel
Write-Host "`n=== TEST 1: Upload Excel ===" -ForegroundColor Cyan

try {
    $uploadResult = Invoke-ApiCall -Method POST -Endpoint "/clientes/upload-excel" `
        -FilePath $excelPath
    
    Write-Host "Respuesta:" -ForegroundColor Yellow
    $uploadResult | ConvertTo-Json | Write-Host
    
    $created = $uploadResult.registros_creados
    $errors = $uploadResult.registros_con_error
    
    Write-Host "`n✓ Clientes creados: $created" -ForegroundColor Green
    Write-Host "⚠️  Con errores: $errors" -ForegroundColor Yellow
    
    if ($created -ne 3 -or $errors -ne 2) {
        Write-Host "❌ FALLO: Esperado 3 creados y 2 con error" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ ERROR en upload: $_" -ForegroundColor Red
    exit 1
}

# TEST 2: Listar clientes con errores
Write-Host "`n=== TEST 2: Listar clientes con errores ===" -ForegroundColor Cyan

try {
    $errorList = Invoke-ApiCall -Method GET `
        -Endpoint "/clientes/revisar/lista?page=1&per_page=20"
    
    $totalErrors = $errorList.total
    $items = $errorList.items
    
    Write-Host "✓ Total con errores en BD: $totalErrors" -ForegroundColor Green
    Write-Host "Items:" -ForegroundColor Yellow
    $items | ForEach-Object {
        Write-Host "  - Fila $($_.fila_origen): $($_.cedula) | $($_.nombres) | Error: $($_.errores)" -ForegroundColor Yellow
    }
    
    if ($totalErrors -lt 2) {
        Write-Host "❌ FALLO: Esperado al menos 2 con errores" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ ERROR listando: $_" -ForegroundColor Red
    exit 1
}

# TEST 3: Verificar clientes creados en lista principal
Write-Host "`n=== TEST 3: Verificar clientes en lista principal ===" -ForegroundColor Cyan

try {
    $clientsList = Invoke-ApiCall -Method GET -Endpoint "/clientes?page=1&per_page=100"
    
    $createdClients = $clientsList.items | Where-Object { $_.cedula -like "V99000*" -or $_.cedula -like "E99000*" }
    $count = @($createdClients).Count
    
    Write-Host "✓ Clientes test encontrados: $count" -ForegroundColor Green
    
    if ($count -ne 3) {
        Write-Host "❌ FALLO: Esperado 3 clientes creados, encontrados $count" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ ERROR verificando: $_" -ForegroundColor Red
    exit 1
}

# CLEANUP
Write-Host "`n=== CLEANUP ===" -ForegroundColor Cyan
Remove-Item $excelPath -Force
Write-Host "✓ Archivo de test eliminado" -ForegroundColor Green

# Resumen
Write-Host "`n╔════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ TODOS LOS TESTS PASARON               ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Green

Write-Host "`nResumen:"
Write-Host "  ✓ Upload Excel: 3 creados, 2 con error"
Write-Host "  ✓ Errores registrados en clientes_con_errores"
Write-Host "  ✓ Clientes válidos en tabla clientes"
```

---

## 8️⃣ TROUBLESHOOTING

### Error: "Tabla clientes_con_errores no existe"

```sql
-- Ejecutar migración SQL 024
SELECT 1;  -- si funciona, base de datos está OK

-- Copiar y pegar contenido de backend/scripts/024_create_clientes_con_errores.sql
```

### Error: "openpyxl not found"

```bash
# En backend
pip install openpyxl

# En requirements.txt, asegurar:
openpyxl>=3.0.0
```

### Error: 422 - Validación fallida

```
Posibles causas:
- Email duplicado en BD
- Cédula duplicada en BD
- Formato Excel incorrecto
- Faltan columnas

Solución: Revisar tabla clientes_con_errores para detalles
```

---

## 9️⃣ VERIFICACIÓN FINAL

Checklist antes de producción:

- [ ] Migración SQL ejecutada
- [ ] Tabla `clientes_con_errores` creada
- [ ] Backend desplegado
- [ ] Frontend compilado y desplegado
- [ ] Endpoint `/clientes/upload-excel` accesible
- [ ] Endpoint `/clientes/revisar/lista` funciona
- [ ] Test Excel sube correctamente
- [ ] Duplicados detectados y registrados
- [ ] UI muestra resultados correctos
- [ ] Email de usuario registrado correctamente

---

**¡Listo para producción!** 🚀

