# Validadores del Formulario de Nuevo Cliente

## Resumen de Validaciones Aplicadas

### 1. **Cédula** (`cedula`)
- **Validador Backend**: `cedula_venezuela` (validación mediante API)
- **Formato Automático**:
  - Primera letra (E, J, V) se convierte automáticamente a mayúscula
  - Ejemplo: `e12345678` → `E12345678`
- **Validación**: Realizada por backend a través del servicio de validadores

---

### 2. **Nombres y Apellidos** (`nombres`)
- **Validador Frontend**: `validateNombres()`
- **Reglas**:
  - ✅ Mínimo **2 palabras** (nombre + apellido)
  - ✅ Máximo **7 palabras** (nombres + apellidos combinados)
  - ✅ Cada palabra debe tener mínimo 2 caracteres
  - ✅ Campo obligatorio
- **Formato Automático**: 
  - **Title Case** en tiempo real (primera letra mayúscula de cada palabra)
  - Ejemplo: `juan carlos pérez gonzález` → `Juan Carlos Pérez González`
- **Mensajes de Error**:
  - "Mínimo 2 palabras requeridas (nombre + apellido)"
  - "Máximo 7 palabras permitidas (tienes X)"
  - "Cada palabra debe tener mínimo 2 caracteres"

---

### 3. **Teléfono** (`telefono`)
- **Validador Frontend**: `validateTelefono()`
- **Reglas**:
  - ✅ Exactamente **10 dígitos** (0-9)
  - ✅ **NO puede empezar por 0**
  - ✅ Solo números (sin letras ni caracteres especiales)
  - ✅ Campo obligatorio
- **Formato**:
  - Prefijo fijo: **+58** (mostrado visualmente, no editable)
  - Input: Solo 10 dígitos (ejemplo: `1234567890`)
  - Guardado en BD: `+581234567890`
- **Mensajes de Error**:
  - "El teléfono debe tener exactamente 10 dígitos"
  - "El teléfono no puede empezar por 0"
  - "El teléfono solo puede contener números (0-9)"

---

### 4. **Email** (`email`)
- **Validador Backend**: `email` (validación mediante API)
- **Formato Automático**: 
  - Convertido a **minúsculas** al guardar
- **Validación**: Realizada por backend a través del servicio de validadores

---

### 5. **Fecha de Nacimiento** (`fechaNacimiento`)
- **Validador Frontend**: `validateFechaNacimiento()`
- **Reglas**:
  - ✅ Formato: **DD/MM/YYYY** (ejemplo: `15/03/1990`)
  - ✅ Fecha debe ser válida (no acepta fechas imposibles como 31/02)
  - ✅ Fecha debe ser **pasada** (no puede ser futura ni de hoy)
  - ✅ **Edad mínima**: 21 años cumplidos
  - ✅ **Edad máxima**: 60 años cumplidos
  - ✅ Campo obligatorio
  - ✅ Rango de año: 1900-2100
- **Conversión**: Al guardar se convierte de `DD/MM/YYYY` a `YYYY-MM-DD` (ISO)
- **Mensajes de Error**:
  - "Formato inválido. Use: DD/MM/YYYY"
  - "Día inválido (1-31)"
  - "Mes inválido (1-12)"
  - "Año inválido (1900-2100)"
  - "Fecha inválida (ej: 31/02 no existe)"
  - "La fecha de nacimiento no puede ser futura o de hoy"
  - "Debe tener al menos 21 años cumplidos"
  - "No puede tener más de 60 años cumplidos"

---

### 6. **Dirección Estructurada**

#### 6.1. **Calle Principal** (`callePrincipal`)
- **Validador**: Parte de `validateDireccion()`
- **Reglas**: ✅ Campo obligatorio
- **Formato Automático**: Title Case al guardar

#### 6.2. **Calle Transversal** (`calleTransversal`)
- **Validador**: No validado (opcional)
- **Formato Automático**: Title Case al guardar

#### 6.3. **Descripción** (`descripcion`)
- **Validador**: No validado (opcional)
- **Nota**: Lugar cercano, color de casa (sin formateo automático)

#### 6.4. **Parroquia** (`parroquia`)
- **Validador**: Parte de `validateDireccion()`
- **Reglas**: ✅ Campo obligatorio
- **Formato Automático**: Title Case al guardar

#### 6.5. **Municipio** (`municipio`)
- **Validador**: Parte de `validateDireccion()`
- **Reglas**: ✅ Campo obligatorio
- **Formato Automático**: Title Case al guardar

#### 6.6. **Ciudad** (`ciudad`)
- **Validador**: Parte de `validateDireccion()`
- **Reglas**: ✅ Campo obligatorio
- **Formato Automático**: Title Case al guardar

#### 6.7. **Estado** (`estadoDireccion`)
- **Validador**: Parte de `validateDireccion()`
- **Reglas**: ✅ Campo obligatorio
- **Formato Automático**: Title Case al guardar

**Almacenamiento**: Los campos de dirección se guardan como **JSON estructurado**:
```json
{
  "callePrincipal": "Av. Bolívar",
  "calleTransversal": "Calle 5 de Julio",
  "descripcion": "Cerca del mercado",
  "parroquia": "San Juan",
  "municipio": "Libertador",
  "ciudad": "Caracas",
  "estado": "Distrito Capital"
}
```

---

### 7. **Ocupación** (`ocupacion`)
- **Validador Frontend**: `validateOcupacion()`
- **Reglas**:
  - ✅ Máximo **2 palabras**
  - ✅ Mínimo 2 caracteres por palabra
  - ✅ Campo obligatorio
- **Formato Automático**: 
  - **Title Case** en tiempo real
  - Ejemplo: `gerente general` → `Gerente General`
- **Mensajes de Error**:
  - "Máximo 2 palabras permitidas en ocupación"
  - "Mínimo 2 caracteres"

---

### 8. **Estado** (`estado`)
- **Validador**: Select con opciones predefinidas
- **Valores permitidos**: `ACTIVO`, `INACTIVO`, `FINALIZADO`
- **Valor por defecto**: `ACTIVO`
- **Campo**: Obligatorio

---

### 9. **Notas** (`notas`)
- **Validador**: No validado (opcional)
- **Valor por defecto**: `'NA'`
- **Límite**: Máximo 1000 caracteres (validación backend)

---

## Validaciones Adicionales

### Regla "NN" (Omitir Campo)
- **Descripción**: Si el usuario ingresa `'nn'` (en cualquier caso o con espacios), el campo se considera válido y se guarda como vacío (`''`)
- **Aplicable a**: Campos que **NO tienen validadores más específicos**. La regla "NN" se aplica automáticamente donde no existe una validación más estricta.
- **Campos donde NO aplica** (tienen validadores específicos):
  - `cedula` (tiene validador de formato V/E/J/Z + dígitos)
  - `nombres` (tiene validador de 2-7 palabras)
  - `telefono` (tiene validador de 10 dígitos, sin empezar por 0)
  - `email` (tiene validador de formato con @ y extensión)
  - `fechaNacimiento` (tiene validador de edad 21-60 años)
  - `ocupacion` (tiene validador de máximo 2 palabras)
  - `descripcion` (tiene validador de mínimo 5 palabras si se completa)
- **Función**: `isNN()` y `blankIfNN()`

### Validación de Duplicados (Backend)
- **Regla**: No se puede crear o actualizar un cliente si **YA EXISTE** otro cliente con:
  - La misma **cédula** **O**
  - El mismo **nombre completo** (case-insensitive, sin espacios extras)
- **Validación**: 
  - Se valida en el backend al crear (`crear_cliente`) y actualizar (`actualizar_cliente`)
  - Comparación case-insensitive para nombres
  - No permite guardar si coincide con igual cédula **Y/O** nombres
- **Mensaje**: "No puedes crear un cliente con el mismo nombre o número de cédula"
- **Acción**: Si se detecta duplicado, se ofrece abrir el cliente existente para editar

### Auto-formato
**Title Case automático** aplicado en tiempo real mientras el usuario escribe y al guardar:

**Campos con Title Case** (primera letra mayúscula de cada palabra):
- ✅ `nombres` - Autoformato en tiempo real
- ✅ `ocupacion` - Autoformato en tiempo real
- ✅ `callePrincipal` - Autoformato al guardar
- ✅ `calleTransversal` - Autoformato al guardar
- ✅ `parroquia` - Autoformato al guardar
- ✅ `municipio` - Autoformato al guardar
- ✅ `ciudad` - Autoformato al guardar
- ✅ `estadoDireccion` - Autoformato al guardar

**Campos con otro formato**:
- ❌ `descripcion` - **NO se formatea** (se guarda tal cual, sin Title Case)
- ⚠️ `cedula` - Solo primera letra mayúscula (E, J, V, Z)
- ⚠️ `email` - Se guarda en **minúsculas** (autoformato a minúsculas en tiempo real)

---

## Orden de Validación

1. **Validación en tiempo real** (mientras el usuario escribe):
   - Auto-formato (Title Case, mayúsculas)
   - Validación frontend personalizada

2. **Validación al enviar** (`handleSubmit`):
   - Verificación de campos obligatorios
   - Validación completa con `isFormValid()`
   - Validación backend adicional

3. **Validación backend** (al crear/actualizar):
   - Validación de duplicados (cédula/nombre)
   - Validación de esquema Pydantic
   - Validación de formato de datos

---

## Campos Obligatorios (Modo Creación)

Los siguientes campos son **obligatorios** en modo creación:
- ✅ Cédula
- ✅ Nombres y Apellidos
- ✅ Teléfono
- ✅ Email
- ✅ Calle Principal
- ✅ Parroquia
- ✅ Municipio
- ✅ Ciudad
- ✅ Estado (dirección)
- ✅ Fecha de Nacimiento
- ✅ Ocupación
- ✅ Estado (ACTIVO/INACTIVO/FINALIZADO)

**Nota**: En modo **edición**, las validaciones son más flexibles para permitir actualizaciones parciales.

