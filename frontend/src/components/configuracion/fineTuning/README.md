# Fine-Tuning Module - Refactored Architecture

This directory contains the refactored Fine-Tuning module for managing AI model training conversations and workflows. The original monolithic `FineTuningTab.tsx` (2000+ lines) has been decomposed into modular, maintainable components.

## Architecture Overview

### File Structure

```
fineTuning/
├── ConversationManagement.tsx  # Conversation list display and CRUD
├── ConversationForms.tsx        # New conversation creation form
├── StatisticsPanel.tsx          # Feedback statistics and analytics
├── TrainingWorkflow.tsx         # Training job management and orchestration
└── README.md                    # This file

hooks/
└── useFineTuning.ts            # Custom hook with all data fetching and handlers
```

### Component Hierarchy

```
FineTuningTab (main orchestrator)
├── StatisticsPanel
├── ConversationManagement
├── ConversationForms
└── TrainingWorkflow
```

## Component Descriptions

### 1. **FineTuningTab.tsx** (~100 lines)
**Location:** `frontend/src/components/configuracion/FineTuningTab.tsx`

Main component wrapper that orchestrates the entire fine-tuning workflow.

**Responsibilities:**
- Initialize the `useFineTuning` hook
- Manage overall UI state (statistics panel visibility, feedback filter toggle)
- Calculate derived state (ready conversations count, filtered count)
- Load initial data on mount
- Compose and render all sub-components
- Handle high-level data preparation and training workflows

**State Management:**
- Uses `useFineTuning` hook for all data and handlers
- Local state for UI visibility (`mostrarEstadisticas`, `filtrarFeedbackNegativo`)
- Refs for file input handling

### 2. **ConversationManagement.tsx** (~350 lines)
**Location:** `frontend/src/components/configuracion/fineTuning/ConversationManagement.tsx`

Displays and manages the conversation list with editing and rating capabilities.

**Features:**
- View conversation list with pagination/scrolling
- Edit existing conversations (inline edit mode)
- Rate conversations (1-5 stars with optional feedback)
- Delete conversations
- Export conversations to JSON
- Import conversations from JSON
- Toggle between view/edit/rate modes

**Props:**
```typescript
interface ConversationManagementProps {
  conversaciones: ConversacionAI[]
  cargando: boolean
  onRate: (id: number, rating: number, feedback: string) => Promise<void>
  onDelete: (id: number) => Promise<void>
  onEdit: (id: number, pregunta: string, respuesta: string) => Promise<void>
  onExport: () => void
  onImport: (event: React.ChangeEvent<HTMLInputElement>) => Promise<void>
  fileInputRef: React.RefObject<HTMLInputElement>
}
```

### 3. **ConversationForms.tsx** (~350 lines)
**Location:** `frontend/src/components/configuracion/fineTuning/ConversationForms.tsx`

Form component for creating and improving conversations.

**Features:**
- New conversation creation form with question/response fields
- Table and field insertion from database schema
- AI enhancement buttons (improve question, response, or both)
- Dynamic table/field selector with auto-completion
- Textarea focus tracking for intelligent insertion

**Props:**
```typescript
interface ConversationFormsProps {
  tablasYCampos: Record<string, string[]>
  cargandoTablasCampos: boolean
  ultimaActualizacion: string
  onCargarTablasCampos: () => Promise<void>
  onCreate: (pregunta: string, respuesta: string) => Promise<void>
  onMejorarPregunta: (pregunta: string) => Promise<string>
  onMejorarRespuesta: (respuesta: string) => Promise<string>
  onMejorarConversacion: (q: string, r: string) => Promise<{pregunta, respuesta}>
}
```

### 4. **StatisticsPanel.tsx** (~150 lines)
**Location:** `frontend/src/components/configuracion/fineTuning/StatisticsPanel.tsx`

Displays feedback statistics and training readiness indicators.

**Features:**
- Total conversations count
- Rated conversations percentage
- Positive feedback count (rating ≥ 4)
- Negative feedback count (rating ≤ 2)
- Rating distribution chart (1-5 stars)
- Usage guidelines and best practices

**Props:**
```typescript
interface StatisticsPanelProps {
  estadisticasFeedback: any | null
  mostrar: boolean
  onClose: () => void
}
```

### 5. **TrainingWorkflow.tsx** (~400 lines)
**Location:** `frontend/src/components/configuracion/fineTuning/TrainingWorkflow.tsx`

Manages the entire training pipeline from data preparation to job monitoring.

**Sections:**
1. **Data Preparation**
   - Shows conversation readiness status
   - Feedback negative filter toggle
   - "Prepare Data" button
   
2. **Training Form**
   - Base model selector (gpt-4o-2024-08-06 recommended)
   - Start training button
   - Form visibility toggle

3. **Job Management**
   - List of all training jobs with status badges
   - Duration calculation for running/completed jobs
   - Job-specific actions (cancel, delete, activate model)
   - Bulk cleanup operations (delete failed, clean all)
   - Auto-refresh button

**Props:**
```typescript
interface TrainingWorkflowProps {
  jobs: FineTuningJob[]
  cargandoJobs: boolean
  tiempoActual: Date
  conversacionesListasCount: number
  conversacionesDespuesFiltrado: number
  filtrarFeedbackNegativo: boolean
  onCargarJobs: () => Promise<void>
  onPrepararDatos: (ids: number[], soloCalificadas: boolean) => Promise<void>
  onIniciarEntrenamiento: (modeloBase: string) => Promise<void>
  // ... additional handlers
}
```

### 6. **useFineTuning.ts** (~400 lines)
**Location:** `frontend/src/hooks/useFineTuning.ts`

Custom React hook encapsulating all business logic and data fetching.

**State Management:**
- `conversaciones`: List of AI training conversations
- `jobs`: Fine-tuning training jobs
- `estadisticasFeedback`: Feedback statistics
- `tablasYCampos`: Database schema for field insertion
- Loading states for each data type
- Current time for duration calculations

**API Handlers:**

Data Loading:
- `cargarConversaciones(params)`: Fetch conversations with filters
- `cargarJobs()`: Fetch training jobs
- `cargarEstadisticasFeedback()`: Fetch feedback statistics
- `cargarTablasCampos()`: Fetch database schema

CRUD Operations:
- `crearConversacion(pregunta, respuesta)`: Create new conversation
- `actualizarConversacion(id, pregunta, respuesta)`: Update conversation
- `eliminarConversacion(id)`: Delete conversation
- `calificar(id, calificacion, feedback)`: Rate conversation

AI Enhancement:
- `mejorarPregunta(pregunta)`: Improve question with AI
- `mejorarRespuesta(respuesta)`: Improve response with AI
- `mejorarConversacionCompleta(q, r)`: Improve both

Training Operations:
- `prepararDatos(ids, soloCalificadas)`: Prepare training dataset
- `iniciarEntrenamiento(modeloBase, archivoId)`: Start training job
- `activarModelo(modeloId)`: Activate trained model
- `cancelarJob(jobId)`: Cancel running job
- `eliminarJob(jobId)`: Delete job
- `eliminarTodosJobs(soloFallidos)`: Batch delete jobs

Import/Export:
- `exportarConversaciones()`: Export to JSON file
- `importarConversaciones(event)`: Import from JSON file

**Effects:**
- Time update polling (30 seconds)
- Job status polling (10 seconds)

## Data Flow

```
FineTuningTab
    ↓
useFineTuning hook
    ├── State: conversaciones, jobs, estadisticas, etc.
    ├── Handlers: 20+ API-connected functions
    ├── Effects: Polling setup
    └── Return: All state + handlers

FineTuningTab receives data and distributes to sub-components:
    ├── ConversationManagement ← conversaciones, handlers
    ├── ConversationForms ← handlers, tablasYCampos
    ├── StatisticsPanel ← estadisticasFeedback
    └── TrainingWorkflow ← jobs, handlers
```

## Key Features Preserved

✅ Conversation CRUD operations
✅ 1-5 star rating system with feedback
✅ AI enhancement (improve question, response, conversation)
✅ Database table/field insertion
✅ JSON import/export
✅ Feedback statistics display
✅ Data preparation for training
✅ Fine-tuning job management
✅ Job status monitoring
✅ Model activation
✅ Training history

## Type Safety

All components are fully typed with TypeScript:
- Interface definitions for all props
- Type-safe hook return values
- Proper event handler typing
- API response types from services

## Error Handling

- Toast notifications for user feedback
- Try-catch blocks in all async operations
- Error messages passed to UI components
- Graceful degradation for failed operations

## Performance Considerations

- Memoized callbacks in hooks
- Polling setup with cleanup
- Efficient state updates
- Lazy loading of statistics (loaded on demand)
- Component-level error boundaries ready

## Migration Notes

### From Old Structure
The original 2000+ line file has been split while maintaining:
- All imports and dependencies
- All state variables and logic
- All API calls and handlers
- All JSX rendering
- All event listeners
- All useEffect hooks

### Import Changes
If any other files import from `FineTuningTab`:
```typescript
// OLD: Single import
import { FineTuningTab } from '...'

// NEW: Same import works, file exports same component
import { FineTuningTab } from '...'
```

No import changes needed - the component export remains the same!

## Future Improvements

- [ ] Add react-query/SWR for better data fetching
- [ ] Implement conversation filtering/search
- [ ] Add conversation tags/categories
- [ ] Pagination for large conversation lists
- [ ] Advanced analytics dashboard
- [ ] Batch rating operations
- [ ] Conversation templates
- [ ] Model comparison dashboard
- [ ] Training cost estimation
- [ ] Conversation versioning

## Testing

Each component is independently testable:
```typescript
// Example test structure
describe('ConversationManagement', () => {
  it('should display conversation list', () => {...})
  it('should handle edit mode', () => {...})
  it('should rate conversations', () => {...})
})
```

## Dependencies

Core:
- React 18+
- TypeScript 5+

UI Components:
- lucide-react (icons)
- Custom UI components (Card, Button, Input, etc.)

Services:
- `aiTrainingService`: API communication
- `constants/fineTuning`: Constants and utilities

Utilities:
- `sonner`: Toast notifications

---

**Created:** February 18, 2026
**Refactored from:** 2000+ line monolithic component
**Status:** ✅ Complete with full TypeScript support and error handling
