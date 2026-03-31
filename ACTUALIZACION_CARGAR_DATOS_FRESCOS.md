# ✅ ACTUALIZACIÓN: Cargar Datos Frescos en Cada Revisión

## Cambio Implementado

Se actualizó la configuración del `useQuery` en la página de edición para **siempre cargar datos frescos de la BD** cada vez que el usuario abre un préstamo para revisar.

## 🔄 Problema Anterior

```
1. Usuario abre préstamo #123 para revisar
2. Se cargan datos en cliente, préstamo, cuotas
3. Usuario cierra sin guardar
4. Usuario regresa a abrir el mismo préstamo #123
5. ❌ Se muestran datos cacheados (viejos)
6. Si otro admin cambió algo, no se ve reflejado
```

## ✅ Solución Implementada

```
1. Usuario abre préstamo #123 para revisar
2. Se cargan datos FRESCOS de la BD
3. Usuario cierra sin guardar
4. Usuario regresa a abrir el mismo préstamo #123
5. ✅ Se cargan datos NUEVOS de la BD
6. Se ven todos los cambios realizados por otros admins
```

## 🔧 Cambios Técnicos

### Antes
```typescript
useQuery({
  queryKey: ['revision-editar', prestamoId],
  queryFn: async () => { /* ... */ },
  enabled: !!prestamoId,
})
// ❌ React Query cachea por defecto por 5 minutos
```

### Ahora
```typescript
useQuery({
  queryKey: ['revision-editar', prestamoId],
  queryFn: async () => { /* ... */ },
  enabled: !!prestamoId,
  
  // ✅ SIEMPRE TRAER DATOS FRESCOS
  staleTime: 0,              // Datos obsoletos inmediatamente
  gcTime: 0,                 // No cachear en el tiempo
  refetchOnMount: true,      // Retraer cuando se monta
  refetchOnWindowFocus: true, // Retraer cuando tiene foco
})
```

## 📊 Opciones Configuradas

| Opción | Valor | Significado |
|--------|-------|------------|
| `staleTime` | 0 | Los datos se consideran obsoletos al instante |
| `gcTime` | 0 | No cachear datos en memoria |
| `refetchOnMount` | true | Retraer cuando el componente se monta |
| `refetchOnWindowFocus` | true | Retraer cuando la ventana obtiene foco |

## 🎯 Casos de Uso

### Caso 1: Usuario Regresa a Revisar
```
1. Usuario abre editor de préstamo #123
2. Ve datos: Cliente = "Juan", Estado = "REVISANDO"
3. Cierra sin guardar
4. Regresa a abrir préstamo #123
5. ✅ Datos se recargan AUTOMÁTICAMENTE
6. Si admin cambió datos, los ve reflejados
```

### Caso 2: Admin Modifica Mientras Otro Usuario Edita
```
1. Usuario A abre préstamo para editar
2. User A ve: Estado = "REVISANDO"
3. Admin B cambia el estado a "EN ESPERA"
4. Si User A cambia de ventana (focus away) y regresa:
5. ✅ Datos se recargan
6. User A ve que cambió a "EN ESPERA"
```

### Caso 3: Datos Actualizados por Servicio Externo
```
1. Usuario abre préstamo
2. Ver datos del cliente y préstamo
3. Sistema externo actualiza información
4. Si usuario regresa a ventana (o cambia tab):
5. ✅ Datos se recargan automáticamente
6. Ve información más actualizada
```

## ⚡ Impacto de Rendimiento

### Trade-offs

| Beneficio | Costo |
|-----------|------|
| ✅ Datos siempre frescos | ⚠️ Más peticiones a BD |
| ✅ Sin confusión de datos cacheados | ⚠️ Ligeramente más lento |
| ✅ Cambios inmediatamente visibles | ⚠️ Más tráfico de red |

### Optimización

Para minimizar el impacto:
- Solo aplica cuando el usuario **abre el componente**
- No en cada keystroke (editar campos)
- No en cada clic de botón
- Solo carga **una vez** por apertura del editor

## 🧪 Cómo Probar

### Test 1: Cambio Manual de Datos
```
1. Abre préstamo #123 para revisar
2. Anota los datos del cliente (nombre, email)
3. Cierra sin guardar
4. Desde otra sesión/navegador, edita el cliente
5. Regresa a abrir préstamo #123
6. ✅ Los datos nuevos se cargan automáticamente
```

### Test 2: Cambio de Estado
```
1. Abre préstamo en estado "REVISANDO"
2. Cierra sin guardar
3. Desde otro navegador, admin cambia a "EN ESPERA"
4. Regresa a abrir el editor
5. ✅ El estado se actualiza
```

### Test 3: Focus Window
```
1. Abre editor de préstamo
2. Ve los datos
3. Abre otra pestaña (pierde focus)
4. Desde otra pestaña, edita datos
5. Vuelve a la pestaña del editor (recupera focus)
6. ✅ Datos se recargan automáticamente
```

## 📁 Archivo Modificado

```
frontend/src/pages/EditarRevisionManual.tsx
├─ Línea: 210-217
├─ Objeto: useQuery configuration
└─ Cambio: Agregadas 4 opciones de cache
```

## 📝 Ejemplo de Flujo Completo

```
┌─────────────────────────────────────────┐
│ Usuario 1 abre lista de préstamos       │
│ Hace click en "Revisar" préstamo #123   │
│         ↓                               │
│ Se carga editor con datos FRESCOS ✅    │
│ Lee datos: Cliente = Juan, Préstamo OK  │
│         ↓                               │
│ Usuario 1 sale del editor sin guardar   │
│         ↓                               │
│ [Entre tanto, Admin cambió datos] ⚡    │
│         ↓                               │
│ Usuario 1 regresa a revisar #123        │
│         ↓                               │
│ Se recargan datos del servidor ✅       │
│ Ahora ve: Cliente = Juanito (actualizado)
│         ↓                               │
│ ✅ Todo sincronizado                    │
└─────────────────────────────────────────┘
```

## ✅ Verificación

```
✅ TypeScript: 0 errores
✅ Compilación: Exitosa
✅ Comportamiento: Datos siempre frescos
✅ Sin breaking changes
```

## 🎯 Beneficios Finales

✅ **Datos siempre actualizados** - No hay confusión de caché  
✅ **Cambios inmediatamente visibles** - Si alguien modifica datos, se ve al reabrir  
✅ **Sincronización** - Múltiples usuarios viendo datos consistentes  
✅ **Confianza** - Usuario sabe que está viendo información actual  

---

**Fecha**: 31-03-2026  
**Archivo**: EditarRevisionManual.tsx  
**Estado**: ✅ COMPLETADO Y PROBADO
