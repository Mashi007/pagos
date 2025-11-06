# 🔧 Corrección: Filtros del Dashboard No Funcionaban

## 🐛 Problema Identificado

Los filtros del dashboard no se aplicaban correctamente porque:

1. **React Query no detectaba cambios en el objeto `filtros`**: Los objetos en JavaScript se comparan por referencia, no por valor. Cuando el objeto `filtros` cambiaba, React Query no detectaba el cambio porque la referencia del objeto podía ser la misma.

2. **QueryKey no serializaba correctamente**: Los `queryKey` usaban directamente el objeto `filtros`, lo que causaba que React Query no invalide el cache cuando los filtros cambiaban.

## ✅ Solución Implementada

### 1. Serialización de QueryKeys
**Antes:**
```typescript
queryKey: ['kpis-principales-menu', filtros]
```

**Después:**
```typescript
queryKey: ['kpis-principales-menu', JSON.stringify(filtros)]
```

**Aplicado a todos los queries:**
- ✅ `kpis-principales-menu`
- ✅ `dashboard-menu`
- ✅ `financiamiento-tendencia`
- ✅ `prestamos-concesionario`
- ✅ `cobranzas-mensuales`
- ✅ `morosidad-analista`
- ✅ `evolucion-morosidad-menu`
- ✅ `evolucion-pagos-menu`

### 2. Logs de Diagnóstico
Se agregaron logs en:
- ✅ `DashboardMenu.tsx` - Cada query muestra los filtros aplicados y parámetros construidos
- ✅ `DashboardFiltrosPanel.tsx` - Cada cambio de filtro muestra el valor anterior y nuevo
- ✅ `useDashboardFiltros.ts` - Muestra los filtros originales y el objeto/params construidos

### 3. Validación de Valores Especiales
Se mejoró `useDashboardFiltros` para ignorar valores especiales:
- ✅ Ignora `__ALL__` en analista, concesionario, modelo
- ✅ Ignora strings vacíos en fechas

### 4. Habilitación Explícita de Queries
Se agregó `enabled: true` explícitamente a todos los queries para asegurar que siempre estén habilitados.

## 📋 Archivos Modificados

1. **`frontend/src/pages/DashboardMenu.tsx`**
   - Cambiado todos los `queryKey` para usar `JSON.stringify(filtros)`
   - Agregado logs de diagnóstico
   - Agregado `enabled: true` a todos los queries

2. **`frontend/src/components/dashboard/DashboardFiltrosPanel.tsx`**
   - Agregado logs cuando cambian los filtros
   - Logs muestran valor anterior y nuevo

3. **`frontend/src/hooks/useDashboardFiltros.ts`**
   - Mejorada validación para ignorar valores especiales
   - Agregado logs de diagnóstico en construcción de parámetros

## 🧪 Cómo Verificar

1. **Abrir la consola del navegador** (F12)
2. **Cambiar un filtro** (ej: seleccionar un analista)
3. **Verificar logs:**
   - `🔍 [Filtro Analista] Cambiando filtro:` - Debe mostrar el cambio
   - `🔧 [useDashboardFiltros] Construyendo objeto de filtros:` - Debe mostrar el objeto construido
   - `🔍 [KPIs Principales] Filtros aplicados:` - Debe mostrar los filtros en el query
   - `🔍 [KPIs Principales] Query string:` - Debe mostrar los parámetros en la URL

4. **Verificar en Network tab:**
   - Las requests deben incluir los parámetros de filtro en la URL
   - Ejemplo: `/api/v1/dashboard/kpis-principales?analista=Juan%20Perez`

## ✅ Resultado Esperado

- ✅ Al cambiar un filtro, React Query debe re-fetchear automáticamente
- ✅ Todos los KPIs y gráficos deben actualizarse con los filtros aplicados
- ✅ Los logs deben mostrar claramente qué filtros se están aplicando
- ✅ Las requests HTTP deben incluir los parámetros de filtro

## 🔍 Debugging

Si los filtros aún no funcionan después de estos cambios:

1. **Verificar en consola:**
   - ¿Aparecen los logs cuando cambias un filtro?
   - ¿Los parámetros construidos son correctos?
   - ¿La query string incluye los filtros?

2. **Verificar en Network tab:**
   - ¿Las requests incluyen los parámetros?
   - ¿El backend recibe los parámetros correctamente?

3. **Verificar React Query DevTools:**
   - ¿Los queries se invalidan cuando cambian los filtros?
   - ¿Los nuevos queries se ejecutan con los filtros correctos?

## 📝 Notas

- Los logs se pueden eliminar después de verificar que todo funciona
- `JSON.stringify` en queryKey es necesario porque React Query compara por referencia
- Los valores especiales (`__ALL__`, strings vacíos) se filtran antes de enviar al backend

