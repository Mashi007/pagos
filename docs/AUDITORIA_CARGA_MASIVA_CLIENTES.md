# Auditoría integral: Carga masiva de clientes

**Alcance:** CARGA MASIVA DE CLIENTES (modal "Sube tu archivo Excel" desde Nuevo Cliente / Clientes).  
**Fecha:** Auditoría de endpoints, conexión BD, validadores y código.

---

## 1. Resumen ejecutivo

| Aspecto | Estado | Notas |
|--------|--------|--------|
| **Arquitectura** | Frontend-only | No existe endpoint dedicado de carga masiva; el Excel se procesa en el navegador y cada fila se envía con `POST /api/v1/clientes`. |
| **Conexión BD** | ✅ Correcta | Cada creación usa `create_cliente` con `Depends(get_db)` y persiste en `public.clientes`. |
| **Validadores** | ✅ Frontend + Backend | Validación en ExcelUploader (formato cédula, nombres, teléfono, email, fecha, etc.) y en backend (Pydantic + reglas de duplicados). |
| **Duplicados** | ✅ Aplicados | Backend rechaza misma cédula, mismo nombre, mismo email o mismo teléfono (409). |
| **Riesgos** | ⚠️ 1 | Método `importarClientes` apunta a un endpoint inexistente (código no usado por el flujo actual). |

---

## 2. Endpoints

### 2.1 Endpoint real utilizado

- **Método y ruta:** `POST /api/v1/clientes`
- **Definición:** `backend/app/api/v1/endpoints/clientes.py` → `create_cliente(payload: ClienteCreate, db: Session = Depends(get_db))`
- **Uso en carga masiva:** El frontend **no** sube el archivo Excel al servidor. Lee el Excel en el navegador (ExcelJS), valida filas y, por cada fila válida, llama a `clienteService.createCliente(clienteData)` → una petición `POST /api/v1/clientes` por cliente.
- **Autenticación:** El router de clientes tiene `dependencies=[Depends(get_current_user)]`, por tanto todas las creaciones requieren usuario autenticado.

### 2.2 Endpoint documentado pero inexistente

- **Ruta documentada:** `POST /api/v1/carga-masiva/clientes` (referida en `docs/REGLAS_NEGOCIO_CLIENTES.md` y en `frontend/src/services/clienteService.ts`).
- **Código frontend:** `clienteService.importarClientes(file)` envía el archivo a `/api/v1/carga-masiva/clientes`.
- **Backend:** No existe router ni endpoint bajo `carga-masiva` en `backend/app/api/v1/__init__.py`. Solo están, entre otros, `clientes`, `pagos`, `cobranzas`, etc.
- **Conclusión:** El flujo real de carga masiva **no** usa `importarClientes` ni ese endpoint. El modal de carga masiva usa solo `createCliente` por fila. El método `importarClientes` es código muerto y fallaría con 404 si se invocara.

---

## 3. Conexión a base de datos

- **Configuración:** `app.core.database.get_db` inyecta la sesión; `engine` y `SessionLocal` usan `settings.DATABASE_URL` (`.env` / variables de entorno).
- **Uso en creación:** `create_cliente` recibe `db: Session = Depends(get_db)`, ejecuta `select(Cliente)...` para duplicados y luego `db.add(row)`, `db.commit()`, `db.refresh(row)`.
- **Tabla:** `public.clientes` (modelo `app.models.cliente.Cliente`).
- **Regla datos reales:** Se cumple: no hay stubs; todas las inserciones son contra la BD configurada.

---

## 4. Validadores

### 4.1 Frontend (ExcelUploader + excelValidation)

**Archivo / tipo de validación:**

| Origen | Archivo | Qué valida |
|--------|---------|------------|
| Archivo | `frontend/src/utils/excelValidation.ts` | Extensión (.xlsx, .xls), tipo MIME, tamaño máx. 10 MB, filas máx. 10 000, columnas máx. 100, nombre de archivo, estructura de datos extraídos. |
| Filas | `ExcelUploader.tsx` → `validateField` | Por campo: cédula (V/E/J/Z + 7-10 dígitos), nombres (2-7 palabras), teléfono (+58 + 10 dígitos), email (formato, sin espacios/comas), dirección (mín. 5 caracteres), estado (ACTIVO/INACTIVO/FINALIZADO), activo (true/false), fecha_nacimiento (DD/MM/YYYY, pasada, ≥18 años), ocupación (mín. 2 caracteres). |
| Regla "NN" | `ExcelUploader` | Si el valor es `nn` (cualquier caso), se trata como vacío (`blankIfNN`). |

**Columnas Excel esperadas (por índice):**  
A: cédula, B: nombres, C: telefono, D: email, E: direccion, F: fecha_nacimiento, G: ocupacion, H: estado, I: activo, J: notas.

### 4.2 Backend

- **Schema:** `ClienteCreate` (Pydantic) exige: `cedula`, `nombres`, `telefono`, `email`, `direccion`, `fecha_nacimiento`, `ocupacion`, `estado`, `usuario_registro`, `notas`.
- **Duplicados:** Antes de insertar, `create_cliente` comprueba:
  - Si ya existe un cliente con la misma **cédula** → 409.
  - Si ya existe un cliente con el mismo **nombre completo** (`nombres`) → 409.
- **Email/teléfono:** No se validan como duplicados; pueden repetirse.
- **Validadores de configuración:** `GET /api/v1/validadores/configuracion-validadores` devuelve reglas de validación (cédula, teléfono, email, fecha); la carga masiva no los llama; usa validación local en `validateField`.

---

## 5. Flujo de código (carga masiva)

1. Usuario abre "Nuevo Cliente" → botón "Cargar Excel" → se muestra el modal `ExcelUploader`.
2. Usuario selecciona o arrastra un archivo .xlsx/.xls.
3. `processExcelFile(file)`:
   - Valida archivo con `validateExcelFile` y `validateExcelData`.
   - Tamaño en memoria: rechazo si `data.byteLength > 10 * 1024 * 1024`.
   - Lee con `readExcelToJSON(data)` (ExcelJS, import dinámico).
   - Por cada fila (desde la 2): construye `ExcelRow`, valida cada campo con `validateField`, marca `_hasErrors`.
4. Se muestra la previsualización de la tabla; el usuario puede editar celdas y volver a validar.
5. Guardado:
   - **Por fila:** "Guardar" en una fila → `saveIndividualClient(row)` → `clienteService.createCliente(clienteData)` → `POST /api/v1/clientes`.
   - **Todos:** "Guardar todos los válidos" → `saveAllValidClients()` → para cada fila válida, mismo `createCliente` en secuencia.
6. Errores 409/400 se muestran con toast; el mensaje del backend (cédula o nombre duplicado) se reenvía al usuario.

---

## 6. Hallazgos y recomendaciones

### 6.1 Corregido: `usuario_registro` en carga masiva

- **Estado:** Corregido. En `ExcelUploader.tsx` se usa `useSimpleAuth()` y se envía `usuario_registro: user?.email ?? 'carga-masiva'` en `saveIndividualClient` y en `saveAllValidClients`.

### 6.2 Medio: Endpoint y método no utilizados

- **Hecho:** `clienteService.importarClientes(file)` y la ruta `POST /api/v1/carga-masiva/clientes` están documentados/referenciados pero el endpoint no existe; el flujo real usa solo `POST /api/v1/clientes` por fila.
- **Recomendación:**  
  - Opción A: Eliminar o marcar como deprecado `importarClientes` y actualizar la documentación para indicar que la carga masiva es vía múltiples `POST /api/v1/clientes`.  
  - Opción B: Implementar `POST /api/v1/carga-masiva/clientes` que reciba el Excel, lo parsee en el backend, valide y cree/actualice clientes en lote, y devuelva resumen de éxitos/errores por fila (mejor para auditoría y consistencia de validación en servidor).

### 6.3 Buenas prácticas ya aplicadas

- Validación de archivo (tipo, tamaño, estructura) antes de procesar.
- Límites de filas/columnas para evitar abusos.
- Duplicados por cédula y por nombre rechazados en backend con 409 y mensaje claro.
- Mensajes de error en frontend alineados con los detalles del backend (cédula vs nombre).
- Uso de `get_db` y persistencia real en `public.clientes`.

### 6.4 Estado "Online" en la UI

- El badge "Online" en el modal de carga masiva refleja el estado del servicio (por ejemplo comprobación de conectividad). No sustituye la validación en backend ni la comprobación de permisos; es solo informativo para el usuario.

---

## 7. Checklist de auditoría

| Ítem | Cumple |
|------|--------|
| Endpoints usados existen y están registrados | ✅ (solo `POST /api/v1/clientes`) |
| Creación de clientes usa BD real (`get_db`) | ✅ |
| Validación de duplicados (cédula/nombre) en backend | ✅ |
| Validación de formato en frontend (cédula, nombres, teléfono, email, fecha, etc.) | ✅ |
| Límites de tamaño y estructura del Excel | ✅ |
| Manejo de errores 409/400 en la UI | ✅ |
| Envío de `usuario_registro` en carga masiva | ✅ |
| Documentación alineada con implementación (carga-masiva) | ❌ |
| Endpoint dedicado de carga masiva (opcional) | No implementado |

---

## 8. Referencia de archivos

| Rol | Ruta |
|-----|------|
| Backend creación cliente | `backend/app/api/v1/endpoints/clientes.py` (`create_cliente`) |
| Schema cliente | `backend/app/schemas/cliente.py` (`ClienteCreate`, `ClienteBase`) |
| Modelo BD | `backend/app/models/cliente.py` |
| Frontend carga masiva UI | `frontend/src/components/clientes/ExcelUploader.tsx` |
| Validación archivo Excel | `frontend/src/utils/excelValidation.ts` |
| Servicio clientes | `frontend/src/services/clienteService.ts` (`createCliente`, `importarClientes`) |
| Lectura Excel | `frontend/src/types/exceljs.ts` (readExcelToJSON, import dinámico desde ExcelUploader) |
| Reglas de negocio clientes | `docs/REGLAS_NEGOCIO_CLIENTES.md` |
