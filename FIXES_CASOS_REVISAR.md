# Asegurar Persistencia de Datos en Casos a Revisar

## Problema Identificado

Cuando los usuarios guardaban cambios en la sección "Casos a revisar" (`https://rapicredit.onrender.com/pagos/clientes`), los datos se guardaban en la base de datos correctamente, pero el frontend no reflejaba los cambios en tiempo real debido a:

1. **Falta de invalidación de cache en React Query**: El componente `CasosRevisarDialog` llamaba directamente al servicio sin invalidar el cache de React Query, por lo que otros componentes que mostraban datos de clientes no se actualizaban.

2. **Lógica de actualización duplicada**: La función `update_cliente` estaba siendo llamada desde `actualizar_clientes_lote` de forma incorrecta, sin pasar correctamente la dependencia de BD inyectada.

## Soluciones Implementadas

### 1. Backend: Refactorización del Endpoint de Actualización (`backend/app/api/v1/endpoints/clientes.py`)

Se extrajo la lógica de actualización en una función helper `_perform_update_cliente()`:

```python
def _perform_update_cliente(cliente_id: int, payload: ClienteUpdate, db: Session) -> ClienteResponse:
    """
    Lógica interna de actualización de cliente (reutilizable desde rutas y otros métodos).
    No se permite dejar cédula+nombres o email duplicados con otro cliente (distinto id) → 409.
    Retorna ClienteResponse tras guardar en BD.
    """
    # Validación y actualización del cliente
    # Guarda en BD con db.commit()
    return ClienteResponse.model_validate(row)
```

**Ventajas:**
- Reutilizable desde múltiples endpoints (PUT singular y POST lote)
- Garantiza que la BD siempre se actualiza con `db.commit()`
- Mantiene todas las validaciones de duplicados consistentes

**Cambios:**
- Líneas 428-493: Nueva función `_perform_update_cliente()`
- Línea 497-500: Endpoint PUT ahora usa la función helper
- Línea 275: `actualizar_clientes_lote` ahora usa la función helper correctamente

### 2. Frontend: Invalidación de Cache en React Query (`frontend/src/components/clientes/CasosRevisarDialog.tsx`)

Se importó `useQueryClient` y `clienteKeys` para invalidar el cache después de cada guardado:

**Cambios:**

a) **Importaciones (líneas 1-11):**
```typescript
import { useQueryClient } from '@tanstack/react-query'
import { clienteKeys } from '../../hooks/useClientes'
```

b) **Hook useQueryClient en el componente (línea 38):**
```typescript
const queryClient = useQueryClient()
```

c) **Invalidación después de guardar un cliente (líneas 75-85):**
```typescript
// ✅ Invalidar cache de React Query para reflejar cambios
queryClient.invalidateQueries({ queryKey: clienteKeys.lists() })
queryClient.invalidateQueries({ queryKey: clienteKeys.detail(String(c.id)) })
queryClient.invalidateQueries({
  queryKey: ['clientes', 'search'],
  exact: false
})
```

d) **Invalidación después de guardar todos (líneas 133-139):**
```typescript
// ✅ Invalidar cache de React Query después de guardar todos
queryClient.invalidateQueries({ queryKey: clienteKeys.lists() })
queryClient.invalidateQueries({
  queryKey: ['clientes', 'search'],
  exact: false
})
```

**Ventajas:**
- Los cambios se reflejan inmediatamente en todos los componentes que usan React Query
- Las búsquedas y listados se actualizan automáticamente
- No requiere recargar la página

## Garantías de Persistencia

### Backend (FastAPI)
✅ Todos los endpoints de actualización usan:
```python
db.commit()  # Persiste en la BD
db.refresh(row)  # Trae datos frescos del servidor
return ClienteResponse.model_validate(row)  # Devuelve respuesta JSON
```

### Frontend (React)
✅ Después de cada actualización:
1. Se invalidan todas las queries relacionadas con clientes
2. React Query automáticamente refetch los datos
3. Los componentes se actualizan con la información fresca

### Base de Datos (PostgreSQL)
✅ Configuración de conexión:
```python
# backend/app/core/database.py
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Objetos no se expiran tras commit
)
```

## Testing Manual

Para verificar que los cambios funcionan:

1. **Ir a**: `https://rapicredit.onrender.com/pagos/clientes`
2. **Abrir**: Modal "Casos a revisar"
3. **Editar**: Un cliente con valores placeholder
4. **Guardar**: El cambio individual
5. **Verificar**: 
   - El cliente desaparece de la lista (caso resuelto)
   - El listado de clientes general se actualiza
   - El cambio persiste al recargar la página

## Archivos Modificados

1. `backend/app/api/v1/endpoints/clientes.py`
   - Líneas 254-288: Función `actualizar_clientes_lote()` - Usa helper
   - Líneas 428-493: Nueva función `_perform_update_cliente()` - Helper
   - Líneas 497-500: Endpoint PUT - Usa helper

2. `frontend/src/components/clientes/CasosRevisarDialog.tsx`
   - Línea 1-11: Importaciones (agregado useQueryClient, clienteKeys)
   - Línea 38: useState con queryClient
   - Líneas 75-85: Invalidación en saveOne()
   - Líneas 133-139: Invalidación en saveAll()

## Datos Reales desde BD

Confirmado que:
- ✅ Los datos se leen desde `public.clientes` (tabla real)
- ✅ Las actualizaciones se guardan en `public.clientes`
- ✅ No hay stubs ni datos de demostración
- ✅ DATABASE_URL en .env controla la conexión
- ✅ Todas las validaciones usan datos reales de BD
