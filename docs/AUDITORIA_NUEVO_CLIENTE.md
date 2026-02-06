# Auditoría integral: Nuevo Cliente

**Alcance:** Formulario "Nuevo Cliente" (creación manual de cliente) y su integración con backend, validadores y reglas de duplicados. Incluye el botón "Cargar Excel" como alternativa de entrada.

---

## 1. Resumen ejecutivo

| Aspecto | Estado | Notas |
|--------|--------|--------|
| **Endpoint** | ✅ | `POST /api/v1/clientes` con `ClienteCreate`; usa `Depends(get_db)`. |
| **Conexión BD** | ✅ | Inserción real en `public.clientes`; sin stubs. |
| **Duplicados** | ✅ | Backend rechaza misma cédula, nombre, email o teléfono (409). |
| **Validación frontend** | ✅ | Campos obligatorios, formato (cédula, nombres 2-7 palabras, teléfono +58, email, fecha no futura, dirección, ocupación). |
| **Validación backend** | ✅ | Pydantic + reglas de duplicados antes de `db.add`. |
| **Manejo 409** | ✅ | Mensaje por tipo (cédula/nombre/email/teléfono) y opción "Abrir cliente existente". |
| **usuario_registro** | ⚠️ | Campo obligatorio en backend; el formulario no lo enviaba (corregido: se envía email del usuario o "formulario"). |

---

## 2. Flujo y componentes

### 2.1 Origen del formulario

- **Ruta:** Desde listado de clientes (`/pagos/clientes`) → botón "Nuevo Cliente" abre modal con `CrearClienteForm`.
- **Componente:** `frontend/src/components/clientes/CrearClienteForm.tsx`.
- **Props:** `onClose`, `onSuccess`, `onClienteCreated`, `onOpenEditExisting` (opcional, para abrir cliente existente ante 409).

### 2.2 Botón "Cargar Excel"

- Muestra el modal `ExcelUploader`; el formulario Nuevo Cliente permanece abierto en segundo plano.
- La carga masiva usa el mismo endpoint `POST /api/v1/clientes` por cada fila (ver `AUDITORIA_CARGA_MASIVA_CLIENTES.md`).
- Mismas reglas de duplicados y validación en backend.

### 2.3 Envío al backend

- **Creación:** `clienteService.createCliente(todosLosDatos)` → `POST /api/v1/clientes` con body: `cedula`, `nombres`, `telefono`, `email`, `direccion` (JSON), `fecha_nacimiento` (YYYY-MM-DD), `ocupacion`, `estado`, `notas`, `usuario_registro`.
- **Edición:** `clienteService.updateCliente(id, clienteData)` → `PUT /api/v1/clientes/{id}` solo con campos modificados.

---

## 3. Endpoint y backend

### 3.1 POST /api/v1/clientes

- **Archivo:** `backend/app/api/v1/endpoints/clientes.py` → `create_cliente`.
- **Auth:** Router con `dependencies=[Depends(get_current_user)]`.
- **Schema:** `ClienteCreate` (hereda de `ClienteBase`): todos los campos obligatorios, incluido `usuario_registro: str`.
- **Validaciones de duplicados (en este orden):**
  1. Misma **cédula** → 409.
  2. Mismo **nombre completo** (`nombres`) → 409.
  3. Mismo **email** (si no vacío) → 409.
  4. Mismo **teléfono** (solo dígitos, mínimo 8) → 409.
- **Persistencia:** `db.add(row)`, `db.commit()`, `db.refresh(row)`; respuesta `ClienteResponse`.

### 3.2 Schema y tabla

- **Schema:** `backend/app/schemas/cliente.py` — `ClienteBase` / `ClienteCreate` alineados con tabla `clientes`.
- **Modelo:** `backend/app/models/cliente.py` — columnas: id, cedula, nombres, telefono, email, direccion, fecha_nacimiento, ocupacion, estado, fecha_registro, fecha_actualizacion, usuario_registro, notas.

---

## 4. Validación en frontend (CrearClienteForm)

### 4.1 Campos obligatorios

- **Datos personales:** Cédula, Nombres y apellidos, Teléfono, Email.
- **Dirección:** Calle principal, Parroquia, Municipio, Ciudad, Estado (dirección).
- **Otros:** Fecha de nacimiento (DD/MM/YYYY), Ocupación.
- **Estado:** ACTIVO | INACTIVO | FINALIZADO (por defecto ACTIVO).
- **Notas:** Por defecto "No hay observacion".

### 4.2 Reglas de formato (validación local)

| Campo | Regla | Mensaje típico |
|-------|--------|----------------|
| **Cédula** | Formato V/E/J + dígitos; autoformato con `formatCedula` | Validación vía validadoresService o fallback local |
| **Nombres** | 2-7 palabras; Title Case | "Nombres y apellidos requeridos" / "DEBE tener entre 2 y 7 palabras" |
| **Teléfono** | +58 + 10 dígitos (sin 0 inicial) | "Teléfono requerido" / "Formato: +58 + 10 dígitos" |
| **Email** | Sin espacios/comas, @, extensión válida; minúsculas | "Email requerido" / "El email debe tener una extensión válida..." |
| **Fecha nacimiento** | DD/MM/YYYY; no futura ni hoy; ≥ 18 años | "La fecha de nacimiento no puede ser futura o de hoy" |
| **Dirección** | Calle principal, parroquia, municipio, ciudad, estado obligatorios | "Calle Principal requerida", etc. |
| **Descripción** | Si se completa, mínimo 5 palabras | Validación en submit |
| **Ocupación** | Máximo 2 palabras; Title Case | Validación local |

### 4.3 Uso del servicio de validadores

- Para **cedula**, **nombres**, **telefono**, **email**, **fechaNacimiento** se usa `validadoresService.validarCampo(tipoValidador, value, 'VENEZUELA')` cuando el campo tiene mapeo a un validador backend (`cedula_venezuela`, `nombre`, `telefono_venezuela`, `email`, `fecha`).
- **Endpoint:** `POST /api/v1/validadores/validar` (o equivalente según `validadoresService`).
- Si el servicio falla, se aplica validación local básica (obligatorio / válido).

### 4.4 Unicidad (cédula, nombre, email, teléfono)

- **No hay comprobación previa en frontend** antes de enviar: la unicidad se garantiza solo en backend.
- Al recibir **409**, el frontend muestra el mensaje del backend y ofrece "Abrir cliente existente" (si viene `Cliente existente ID` en el `detail`).

---

## 5. Preparación del payload y corrección usuario_registro

### 5.1 Objeto enviado en creación

- **todosLosDatos** incluye: `cedula`, `nombres`, `telefono`, `email`, `direccion` (JSON), `fecha_nacimiento`, `ocupacion`, `estado`, `notas`.
- **usuario_registro:** El backend lo exige en `ClienteCreate`. El formulario debe enviarlo; en la corrección se usa el email del usuario autenticado (`useSimpleAuth`) o el literal `"formulario"` si no hay usuario.

### 5.2 Formateo antes de enviar

- Cédula: `formatCedula`, mayúscula inicial.
- Nombres/ocupación: Title Case, normalización "nn" → vacío.
- Teléfono: `+58` + 10 dígitos.
- Email: minúsculas, sin espacios.
- Dirección: JSON con callePrincipal, calleTransversal, descripcion, parroquia, municipio, ciudad, estado (Title Case).
- Fecha: DD/MM/YYYY → YYYY-MM-DD.

---

## 6. Manejo de errores (409 / 400 / 422)

- **409:** Se identifica el tipo por el texto del `detail`: "misma cédula", "mismo nombre completo", "mismo email", "mismo teléfono". Se muestra confirm con mensaje amigable y, si hay ID en el mensaje, se ofrece abrir ese cliente con `onOpenEditExisting(existingId)`.
- **400 / 422:** Se muestra el mensaje del backend (p. ej. validación Pydantic o faltante de `usuario_registro` si no se enviaba).

---

## 7. Checklist de auditoría

| Ítem | Cumple |
|------|--------|
| Endpoint POST /clientes existe y usa get_db | ✅ |
| Duplicados: cédula, nombre, email, teléfono → 409 | ✅ |
| Validación frontend de campos obligatorios y formato | ✅ |
| Integración con validadores (backend) para cédula, nombre, teléfono, email, fecha | ✅ |
| Fecha nacimiento: no futura, ≥ 18 años | ✅ |
| Dirección estructurada (JSON) y campos requeridos | ✅ |
| Envío de usuario_registro en creación | ✅ (tras corrección) |
| Manejo 409 con mensaje y "Abrir cliente existente" | ✅ |
| Cargar Excel usa mismo endpoint y mismas reglas | ✅ |
| Documentación (REGLAS_NEGOCIO_CLIENTES) alineada | ✅ |

---

## 8. Referencia de archivos

| Rol | Ruta |
|-----|------|
| Formulario Nuevo Cliente | `frontend/src/components/clientes/CrearClienteForm.tsx` |
| Listado y apertura del modal | `frontend/src/components/clientes/ClientesList.tsx` |
| Servicio clientes | `frontend/src/services/clienteService.ts` |
| Servicio validadores | `frontend/src/services/validadoresService.ts` |
| Endpoint crear cliente | `backend/app/api/v1/endpoints/clientes.py` |
| Schema cliente | `backend/app/schemas/cliente.py` |
| Modelo BD | `backend/app/models/cliente.py` |
| Reglas de negocio | `docs/REGLAS_NEGOCIO_CLIENTES.md` |
| Auditoría Carga masiva | `docs/AUDITORIA_CARGA_MASIVA_CLIENTES.md` |
