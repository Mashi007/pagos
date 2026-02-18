# Revisión: Conexión de la tabla `clientes` con backend y frontend

**Fecha:** 18 Feb 2025  
**Objetivo:** Verificar que la tabla `clientes` esté correctamente conectada con préstamos, tickets, comunicaciones y otras tablas.

---

## 1. Modelos y relaciones en backend

### 1.1 Tablas que referencian `clientes`

| Tabla      | Columna    | FK              | Uso                                      |
|------------|------------|------------------|------------------------------------------|
| **prestamos** | `cliente_id` | `clientes.id` (NOT NULL) | Cada préstamo pertenece a un cliente      |
| **cuotas**    | `cliente_id` | `clientes.id` (nullable)  | Cuotas pueden tener cliente directo      |
| **tickets**   | `cliente_id` | `clientes.id` (nullable)  | Tickets CRM asociados a clientes         |
| **pagos**     | —           | —                | Conecta vía `prestamo_id` → prestamo → cliente |

### 1.2 Modelo Cliente

```python
# app/models/cliente.py
class Cliente(Base):
    __tablename__ = "clientes"
    id, cedula, nombres, telefono, email, direccion, fecha_nacimiento,
    ocupacion, estado, fecha_registro, fecha_actualizacion, usuario_registro, notas
```

### 1.3 Modelo Prestamo

```python
# app/models/prestamo.py
cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
```

---

## 2. Endpoints backend – uso de clientes

### 2.1 Préstamos (`/api/v1/prestamos`)

| Endpoint / acción | Conexión con clientes |
|-------------------|------------------------|
| `GET /prestamos`  | JOIN con Cliente; devuelve `nombres`, `cedula`, `cliente_id`; filtros `cliente_id`, `cedula`, `search` (por cédula/nombres) |
| `GET /prestamos/{id}` | Incluye `cliente_id` del préstamo |
| `POST /prestamos` | Valida que `cliente_id` exista; toma `cedula` y `nombres` del Cliente |
| `PUT /prestamos/{id}` | Permite actualizar `cliente_id`; valida que el cliente exista |

### 2.2 Tickets (`/api/v1/tickets`)

| Endpoint / acción | Conexión con clientes |
|-------------------|------------------------|
| `GET /tickets`    | Filtro `cliente_id`; respuesta incluye `clienteData` (nombres, cedula, telefono, email) |
| `POST /tickets`   | Acepta `cliente_id` |
| `PUT /tickets/{id}` | Permite actualizar `cliente_id` |

### 2.3 Comunicaciones (`/api/v1/comunicaciones`)

| Endpoint / acción | Conexión con clientes |
|-------------------|------------------------|
| `GET /comunicaciones` | Filtro `cliente_id`; vincula por `clientes.telefono` ↔ `conversacion_cobranza.telefono` |

### 2.4 Dashboard, KPIs, Pagos, Reportes

- Todas las consultas que involucran préstamos hacen `JOIN` con `Cliente` y filtran por `Cliente.estado == "ACTIVO"`.
- Consistencia: solo se consideran clientes ACTIVOS para métricas y reportes.

---

## 3. Frontend – uso de clientes

### 3.1 Préstamos

| Componente / servicio | Uso de clientes |
|----------------------|------------------|
| `PrestamosList.tsx`  | Muestra `prestamo.nombres ?? prestamo.nombre_cliente ?? Cliente #${prestamo.cliente_id}` |
| `CrearPrestamoForm.tsx` | Busca cliente por cédula (`useSearchClientes`); al crear, envía `cliente_id: clienteData.id` |
| `prestamoService.ts` | No envía `cliente_id` en filtros (el backend sí lo soporta) |
| `usePrestamos.ts`    | `PrestamoFilters` no incluye `cliente_id` |

### 3.2 Tickets

| Componente / servicio | Uso de clientes |
|----------------------|------------------|
| `TicketsAtencion.tsx` | Muestra `clienteId`; enlace "Ver cliente completo" → `/clientes/{clienteId}` |
| `ticketsService.ts`   | Envía `cliente_id` en filtros al listar tickets |

### 3.3 Comunicaciones

| Componente / servicio | Uso de clientes |
|----------------------|------------------|
| `Comunicaciones.tsx` | Recibe `clienteId` por URL (`?cliente_id=`); pasa a `listarComunicaciones(..., clienteId)` |
| `comunicacionesService.ts` | Añade `cliente_id` a params cuando `clienteId` está definido |

### 3.4 Clientes

| Componente / servicio | Uso |
|-----------------------|-----|
| `ClientesList.tsx`    | Enlaces a Comunicaciones: `/comunicaciones?cliente_id=${cliente.id}` |
| `EmbudoClientes.tsx`  | Filtra `prestamos.filter(p => p.cliente_id === cliente.id)`; navega a `/clientes/${cliente.id}` |
| `EmbudoConcesionarios.tsx` | Usa `prestamo.cliente_id` para vincular préstamos con clientes |

---

## 4. Resumen de estado

### Correctamente conectado

1. **Préstamos ↔ Clientes**
   - Backend: FK, JOIN, filtros y validación de `cliente_id`.
   - Frontend: Crear préstamo usa `cliente_id`; listado muestra nombres del cliente.

2. **Tickets ↔ Clientes**
   - Backend: FK, filtro `cliente_id`, `clienteData` en respuesta.
   - Frontend: Filtro por cliente y enlace a detalle de cliente.

3. **Comunicaciones ↔ Clientes**
   - Backend: Filtro `cliente_id`; vinculación por teléfono.
   - Frontend: `clienteId` por URL y en llamadas al servicio.

4. **Cuotas ↔ Clientes**
   - Modelo con `cliente_id` (nullable); uso en lógica de morosidad y reportes.

### Mejoras opcionales

1. **Filtro por cliente en préstamos**
   - Backend ya soporta `cliente_id` en `GET /prestamos`.
   - Frontend: añadir `cliente_id` a `PrestamoFilters` y `prestamoService.getPrestamos` si se quiere filtrar desde la vista de cliente.

2. **Ruta `/clientes/:id`**
   - Existe la ruta pero `ClientesList` no usa `useParams` para mostrar detalle de un cliente.
   - Al abrir `/clientes/123` desde Tickets o Embudo, se muestra la lista general, no el detalle del cliente 123.
   - Opción: crear vista de detalle de cliente con préstamos, tickets y comunicaciones.

3. **Endpoint `/clientes/{id}/prestamos`**
   - No existe; para listar préstamos de un cliente se usa `GET /prestamos?cliente_id={id}`.
   - No es obligatorio añadirlo si el filtro actual es suficiente.

---

## 5. Conclusión

La tabla `clientes` está correctamente conectada con:

- **Préstamos**: FK, JOIN, validación y uso en creación/edición.
- **Tickets**: FK, filtros y datos de cliente en respuestas.
- **Comunicaciones**: filtro por cliente y vinculación por teléfono.
- **Cuotas**: FK y uso en reportes y morosidad.

No se detectan errores de integración. Las mejoras sugeridas son opcionales y orientadas a UX (filtros y vista de detalle de cliente).
