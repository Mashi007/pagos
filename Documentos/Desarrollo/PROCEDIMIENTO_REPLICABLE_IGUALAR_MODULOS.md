# PROCEDIMIENTO REPLICABLE: Igualar Módulos al Template de Analistas

## OBJETIVO
Aplicar el mismo perfil y funcionalidades de Analistas a otros módulos (Concesionarios, Modelos, etc.)

## BASE DE DATOS
✅ **NO modificar estructura de tablas**
✅ **Conservar todos los registros existentes**
✅ **Solo agregar columnas** `created_at` y `updated_at` si no existen

## PASOS DEL PROCEDIMIENTO

### 1. ANÁLISIS PREVIO

#### 1.1 Verificar estructura BD
```sql
-- Verificar columnas existentes
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'tu_tabla';
```

#### 1.2 Identificar archivos del módulo
```
Backend:
- app/api/v1/endpoints/tu_modulo.py
- app/models/tu_modulo.py
- app/schemas/tu_modulo.py

Frontend:
- pages/TuModulo.tsx
- components/configuracion/TuModuloConfig.tsx
- hooks/useTuModulo.ts
- services/tuModuloService.ts
```

#### 1.3 Verificar duplicados
```bash
# Buscar duplicados en frontend
glob_file_search "**/*tu_modulo*.tsx"

# Buscar duplicados en backend
glob_file_search "**/*tu_modulo*.py"
```

---

### 2. CREAR/ACTUALIZAR HOOKS DE REACT QUERY

**Archivo**: `frontend/src/hooks/useTuModulo.ts`

**Contenido básico**:
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { tuModuloService, TuModulo, TuModuloCreate, TuModuloUpdate } from '@/services/tuModuloService'
import toast from 'react-hot-toast'

// Constantes
const STALE_TIME_MEDIUM = 5 * 60 * 1000
const STALE_TIME_LONG = 10 * 60 * 1000
const RETRY_COUNT = 3
const RETRY_DELAY = 1000

// Keys para React Query
export const tuModuloKeys = {
  all: ['tu_modulos'] as const,
  lists: () => [...tuModuloKeys.all, 'list'] as const,
  list: (filters?: any) => [...tuModuloKeys.lists(), filters] as const,
  details: () => [...tuModuloKeys.all, 'detail'] as const,
  detail: (id: number) => [...tuModuloKeys.details(), id] as const,
  activos: () => [...tuModuloKeys.all, 'activos'] as const,
}

// Hook para obtener lista
export function useTuModulos(filters?: any) {
  return useQuery({
    queryKey: tuModuloKeys.list(filters),
    queryFn: () => tuModuloService.listar(filters),
    staleTime: STALE_TIME_MEDIUM,
    retry: RETRY_COUNT,
    retryDelay: RETRY_DELAY,
  })
}

// Hook para crear
export function useCreateTuModulo() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: TuModuloCreate) => tuModuloService.crear(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tuModuloKeys.lists() })
      toast.success('Creado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al crear')
    },
  })
}

// Hook para actualizar
export function useUpdateTuModulo() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: TuModuloUpdate }) =>
      tuModuloService.actualizar(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tuModuloKeys.lists() })
      toast.success('Actualizado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al actualizar')
    },
  })
}

// Hook para eliminar
export function useDeleteTuModulo() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => tuModuloService.eliminar(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tuModuloKeys.lists() })
      toast.success('Eliminado exitosamente')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Error al eliminar')
    },
  })
}
```

---

### 3. ACTUALIZAR BACKEND

#### 3.1 Agregar orden por ID
**Archivo**: `backend/app/api/v1/endpoints/tu_modulo.py`

**Cambio**:
```python
# Después de los filtros, antes de count()
query = query.order_by(TuModulo.id)
```

#### 3.2 Actualizar updated_at manualmente en PUT
**Archivo**: `backend/app/api/v1/endpoints/tu_modulo.py`

**Cambio** (en función `actualizar_`):
```python
from datetime import datetime

# Después de setattr loop
tu_modulo.updated_at = datetime.utcnow()

db.commit()
```

---

### 4. CREAR/ACTUALIZAR PÁGINA PRINCIPAL

**Archivo**: `frontend/src/pages/TuModulo.tsx`

#### 4.1 Estructura requerida
1. **Estados**:
   - `searchTerm`
   - `showCreateForm`
   - `editingItem`
   - `formData`
   - `validationError`
   - `currentPage`
   - `itemsPerPage = 10`

2. **Hooks React Query**:
   - `useTuModulos()`
   - `useCreateTuModulo()`
   - `useUpdateTuModulo()`
   - `useDeleteTuModulo()`

3. **Validación** (2-4 palabras):
```typescript
const validateNombre = (nombre: string): string => {
  if (!nombre.trim()) return 'El nombre es requerido'
  const nombreLimpio = nombre.trim().replace(/\s+/g, ' ')
  const palabras = nombreLimpio.split(' ')

  if (palabras.length < 2) {
    return 'Debe ingresar al menos 2 palabras (Nombre y Apellido)'
  }
  if (palabras.length > 4) {
    return 'Debe ingresar máximo 4 palabras'
  }

  for (const palabra of palabras) {
    if (palabra.length < 2) {
      return 'Cada palabra debe tener al menos 2 caracteres'
    }
  }

  return ''
}
```

4. **Formateo** (capitalizar):
```typescript
const formatNombre = (nombre: string): string => {
  const nombreLimpio = nombre.trim().replace(/\s+/g, ' ')
  return nombreLimpio.split(' ').map(word => {
    if (word.length === 0) return word
    return word[0].toUpperCase() + word.slice(1).toLowerCase()
  }).join(' ')
}
```

5. **KPIs** (4 cards):
   - Total
   - Activos
   - Inactivos
   - Mostrados

6. **Paginación** (10 por página):
   - Botones Anterior/Siguiente
   - Números de página
   - Contador "Mostrando X a Y de Z"

7. **Modal** (Formulario popup):
   - Overlay con `onClick={resetForm}`
   - Validación 2-4 palabras
   - Botón "Estado" solo visible al editar
   - Campo "Estado" se muestra solo cuando `editingItem` existe

---

### 5. CREAR/ACTUALIZAR COMPONENTE DE CONFIGURACIÓN

**Archivo**: `frontend/src/components/configuracion/TuModuloConfig.tsx`

**IMPORTANTE**: Debe tener LA MISMA funcionalidad que `TuModulo.tsx` pero:
- Header con `h2` en lugar de `h1`
- Sin icono grande en header (mantener texto "Configuración de...")
- Usar React Query en lugar de `useState/useEffect`

**Estructura idéntica**:
- Mismos hooks
- Misma validación
- Misma paginación
- Mismos KPIs

---

### 6. ELIMINAR DUPLICADOS

#### 6.1 Backend
Buscar archivos residuales:
```bash
glob_file_search "**/*tu_modulo*.py"
```
- Si existe `verificar_tu_modulo.py` → ELIMINAR
- Solo debe existir `tu_modulo.py` en endpoints

#### 6.2 Frontend
Buscar componentes duplicados:
```bash
glob_file_search "**/*TuModulo*.tsx"
```

Debería haber:
- `pages/TuModulo.tsx` (página standalone)
- `components/configuracion/TuModuloConfig.tsx` (para Configuración)

Si existe versión antigua sin React Query → REEMPLAZAR

---

### 7. CHECKLIST FINAL

#### Backend
- [ ] Endpoint ordena por `id`
- [ ] PUT actualiza `updated_at` manualmente
- [ ] No hay archivos duplicados en endpoints
- [ ] Importado correctamente en `main.py`

#### Frontend
- [ ] Hooks creados con React Query
- [ ] Página principal usa hooks
- [ ] Componente de config usa hooks
- [ ] Validación 2-4 palabras implementada
- [ ] Paginación de 10 por página
- [ ] KPIs integrados a BD
- [ ] Botones Editar/Eliminar sin `disabled`
- [ ] Botón Guardar tiene `disabled` solo en `isPending`
- [ ] Modal funciona correctamente
- [ ] Toast usa `react-hot-toast`
- [ ] Campo "Estado" solo visible al editar

#### Verificación de Duplicados
- [ ] Solo existe 1 archivo de endpoints en backend
- [ ] Solo existen 2 archivos frontend: `TuModulo.tsx` y `TuModuloConfig.tsx`
- [ ] Ambos usan React Query
- [ ] Misma funcionalidad en ambos

---

### 8. COMMITS

```bash
git add .
git commit -m "feat: Equalizar TuModulo con template de Analistas
- Agregar React Query hooks
- Agregar validación de nombre (2-4 palabras)
- Agregar paginación (10 por página)
- Cambiar toast a react-hot-toast
- Ajustar KPIs para Boolean/Integer
- Ordenar por ID en backend
- Actualizar updated_at en PUT"

git push origin main
```

---

### 9. VERIFICACIÓN POST-DEPLOY

1. **Botones Activos**:
   - ✅ "Nuevo" sin disabled
   - ✅ "Editar" sin disabled
   - ✅ "Eliminar" sin disabled
   - ✅ "Guardar" disabled solo en isPending

2. **Formularios Conectados a BD**:
   - ✅ CREAR guarda en BD
   - ✅ EDITAR actualiza BD
   - ✅ ELIMINAR borra de BD
   - ✅ Fecha se actualiza en edit

3. **KPIs Integrados**:
   - ✅ Total muestra cantidad real
   - ✅ Activos muestra cantidad real
   - ✅ Inactivos muestra cantidad real
   - ✅ KPIs se actualizan automáticamente

4. **Sin Duplicados**:
   - ✅ Solo 1 archivo backend en endpoints
   - ✅ Solo 2 archivos frontend (página + config)
   - ✅ Ambos usan React Query

---

## RESUMEN DEL PROCEDIMIENTO

### Archivos a Crear/Modificar

**Backend** (1 archivo):
1. `backend/app/api/v1/endpoints/tu_modulo.py`

**Frontend** (4 archivos):
1. `frontend/src/hooks/useTuModulo.ts` (CREAR)
2. `frontend/src/pages/TuModulo.tsx` (REESCRIBIR)
3. `frontend/src/components/configuracion/TuModuloConfig.tsx` (REESCRIBIR)
4. `frontend/src/services/tuModuloService.ts` (VERIFICAR/ACTUALIZAR)

### Características Obligatorias

✅ React Query hooks
✅ Validación 2-4 palabras
✅ Paginación 10 por página
✅ Modal con overlay
✅ KPIs integrados a BD
✅ Toast con `react-hot-toast`
✅ Ordenar por ID en backend
✅ Actualizar `updated_at` en PUT
✅ Validación en frontend antes de guardar
✅ Botones siempre activos (excepto Guardar en isPending)

---

## EJEMPLO PRÁCTICO: Concesionarios

### Archivos modificados:
1. ✅ `backend/app/api/v1/endpoints/concesionarios.py`
2. ✅ `frontend/src/hooks/useConcesionarios.ts` (creado)
3. ✅ `frontend/src/pages/Concesionarios.tsx` (reescrito)
4. ✅ `frontend/src/components/configuracion/ConcesionariosConfig.tsx` (reescrito)

### Archivos eliminados:
1. ✅ `backend/app/api/v1/endpoints/verificar_concesionarios.py`

### Resultado:
- ✅ Base de datos original mantenida
- ✅ Registros originales conservados
- ✅ Sin duplicados
- ✅ Funcionalidad igual a Analistas
- ✅ KPIs integrados
- ✅ Botones y formularios conectados a BD

---

## SIGUIENTE: Aplicar a Modelos de Vehículos

Usar este mismo procedimiento para igualar `ModelosVehiculos` al template de Analistas.

