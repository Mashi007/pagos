# 🔗 CONEXIONES DEL PROCESO DE CARGA MASIVA Y CREACIÓN DE CLIENTES

## 📋 ARCHIVO PRINCIPAL: `ExcelUploader.tsx`

### 🔌 IMPORTS Y DEPENDENCIAS

#### **1. Componentes UI (React)**
- `@/components/ui/card` - Tarjetas para mostrar datos
- `@/components/ui/button` - Botones de acción
- `@/components/ui/badge` - Badges de estado
- `@/components/ui/searchable-select` - Dropdowns con búsqueda

#### **2. Componentes Relacionados**
- `./ConfirmacionDuplicadoModal` - Modal para confirmar duplicados
  - **Propósito**: Muestra información del cliente existente y nuevo
  - **Interfaz**:
    - `clienteExistente`: Cliente ya registrado
    - `clienteNuevo`: Cliente que se intenta crear
    - `prestamos`: Préstamos del cliente existente
    - `onConfirm(comentarios)`: Callback cuando el usuario confirma

#### **3. Servicios (API Calls)**
- `@/services/clienteService` ⭐ **PRINCIPAL**
  - `createCliente(data)` - Crear cliente normal
  - `createClienteWithConfirmation(data, comentarios)` - Crear con `confirm_duplicate: true`

- `@/services/concesionarioService`
  - Obtiene lista de concesionarios activos para dropdowns

- `@/services/analistaService`
  - Obtiene lista de analistas activos para dropdowns

- `@/services/modeloVehiculoService`
  - Obtiene lista de modelos de vehículos activos para dropdowns

#### **4. Librerías Externas**
- `xlsx` - Procesamiento de archivos Excel
- `@tanstack/react-query` - Cache y invalidación de queries
- `framer-motion` - Animaciones
- `react-router-dom` - Navegación

---

## 🔄 FLUJO DE DATOS

### **1. Carga de Excel**
```
ExcelUploader.tsx
  └─> XLSX.read() - Lee archivo Excel
  └─> Procesa filas
  └─> Valida campos (validateField)
  └─> Carga dropdowns:
      ├─> concesionarioService.getConcesionariosActivos()
      ├─> analistaService.getAnalistasActivos()
      └─> modeloVehiculoService.getModelosActivos()
```

### **2. Guardado Individual**
```
ExcelUploader.tsx (saveIndividualClient)
  └─> clienteService.createCliente(clienteData)
      └─> POST /api/v1/clientes/
          └─> backend/app/api/v1/endpoints/clientes.py
              └─> crear_cliente()
                  ├─> Verifica duplicado (409 Conflict)
                  │   └─> Retorna: cliente_existente + préstamos
                  └─> Si confirm_duplicate: True
                      └─> Crea cliente nuevo
```

### **3. Manejo de Duplicados**
```
ExcelUploader.tsx
  └─> 409 Conflict detectado
  └─> setClienteDuplicado() - Guarda info del duplicado
  └─> setShowConfirmacionModal(true)
  └─> ConfirmacionDuplicadoModal
      └─> Usuario confirma o cancela
      └─> handleConfirmarDuplicado()
          └─> clienteService.createClienteWithConfirmation()
              └─> POST /api/v1/clientes/ con confirm_duplicate: true
```

### **4. Guardado Masivo**
```
ExcelUploader.tsx (saveAllValidClients)
  └─> Itera sobre filas válidas
  └─> Para cada fila:
      ├─> saveIndividualClient(row)
      │   ├─> Si hay duplicado → Promise pendiente
      │   │   └─> Espera confirmación del usuario
      │   └─> Si éxito → continúa siguiente fila
      └─> Actualiza contadores (successful, failed)
```

---

## 🗄️ BACKEND: ENDPOINTS Y SCHEMAS

### **Endpoint Principal**
```
POST /api/v1/clientes/
Archivo: backend/app/api/v1/endpoints/clientes.py
Función: crear_cliente()
```

### **Schema de Validación**
```
Archivo: backend/app/schemas/cliente.py
Schema: ClienteCreate
Campos:
  - cedula: str (8-20 caracteres)
  - nombres: str (2-100 caracteres, 2-4 palabras)
  - telefono: str (13 caracteres)
  - email: EmailStr
  - direccion: str (5-500 caracteres)
  - fecha_nacimiento: date (>=18 años)
  - ocupacion: str (2-100 caracteres)
  - modelo_vehiculo: Optional[str]
  - concesionario: Optional[str]
  - analista: Optional[str]
  - estado: str (ACTIVO|INACTIVO|FINALIZADO)
  - activo: Optional[bool]
  - notas: Optional[str]
  - confirm_duplicate: bool (False por defecto)
```

### **Respuesta de Error 409 (Duplicado)**
```json
{
  "detail": {
    "error": "CLIENTE_DUPLICADO",
    "message": "Ya existe un cliente con la cédula {cedula}",
    "cedula": "V1803113362",
    "cliente_existente": {
      "id": 821,
      "cedula": "V1803113362",
      "nombres": "Cliente Uno Apellido Uno",
      "telefono": "+581111111111",
      "email": "aaroncrespo@gmail.com",
      "fecha_registro": "2025-10-29T..."
    },
    "prestamos": [
      {
        "id": 123,
        "monto_financiamiento": 10000.0,
        "estado": "AL DÍA",
        "modalidad_pago": "MENSUAL",
        "cuotas_pagadas": 5,
        "cuotas_pendientes": 31
      }
    ]
  }
}
```

---

## 🧩 COMPONENTES RELACIONADOS

### **1. CrearClienteForm.tsx**
**Ubicación**: `frontend/src/components/clientes/CrearClienteForm.tsx`

**Conexión con ExcelUploader**:
```typescript
// Puede abrir ExcelUploader desde el formulario
const [showExcelUploader, setShowExcelUploader] = useState(false)

// Botón en el formulario:
<Button onClick={() => setShowExcelUploader(true)}>
  Cargar Excel
</Button>

// Renderiza ExcelUploader si está activo:
{showExcelUploader && (
  <ExcelUploader
    onClose={() => setShowExcelUploader(false)}
    onSuccess={() => setShowExcelUploader(false)}
  />
)}
```

**Uso Compartido**:
- Ambos usan `clienteService` para crear clientes
- Ambos manejan duplicados con `ConfirmacionDuplicadoModal`
- Ambos validan campos similares (nombres, cédula, fecha nacimiento)

**Diferencias**:
- `CrearClienteForm`: Formulario manual, un cliente a la vez
- `ExcelUploader`: Carga masiva desde Excel, múltiples clientes

### **2. ConfirmacionDuplicadoModal.tsx**
**Ubicación**: `frontend/src/components/clientes/ConfirmacionDuplicadoModal.tsx`

**Props**:
```typescript
interface ConfirmacionDuplicadoModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (comentarios: string) => void
  clienteExistente: ClienteExistente
  clienteNuevo: { nombres, cedula, telefono, email }
  prestamos?: Prestamo[]
}
```

**Usado por**:
- ✅ `ExcelUploader.tsx` - Para confirmar duplicados en carga masiva
- ✅ `CrearClienteForm.tsx` - Para confirmar duplicados en formulario manual

---

## 🔄 ESTADO Y CACHE (React Query)

### **Queries Invalidadas**
```typescript
// Cuando se crea un cliente exitosamente:
queryClient.invalidateQueries({ queryKey: ['clientes'] })
queryClient.invalidateQueries({ queryKey: ['clientes-list'] })
queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })
```

**Efecto**: Refresca automáticamente:
- Lista de clientes en Dashboard
- Estadísticas de clientes
- Filtros y búsquedas

---

## 🔐 VALIDACIONES Y REGLAS

### **Frontend (ExcelUploader.tsx)**

#### **Validación de Cédula**:
```typescript
const cedulaPattern = /^[VEJ]\d{7,10}$/
// V/E/J seguido de 7-10 dígitos
```

#### **Validación de Nombres**:
```typescript
// CARGA MASIVA: Entre 2 y 4 palabras
if (nombresWords.length < 2 || nombresWords.length > 4) {
  return { isValid: false, message: 'DEBE tener entre 2 y 4 palabras' }
}
```

#### **Validación de Fecha de Nacimiento**:
```typescript
// Formato: DD/MM/YYYY
// No puede ser futura o de hoy
// Debe tener al menos 18 años cumplidos
const fecha18 = new Date(anoNum + 18, mesNum - 1, diaNum)
if (fecha18 > hoy) {
  return { isValid: false, message: 'Debe tener al menos 18 años cumplidos' }
}
```

#### **Validación de Dirección**:
```typescript
// Mínimo 5 caracteres
if (value.trim().length < 5) {
  return { isValid: false, message: 'Dirección debe tener al menos 5 caracteres' }
}
```

#### **Validación de Ocupación**:
```typescript
// Mínimo 2 caracteres
if (value.trim().length < 2) {
  return { isValid: false, message: 'Ocupación debe tener al menos 2 caracteres' }
}
```

### **Backend (cliente.py)**

**Validaciones en Schema**:
- `cedula`: MIN 8, MAX 20 caracteres
- `nombres`: MIN 2, MAX 100 caracteres
- `telefono`: Exactamente 13 caracteres
- `email`: Validación de EmailStr
- `direccion`: MIN 5, MAX 500 caracteres
- `fecha_nacimiento`: Tipo date (validado por Pydantic)
- `ocupacion`: MIN 2, MAX 100 caracteres

---

## 📊 FLUJO COMPLETO: CARGA MASIVA CON DUPLICADOS

```
1. Usuario carga Excel
   └─> ExcelUploader procesa archivo
   └─> Valida cada fila
   └─> Muestra tabla editable

2. Usuario hace clic en "Guardar Todos"
   └─> saveAllValidClients()
   └─> Itera sobre filas válidas

3. Para cada fila:
   ├─> saveIndividualClient(row)
   │   └─> POST /api/v1/clientes/
   │       ├─> Si éxito → continúa
   │       └─> Si 409 Conflict:
   │           ├─> setClienteDuplicado()
   │           ├─> setShowConfirmacionModal(true)
   │           ├─> Retorna Promise pendiente
   │           └─> Bucle pausa esperando usuario
   │
   ├─> Usuario ve modal de duplicado
   │   └─> ConfirmacionDuplicadoModal
   │       ├─> Muestra cliente existente
   │       ├─> Muestra cliente nuevo
   │       └─> Muestra préstamos del existente
   │
   ├─> Usuario confirma o cancela
   │   ├─> Si confirma:
   │   │   └─> handleConfirmarDuplicado()
   │   │       └─> clienteService.createClienteWithConfirmation()
   │   │           └─> POST con confirm_duplicate: true
   │   │               └─> Backend crea cliente
   │   │                   └─> Promise se resuelve
   │   │                       └─> Bucle continúa
   │   │
   │   └─> Si cancela:
   │       └─> Promise se resuelve con false
   │           └─> Fila marcada como fallida
   │               └─> Bucle continúa

4. Después de todas las filas:
   └─> Muestra resumen (exitosos/fallidos)
   └─> Elimina filas guardadas
   └─> Actualiza cache de React Query
   └─> Refresca Dashboard
```

---

## ⚠️ PUNTOS CRÍTICOS DE INTEGRACIÓN

### **1. Manejo de Promesas en Guardado Masivo**
- **Archivo**: `ExcelUploader.tsx`
- **Líneas**: 591-607
- **Problema resuelto**: El bucle espera confirmación del usuario para cada duplicado
- **Solución**: `duplicadoResolver` state + Promise pendiente

### **2. Limpieza de Estado**
- **Archivo**: `ExcelUploader.tsx`
- **Funciones helper**: `clearSavingProgressAndResolve()`, `clearSavingProgressAndReject()`
- **Problema resuelto**: `savingProgress` se limpia correctamente en todos los casos

### **3. Búsqueda de Fila por _rowIndex**
- **Archivo**: `ExcelUploader.tsx`
- **Líneas**: 303-304
- **Problema resuelto**: Usa `excelData.find(r => r._rowIndex === targetRowIndex)` en lugar de índice del array
- **Razón**: Las filas pueden eliminarse del array, pero `_rowIndex` es persistente

### **4. Sincronización de Validaciones**
- **Frontend**: Valida en tiempo real con `validateField()`
- **Backend**: Re-valida con Pydantic schemas
- **Consistencia**: Mismas reglas en ambos lados

---

## 📝 NOTAS IMPORTANTES

1. **Campos Opcionales en Backend**:
   - `modelo_vehiculo`, `concesionario`, `analista` son `Optional[str]`
   - Si vienen vacíos, backend asigna "Por Definir"
   - Frontend envía `''` (string vacío) en lugar de `undefined`

2. **Formato de Fechas**:
   - **Frontend muestra**: DD/MM/YYYY
   - **Frontend envía**: YYYY-MM-DD
   - **Conversión**: `convertirFechaParaBackend()`

3. **Formato de Nombres**:
   - **Frontend**: Unifica nombres + apellidos (2-4 palabras)
   - **Formato**: Title Case con `formatNombres()`

4. **Validación de Edad**:
   - Implementada en frontend (18+ años)
   - Debe validarse también en backend si no existe

5. **Cache de React Query**:
   - Se invalida automáticamente al crear clientes
   - Refresca Dashboard sin necesidad de recargar página

---

## 🔍 ARCHIVOS RELACIONADOS

### **Frontend**:
1. `frontend/src/components/clientes/ExcelUploader.tsx` ⭐ **PRINCIPAL**
2. `frontend/src/components/clientes/CrearClienteForm.tsx` - Formulario manual
3. `frontend/src/components/clientes/ConfirmacionDuplicadoModal.tsx` - Modal duplicados
4. `frontend/src/services/clienteService.ts` - Servicio API
5. `frontend/src/services/concesionarioService.ts` - Dropdown concesionarios
6. `frontend/src/services/analistaService.ts` - Dropdown analistas
7. `frontend/src/services/modeloVehiculoService.ts` - Dropdown modelos
8. `frontend/src/types/index.ts` - Tipo `ClienteForm`

### **Backend**:
1. `backend/app/api/v1/endpoints/clientes.py` - Endpoint POST `/api/v1/clientes/`
2. `backend/app/schemas/cliente.py` - Schema `ClienteCreate`
3. `backend/app/models/cliente.py` - Modelo SQLAlchemy `Cliente`
4. `backend/app/models/prestamo.py` - Para obtener préstamos del cliente existente

---

## ✅ CHECKLIST DE INTEGRACIÓN

- [x] ExcelUploader se conecta correctamente con clienteService
- [x] Modal de duplicados funciona en carga masiva
- [x] Validaciones frontend coinciden con backend
- [x] Cache de React Query se invalida correctamente
- [x] Dropdowns se cargan desde servicios independientes
- [x] Manejo de Promesas para guardado masivo con duplicados
- [x] Limpieza de estado en todos los casos (éxito, error, cancelación)
- [x] Búsqueda de filas por _rowIndex (no por índice del array)

---

**Última revisión**: 2025-10-29
**Estado**: ✅ Todas las conexiones verificadas y funcionando correctamente

