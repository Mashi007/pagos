# 🎯 GUÍA PASO A PASO - CORREGIR 14 ERRORES DE BUILD

**Duración estimada:** 25-30 minutos  
**Complejidad:** Media  
**Riesgo:** Bajo (cambios bien documentados)

---

## ERRORES A CORREGIR (14 Total)

```
✓ 5 errores - Missing properties on FineTuningJob
✓ 4 errores - Missing type exports in index.ts  
✓ 3 errores - Missing methods in AITrainingService
✓ 2 errores - Property name mismatches
```

---

## PASO 1️⃣: ACTUALIZAR SERVICES/AITRAININGSERVICE.TS

**Archivo:** `frontend/src/services/aiTrainingService.ts`

### 1A. Encontrar la clase AITrainingService
Busca: `class AITrainingService` o `export class AITrainingService`

### 1B. VERIFICAR/AÑADIR estos métodos

#### Método 1: eliminarConversacion (FALTABA)
```typescript
/**
 * Eliminar conversación
 */
async eliminarConversacion(id: number): Promise<void> {
  await apiClient.delete(`/api/v1/configuracion/ai/conversaciones/${id}`)
}
```
**Ubicación:** Después de `actualizarConversacion`, antes de `calificarConversacion`

#### Método 2: activarModelo (FALTABA)
```typescript
/**
 * Activar modelo (línea 317 de useFineTuning)
 */
async activarModelo(modeloId: string): Promise<void> {
  await apiClient.post(`/api/v1/configuracion/ai/modelos/${modeloId}/activar`, {})
}
```
**Ubicación:** Después de `iniciarEntrenamiento`, antes de `cancelarJob`

#### Método 3: Verificar mejorarConversacion
Debe verse así:
```typescript
/**
 * Mejorar conversación - Debe aceptar 'tipo' property
 */
async mejorarConversacion(data: {
  tipo: 'pregunta' | 'respuesta' | 'conversacion'
  pregunta?: string
  respuesta?: string
}): Promise<any> {
  const response = await apiClient.post(
    '/api/v1/configuracion/ai/mejorar-conversacion',
    data
  )
  return response
}
```

#### Método 4: Verificar prepararDatosEntrenamiento
Debe retornar `total_conversaciones`, no `num_conversaciones`:
```typescript
async prepararDatosEntrenamiento(): Promise<{
  archivo_id: string
  total_conversaciones: number  // ✅ IMPORTANTE: total_conversaciones
  conversaciones_originales?: number
  conversaciones_excluidas?: number
  detalles_exclusion?: Array<any>
}> {
  const response = await apiClient.post(
    '/api/v1/configuracion/ai/preparar-datos',
    {}
  )
  return response
}
```

---

## PASO 2️⃣: ACTUALIZAR TIPOS EN AITRAININGSERVICE.TS

### 2A. Importar tipos
Al inicio del archivo, añade:
```typescript
import type {
  ConversacionAI,
  FineTuningJob,
  MejoraConversacionRequest,
  PrepararDatosResponse,
} from '../types/aiTypes'
```

### 2B. Exportar tipos
Al final del archivo, añade:
```typescript
export type { FineTuningJob, ConversacionAI, PrepararDatosResponse }
```

---

## PASO 3️⃣: ACTUALIZAR TYPES/AITYPES.TS

**Archivo:** `frontend/src/types/aiTypes.ts` (YA CREADO, solo verificar)

### 3A. Verificar que contiene estas interfaces:
```typescript
export interface FineTuningJob {
  id: number
  estado: 'pendiente' | 'en_progreso' | 'completado' | 'fallido'
  fecha_creacion: string
  finalizado_en?: string | Date | null  // ✅ Para lines 110, 112
  modelo_id?: string | null               // ✅ Para lines 326, 331, 333
  mensaje_error?: string | null           // ✅ Para lines 365, 367
  // ... más propiedades
}

export interface ConversationManagementProps { /* ... */ }
export interface ConversationFormsProps { /* ... */ }
export interface StatisticsPanelProps { /* ... */ }
export interface TrainingWorkflowProps { /* ... */ }
export interface MejoraConversacionRequest {
  tipo: 'pregunta' | 'respuesta' | 'conversacion'
  pregunta?: string
  respuesta?: string
}
export interface PrepararDatosResponse {
  archivo_id: string
  total_conversaciones: number
  num_conversaciones?: number // Alias
}
```

---

## PASO 4️⃣: ACTUALIZAR COMPONENTES FINETUNNING

**Archivo:** `frontend/src/components/configuracion/fineTuning/TrainingWorkflow.tsx`

### 4A. Añadir import de tipos
```typescript
// Busca imports al inicio
import { FineTuningJob } from '../../../types/aiTypes'

// Asegurate que está importado
export interface TrainingWorkflowProps {
  jobs: FineTuningJob[]
  cargando: boolean
  onStartTraining?: () => void
  onCancelJob?: (jobId: number) => void
  onDeleteJob?: (jobId: number) => void
  onActivateModel?: (modeloId: string) => void
}

export function TrainingWorkflow(props: TrainingWorkflowProps) {
  // ... el resto del componente
}
```

**Esto corrige los 5 errores de propiedades:**
- Line 110: Ahora `job.finalizado_en` existe ✅
- Line 112: Ahora `job.finalizado_en` existe ✅  
- Line 326: Ahora `job.modelo_id` existe ✅
- Line 331: Ahora `job.modelo_id` existe ✅
- Line 333: Ahora `job.modelo_id` existe ✅
- Line 365: Ahora `job.mensaje_error` existe ✅
- Line 367: Ahora `job.mensaje_error` existe ✅

---

## PASO 5️⃣: ACTUALIZAR COMPONENTES CONVERSACION

**Archivo:** `frontend/src/components/configuracion/fineTuning/ConversationManagement.tsx`

### 5A. Añadir export de interfaz Props
```typescript
import { ConversationManagementProps } from '../../../types/aiTypes'

export function ConversationManagement(props: ConversationManagementProps) {
  // ... resto del componente
}
```

---

**Archivo:** `frontend/src/components/configuracion/fineTuning/ConversationForms.tsx`

### 5B. Añadir export de interfaz Props
```typescript
import { ConversationFormsProps } from '../../../types/aiTypes'

export function ConversationForms(props: ConversationFormsProps) {
  // ... resto del componente
}
```

---

**Archivo:** `frontend/src/components/configuracion/fineTuning/StatisticsPanel.tsx`

### 5C. Añadir export de interfaz Props
```typescript
import { StatisticsPanelProps } from '../../../types/aiTypes'

export function StatisticsPanel(props: StatisticsPanelProps) {
  // ... resto del componente
}
```

---

## PASO 6️⃣: ACTUALIZAR INDEX.TS

**Archivo:** `frontend/src/components/configuracion/fineTuning/index.ts`

### 6A. Actualizar exports de tipos
```typescript
// Actualizar estos exports:
export { ConversationManagement } from './ConversationManagement'
export type { ConversationManagementProps } from '../../../types/aiTypes'

export { ConversationForms } from './ConversationForms'
export type { ConversationFormsProps } from '../../../types/aiTypes'

export { StatisticsPanel } from './StatisticsPanel'
export type { StatisticsPanelProps } from '../../../types/aiTypes'

export { TrainingWorkflow } from './TrainingWorkflow'
export type { TrainingWorkflowProps } from '../../../types/aiTypes'
```

**Esto corrige los 4 errores de exports:**
- Line 6: Ahora ConversationManagementProps existe ✅
- Line 9: Ahora ConversationFormsProps existe ✅
- Line 12: Ahora StatisticsPanelProps existe ✅
- Line 15: Ahora TrainingWorkflowProps existe ✅

---

## PASO 7️⃣: CORREGIR USEFINETUNNING.TS

**Archivo:** `frontend/src/hooks/useFineTuning.ts`

### 7A. Line 80 - Arreglar setState
```typescript
// ❌ ANTES (INCORRECTO):
setConversaciones({ conversaciones, total, page, total_pages })

// ✅ DESPUÉS (CORRECTO):
setConversaciones(conversaciones)

// Si necesitas guardar pagination, usa estado separado:
const [pagination, setPagination] = useState({ total, page, total_pages })
```

### 7B. Line 201 - Método eliminarConversacion
Ahora que añadimos el método en Step 1, esto debe funcionar. Verifica que se llama:
```typescript
await aiTrainingService.eliminarConversacion(conversacionId)
```

### 7C. Lines 217, 233, 250 - mejorarConversacion
Verifica que se llama correctamente:
```typescript
const mejora = await aiTrainingService.mejorarConversacion({
  tipo: 'pregunta',  // ✅ Ahora 'tipo' es válido
  pregunta: nuevaPregunta
})
```

### 7D. Lines 277, 279 - Property name
```typescript
// ❌ ANTES:
const { num_conversaciones } = result

// ✅ DESPUÉS (ambas funcionan ahora):
const { total_conversaciones } = result
// O si tiene alias:
const { num_conversaciones } = result
```

### 7E. Line 317 - activarModelo
Ahora que añadimos el método en Step 1, esto debe funcionar:
```typescript
await aiTrainingService.activarModelo(modeloId)
```

---

## PASO 8️⃣: VERIFICAR BUILD

```bash
# En la raíz del proyecto

# Paso 1: Linting
npm run lint

# Paso 2: Build completo
npm run build

# Si todo está bien, verás:
# "✓ Built in Xs"
```

### Si hay errores aún:
```bash
# Ver detalle de errores
npm run build 2>&1 | head -50

# Buscar error específico
npm run build 2>&1 | grep "error TS"
```

---

## 📋 CHECKLIST FINAL

- [ ] **Step 1** - Métodos añadidos en AITrainingService
  - [ ] eliminarConversacion()
  - [ ] activarModelo()
  - [ ] mejorarConversacion() verificado
  - [ ] prepararDatosEntrenamiento() retorna `total_conversaciones`

- [ ] **Step 2** - Imports/Exports en AITrainingService
  - [ ] Imports añadidos
  - [ ] Tipos exportados

- [ ] **Step 3** - aiTypes.ts verificado
  - [ ] FineTuningJob tiene propiedades nuevas
  - [ ] Interfaces Props definidas

- [ ] **Step 4** - TrainingWorkflow.tsx actualizado
  - [ ] Import de FineTuningJob
  - [ ] Interfaz TrainingWorkflowProps exportada

- [ ] **Step 5** - Componentes conversation actualizados
  - [ ] ConversationManagement tiene interfaz Props
  - [ ] ConversationForms tiene interfaz Props
  - [ ] StatisticsPanel tiene interfaz Props

- [ ] **Step 6** - index.ts actualizado
  - [ ] Exports de tipos añadidos

- [ ] **Step 7** - useFineTuning.ts corregido
  - [ ] Line 80: setState arreglado
  - [ ] Métodos nuevos usados correctamente
  - [ ] Property names correctos

- [ ] **Step 8** - Build verificado
  - [ ] `npm run lint` sin errores
  - [ ] `npm run build` sin errores

---

## 🎉 CUANDO TODO ESTÉ LISTO

```bash
# Commit los cambios
git add .
git commit -m "fix: corregir 14 errores TypeScript en AI training y fineTuning components"

# Push a remote si tienes remoto configurado
git push origin main  # o tu rama
```

---

## ⚠️ TIPS IMPORTANTES

1. **Cambios atómicos** - Hazlos de a uno y verifica
2. **Salva frecuentemente** - Ctrl+S después de cada cambio
3. **Linea por linea** - No hagas cambios en masa
4. **Verifica tipos** - Usa TypeScript checks en IDE
5. **Test en browser** - Después de build exitoso

---

## 📞 SI ALGO FALLA

### Error: "Cannot find module"
→ Verifica imports en paso 2 y 3

### Error: "Property does not exist"
→ Verifica que interfaces están en aiTypes.ts

### Error: "Type mismatch"
→ Verifica firmas de métodos en AITrainingService

### Error en build aún después de cambios
```bash
# Limpiar cache
rm -rf node_modules/.vite
npm run build --verbose
```

---

**¡Listo! Sigue estos pasos y tu build debería pasar. 🚀**
