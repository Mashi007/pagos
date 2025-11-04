# Guía de Migración: Eliminar uso de `any`

## 📋 Estrategia de Migración

### Fase 1: Tipos Base (✅ Completado)
- ✅ `frontend/src/types/errors.ts` - Tipos para errores
- ✅ `frontend/src/types/recharts.ts` - Tipos para Recharts
- ✅ `frontend/src/types/common.ts` - Tipos comunes

### Fase 2: Correcciones Manuales Críticas
1. **Bloques catch** - Cambiar `catch (error: any)` → `catch (error: unknown)`
2. **Props de componentes** - Definir interfaces específicas
3. **Type assertions** - Reemplazar `as any` con tipos específicos
4. **Retornos de funciones** - Definir tipos de retorno explícitos

### Fase 3: Automatización
- Script para buscar y reemplazar patrones comunes
- Linter rules más estrictas

## 🔧 Patrones Comunes a Corregir

### 1. Bloques Catch
```typescript
// ❌ ANTES
catch (error: any) {
  console.error(error.message)
}

// ✅ DESPUÉS
import { getErrorMessage } from '@/types/errors'
catch (error: unknown) {
  console.error(getErrorMessage(error))
}
```

### 2. Props de Componentes
```typescript
// ❌ ANTES
const CustomTooltip = ({ active, payload, label }: any) => {

// ✅ DESPUÉS
import { CustomTooltipProps } from '@/types/recharts'
const CustomTooltip = ({ active, payload, label }: CustomTooltipProps) => {
```

### 3. Formatters de Recharts
```typescript
// ❌ ANTES
formatter={(value: number, name: string, props: any) => ...}

// ✅ DESPUÉS
formatter={(value: number, name: string, props: { payload?: Record<string, unknown> }) => ...}
```

### 4. Type Assertions
```typescript
// ❌ ANTES
const data = response.data as any

// ✅ DESPUÉS
interface ApiResponse {
  data: MyType
}
const data = response.data as ApiResponse['data']
```

## 📊 Progreso

- Total instancias: ~326
- Corregidas: ~10
- Pendientes: ~316

## 🎯 Prioridades

1. **Alta**: Servicios API (`api.ts`, `*Service.ts`)
2. **Alta**: Componentes de formularios
3. **Media**: Componentes de dashboard/modals
4. **Baja**: Utilities y helpers

