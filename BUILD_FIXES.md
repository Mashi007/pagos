# ✅ CORRECCIONES NECESARIAS PARA BUILD DE RENDER

**Estado:** Identificadas 14 errores de TypeScript  
**Nivel de criticidad:** ALTA - Build fallando en Render  
**Tiempo estimado de corrección:** 10-15 minutos

---

## 🔴 Errores Reportados

### 1. TrainingWorkflow.tsx - Missing Properties (5 errores)

**Archivo:** `frontend/src/components/configuracion/fineTuning/TrainingWorkflow.tsx`

**Errores:**
- Line 110: `job.finalizado_en` doesn't exist on FineTuningJob
- Line 112: `job.finalizado_en` doesn't exist on FineTuningJob
- Line 326, 331, 333: `job.modelo_id` doesn't exist
- Line 365, 367: `job.mensaje_error` doesn't exist

**Solución:**

Añade estas propiedades a la interfaz `FineTuningJob` en `services/aiTrainingService.ts`:

```typescript
export interface FineTuningJob {
  id: number
  nombre?: string
  estado: 'pendiente' | 'en_progreso' | 'completado' | 'fallido'
  fecha_creacion: string
  fecha_inicio?: string
  fecha_fin?: string
  finalizado_en?: string | Date | null  // ✅ AÑADIR
  modelo_id?: string | null               // ✅ AÑADIR
  mensaje_error?: string | null           // ✅ AÑADIR
  // ... resto de propiedades
}
```

---

### 2. index.ts - Missing Prop Type Exports (4 errores)

**Archivo:** `frontend/src/components/configuracion/fineTuning/index.ts`

**Errores:**
- Line 6: No exported member `ConversationManagementProps`
- Line 9: No exported member `ConversationFormsProps`
- Line 12: No exported member `StatisticsPanelProps`
- Line 15: No exported member `TrainingWorkflowProps`

**Solución:**

Para cada componente, añade la interfaz de props:

**ConversationManagement.tsx:**
```typescript
export interface ConversationManagementProps {
  conversaciones: ConversacionAI[]
  cargando: boolean
  onAddNew?: () => void
  onEdit?: (conversacionId: number) => void
  onDelete?: (conversacionId: number) => void
  onRate?: (conversacionId: number, calificacion: number) => void
}

export function ConversationManagement(props: ConversationManagementProps) {
  // ... componente
}
```

**ConversationForms.tsx:**
```typescript
export interface ConversationFormsProps {
  mostrarForm: boolean
  cargando: boolean
  onClose?: () => void
  onSubmit?: (data: any) => void
  editandoId?: number | null
}

export function ConversationForms(props: ConversationFormsProps) {
  // ... componente
}
```

**StatisticsPanel.tsx:**
```typescript
export interface StatisticsPanelProps {
  estadisticas: any
  cargando: boolean
}

export function StatisticsPanel(props: StatisticsPanelProps) {
  // ... componente
}
```

**TrainingWorkflow.tsx:** (ya existe la interfaz, solo asegurar que se exporta)
```typescript
export interface TrainingWorkflowProps {
  jobs: FineTuningJob[]
  cargando: boolean
  onStartTraining?: () => void
  onCancelJob?: (jobId: number) => void
  onDeleteJob?: (jobId: number) => void
  onActivateModel?: (modeloId: string) => void
}

export function TrainingWorkflow(props: TrainingWorkflowProps) {
  // ... componente
}
```

---

### 3. useFineTuning.ts - Type Mismatches (7 errores)

**Archivo:** `frontend/src/hooks/useFineTuning.ts`

#### 3.1 Line 80: SetStateAction Mismatch
```typescript
// ❌ INCORRECTO
setConversaciones({ conversaciones, total, page, total_pages })

// ✅ CORRECTO
setConversaciones(conversaciones)
// Almacenar pagination info en estado separado si es necesario
```

#### 3.2 Line 201: Method 'eliminarConversacion' doesn't exist
```typescript
// Asegurar que aiTrainingService tiene este método:
async eliminarConversacion(id: number): Promise<void> {
  await apiClient.delete(`/api/v1/configuracion/ai/conversaciones/${id}`)
}
```

#### 3.3 Lines 217, 233, 250: 'tipo' property invalid
```typescript
// ❌ INCORRECTO
await aiTrainingService.mejorarConversacion({
  tipo: 'pregunta',
  pregunta: nuevaPregunta
})

// ✅ CORRECTO - Definir interfaz correcta
interface MejoraConversacionRequest {
  tipo: 'pregunta' | 'respuesta' | 'conversacion'
  pregunta?: string
  respuesta?: string
}

// Usar:
await aiTrainingService.mejorarConversacion({
  tipo: 'pregunta',
  pregunta: nuevaPregunta
})
```

#### 3.4 Lines 277, 279: 'num_conversaciones' property
```typescript
// ❌ INCORRECTO
result.num_conversaciones

// ✅ CORRECTO - Usar el nombre correcto del API
result.total_conversaciones

// O añadir alias en el servicio:
interface PrepararDatosResponse {
  archivo_id: string
  total_conversaciones: number
  num_conversaciones?: number // Alias
}
```

#### 3.5 Line 317: 'activarModelo' method doesn't exist
```typescript
// Asegurar que aiTrainingService tiene este método:
async activarModelo(modeloId: string): Promise<void> {
  await apiClient.post(`/api/v1/configuracion/ai/modelos/${modeloId}/activar`, {})
}
```

---

## 📋 PLAN DE ACCIÓN

### Paso 1: Crear archivos de tipos (YA HECHO)
- ✅ `frontend/src/types/aiTypes.ts` - Interfices centralizadas

### Paso 2: Actualizar AITrainingService
**Archivo:** `frontend/src/services/aiTrainingService.ts`

Implementar estos métodos exactos:
```typescript
async cargarConversaciones(params?: { page?: number; limit?: number }): Promise<...>
async crearConversacion(data: { pregunta: string; respuesta: string }): Promise<ConversacionAI>
async actualizarConversacion(id: number, data: ...): Promise<ConversacionAI>
async eliminarConversacion(id: number): Promise<void>  // ✅ FALTABA
async calificarConversacion(id: number, data: ...): Promise<ConversacionAI>
async mejorarConversacion(data: MejoraConversacionRequest): Promise<...>  // ✅ VERIFICAR FIRMA
async cargarJobs(): Promise<FineTuningJob[]>
async prepararDatosEntrenamiento(): Promise<PrepararDatosResponse>
async iniciarEntrenamiento(data: ...): Promise<FineTuningJob>
async activarModelo(modeloId: string): Promise<void>  // ✅ FALTABA
async cancelarJob(jobId: number): Promise<void>
async eliminarJob(jobId: number): Promise<void>
```

### Paso 3: Actualizar componentes de FineTuning

**TrainingWorkflow.tsx:**
- Importar tipos: `import { FineTuningJob } from '../../../types/aiTypes'`
- Usar propiedades correctas: `finalizado_en`, `modelo_id`, `mensaje_error`

**index.ts:**
- Exportar interfaces Props de cada componente
- Actualizar imports

**Componentes (ConversationManagement, ConversationForms, StatisticsPanel):**
- Añadir interfaces Props
- Tipificar correctamente

### Paso 4: Corregir useFineTuning.ts

Cambios específicos:
```typescript
// Line 80: Arreglar setState
const [conversaciones, setConversaciones] = useState<ConversacionAI[]>([])
// Usar solo:
setConversaciones(data.conversaciones)

// Lines 217, 233, 250: Asegurar firma correcta
const mejorada = await aiTrainingService.mejorarConversacion({
  tipo: 'pregunta' | 'respuesta' | 'conversacion',
  pregunta?: string,
  respuesta?: string
})

// Lines 277, 279: Usar property correcta
const { total_conversaciones } = await aiTrainingService.prepararDatosEntrenamiento()
```

### Paso 5: Verificar build
```bash
npm run lint
npm run build
```

---

## 🎯 ORDEN RECOMENDADO

1. **Actualizar `services/aiTrainingService.ts`** (5 min)
   - Añadir métodos faltantes: `eliminarConversacion`, `activarModelo`
   - Asegurar firmas correctas de métodos
   - Exportar tipos correctamente

2. **Actualizar `types/aiTypes.ts`** - YA HECHO (10 min)
   - Interfaces centralizadas
   - Propiedades faltantes en FineTuningJob

3. **Actualizar componentes de FineTuning** (7 min)
   - Añadir interfaces Props
   - Importar tipos correctos
   - Actualizar index.ts

4. **Corregir useFineTuning.ts** (5 min)
   - Arreglar setState
   - Usar métodos correctos
   - Usar property names correctos

5. **Testing** (3 min)
   - `npm run lint`
   - `npm run build`

**Tiempo total: ~30 minutos**

---

## 📌 NOTA IMPORTANTE

El archivo `frontend/src/types/aiTypes.ts` YA FUE CREADO con todas las interfaces necesarias.

Ahora solo falta:
1. Actualizar el servicio AITrainingService
2. Actualizar los componentes  
3. Corregir el hook useFineTuning

Después, el build debe pasar sin errores.
