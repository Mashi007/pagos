# Auditoría integral: Modelos de Vehículos y articulación con Préstamos

**Fecha:** 2025-02-05  
**Ámbito:** [Modelos de Vehículos](https://rapicredit.onrender.com/pagos/modelos-vehiculos) y [Préstamos](https://rapicredit.onrender.com/pagos/prestamos)

## 1. Objetivos de la auditoría

- Asegurar que en **Modelos de Vehículos** se puedan **agregar**, **editar** (incluyendo el campo **precio**) y eliminar modelos.
- Verificar que la sección se **articule correctamente** con **Préstamos**: al seleccionar un modelo en "Nuevo Préstamo", el **Valor Activo** debe cargarse con el precio del modelo.

## 2. Estado inicial (hallazgos)

| Área | Estado |
|------|--------|
| **Backend** | Tabla `modelos_vehiculos` creada con `id`, `modelo`, `activo`, `precio`, timestamps. CRUD implementado (GET list/activos, GET by id, POST, PUT, DELETE). |
| **Frontend página** | Formulario con modelo, precio y estado; llamadas a create/update/delete. |
| **Articulación** | `CrearPrestamoForm` usa `useModelosVehiculosActivos()` y asigna `modeloSel.precio` a Valor Activo al seleccionar modelo. |
| **Problemas** | 1) Actualizar precio a "vacío" (null) no se aplicaba en backend. 2) Precio obligatorio en formulario. 3) Toasts duplicados. 4) Importación Excel devuelve 501 sin mensaje claro. 5) Moneda (VES) en UI mientras Valor Activo en préstamos es USD. |

## 3. Cambios realizados

### 3.1 Backend (`backend/app/api/v1/endpoints/modelos_vehiculos.py`)

- **Actualización de precio a `null`:** Se usa `payload.model_dump(exclude_unset=True)` para detectar si `precio` fue enviado en el body. Si viene `precio: null`, se actualiza el registro a `precio = None`.
- **Creación:** Ajuste de asignación de `precio` con manejo seguro de `Decimal` (incluye `precio: null` en create).

### 3.2 Frontend – Página Modelos de Vehículos (`frontend/src/pages/ModelosVehiculos.tsx`)

- **Precio opcional:** El campo Precio (USD) deja de ser obligatorio. Se puede crear/editar un modelo sin precio; en "Nuevo Préstamo" el usuario puede ingresar Valor Activo manualmente si el modelo no tiene precio.
- **Estado del formulario:** Se usa `precioInput` (string/número) para el input y se envía `precio: null` cuando el campo está vacío.
- **Toasts:** Eliminados toasts duplicados en la página; los hooks (`useCreateModeloVehiculo`, `useUpdateModeloVehiculo`) siguen mostrando un único toast por acción.
- **Importación Excel:** Si el backend responde 501, se muestra el mensaje: "Importación desde Excel no disponible por el momento."
- **Unidad monetaria:** Tabla y formulario usan **USD** (Precio (USD)) para alinearse con Valor Activo en Préstamos.
- **Texto de ayuda:** Subtítulo: "El precio (USD) se usa como Valor Activo al crear un préstamo." Placeholder del campo precio: "Opcional; se usa como Valor Activo en Nuevo Préstamo."

### 3.3 Frontend – Configuración (`frontend/src/components/configuracion/ModelosVehiculosConfig.tsx`)

- Misma lógica que la página principal: precio opcional, `precioInput`, payload con `precio: null` cuando corresponde, Precio (USD), y texto de ayuda coherente con Préstamos.

### 3.4 Servicio e tipos (`frontend/src/services/modeloVehiculoService.ts`)

- **ModeloVehiculoCreate:** `precio` pasa a ser opcional (`precio?: number | null`) para permitir crear modelos sin precio.

## 4. Flujo verificado: Modelos de Vehículos ↔ Préstamos

1. **Modelos de Vehículos**  
   - Listado: `GET /api/v1/modelos-vehiculos` (paginado) y `GET /api/v1/modelos-vehiculos/activos` (para formularios).  
   - Crear: `POST /api/v1/modelos-vehiculos` con `{ modelo, activo?, precio? }`.  
   - Editar: `PUT /api/v1/modelos-vehiculos/:id` con `{ modelo?, activo?, precio? }` (incluye `precio: null` para borrar precio).  
   - Eliminar: `DELETE /api/v1/modelos-vehiculos/:id`.

2. **Préstamos – Nuevo Préstamo**  
   - Carga modelos activos con `useModelosVehiculosActivos()` → `GET /api/v1/modelos-vehiculos/activos`.  
   - Al elegir un modelo, si `modelo.precio != null` se asigna a **Valor Activo**; si no, el usuario ingresa el valor manualmente.  
   - Invalidación de caché: al crear/actualizar/eliminar un modelo, los hooks invalidan `modeloVehiculoKeys.activos()`, por lo que la próxima apertura de "Nuevo Préstamo" obtiene la lista actualizada.

3. **Consistencia**  
   - Precio en Modelos de Vehículos = Valor Activo (USD) en Préstamos.  
   - Solo modelos con `activo: true` aparecen en el desplegable de "Nuevo Préstamo".

## 5. Checklist de verificación

- [x] Agregar modelo (con o sin precio).
- [x] Editar modelo (nombre, precio, estado activo/inactivo).
- [x] Poder dejar precio vacío al editar (actualiza a `null` en BD).
- [x] Eliminar modelo.
- [x] Listado y búsqueda en la página de Modelos de Vehículos.
- [x] En Nuevo Préstamo, al seleccionar modelo con precio, se rellena Valor Activo.
- [x] En Nuevo Préstamo, modelos sin precio permiten ingresar Valor Activo manualmente.
- [x] Precio expresado en USD en Modelos de Vehículos y en Préstamos.
- [x] Mensaje claro cuando la importación Excel no está disponible (501).

## 6. Despliegue y migración

- La tabla `modelos_vehiculos` se crea con `Base.metadata.create_all()` al arrancar el backend si no existe.
- Script opcional: `backend/sql/migracion_modelos_vehiculos.sql` (crear tabla e índices).  
- Opcional: rellenar desde préstamos existentes (comentado en el mismo SQL) con `INSERT ... ON CONFLICT (modelo) DO NOTHING` para tener modelos con precio `NULL` y luego completar en la UI.

## 7. Resumen

La auditoría confirma que **Modelos de Vehículos** permite **agregar**, **editar** (incluido el campo **precio** y dejarlo vacío) y **eliminar** modelos, y que se **articula correctamente** con **Préstamos**: el precio del modelo se usa como **Valor Activo** en "Nuevo Préstamo" cuando está definido, con UX y mensajes alineados (USD, precio opcional, manejo de 501 en Excel).
