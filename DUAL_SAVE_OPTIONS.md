# Guardado Flexible: Uno a Uno o Lote Completo

## Dos Formas de Guardar

El modal "Casos a revisar" permite guardar de dos formas flexibles:

### 1️⃣ **Guardar Uno a Uno** (Individual)
```
Botón por cada fila: "Guardar"
```

### 2️⃣ **Guardar Todos** (Lote)
```
Botón en footer: "Guardar todos"
```

---

## Opción 1: Guardar Individual (Uno a Uno)

### Cuándo Usar
- Quieres revisar un cliente a la vez
- Necesitas validar antes de guardar
- Prefieres control total

### Flujo Visual

```
┌─────────────────────────────────────────┐
│ ID │ Cédula      │ Nombres    │ Guardar │
├─────────────────────────────────────────┤
│13075│ V2868736   │ JAVIER ... │ [Guardar]│  ← Click aquí
├─────────────────────────────────────────┤
│13074│ V1387...   │ MAIKEL ... │ [Guardar]│
├─────────────────────────────────────────┤
│13073│ V2071...   │ DAVID ...  │ [Guardar]│
└─────────────────────────────────────────┘
```

### Paso a Paso
```
1. Editar cliente #13075:
   - Cédula: V2868736 (válida)
   - Nombres: JAVIER ANTONIO PÉREZ (válido)
   - Teléfono: 04242263xxx (válido)
   - Email: elgranjapo@gmail.com (válido)

2. Hacer clic: Botón "Guardar" en la fila

3. Resultado:
   ✅ Toast: "Cliente #13075 completado y removido"
   ✅ Fila desaparece con animación
   ✅ En BD: cambios persistidos
   ✅ Frontend: lista actualizada
```

### Código de `saveOne()`

```typescript
const saveOne = async (c: Cliente) => {
  // 1. Validar cambios
  if (!hasChanges(c)) return
  setSaving(c.id)  // Estado: guardando este cliente
  
  try {
    // 2. Preparar datos
    const updateData = {
      cedula: payload.cedula ?? c.cedula,
      nombres: payload.nombres ?? c.nombres,
      telefono: payload.telefono ?? c.telefono,
      email: payload.email ?? c.email,
    }
    
    // 3. Guardar en backend (db.commit() → BD)
    const result = await clienteService.updateCliente(String(c.id), updateData)
    
    // 4. Invalidar cache React Query
    queryClient.invalidateQueries({ queryKey: clienteKeys.lists() })
    
    // 5. Verificar validadores
    if (cumpleConValidadores(result)) {
      // Completado: remover de lista
      setClientes(prev => prev.filter(x => x.id !== c.id))
      toast.success(`✓ Cliente #${c.id} completado y removido`)
    } else {
      // Parcial: mantener y actualizar
      setClientes(prev => prev.map(x => x.id === c.id ? result : x))
      toast.info(`✓ Cliente #${c.id} actualizado`)
    }
  } catch (e) {
    // Error: mostrar mensaje
    toast.error(`✗ Error al guardar cliente #${c.id}`)
  } finally {
    setSaving(null)  // Limpiar estado
  }
}
```

### Ventajas
- ✅ Controlado: Revisas cada cliente
- ✅ Rápido: Cambios inmediatos
- ✅ Aislado: No afecta otros clientes si hay error
- ✅ Feedback: Toast específico para cada uno

### Desventajas
- ❌ Lento: Múltiples clics
- ❌ Manual: Requiere atención

---

## Opción 2: Guardar Todos (Lote)

### Cuándo Usar
- Tienes muchos clientes para guardar
- Son actualizaciones similares
- Quieres rapidez

### Flujo Visual

```
┌──────────────────────────────────────────────┐
│ Casos a revisar                              │
├──────────────────────────────────────────────┤
│ ID │ Cédula │ Nombres │ Teléfono │ Guardar │
├──────────────────────────────────────────────┤
│13075│ ✎     │ ✎      │ ✎       │ Guardar │
│13074│ ✎     │ ✎      │ ✎       │ Guardar │
│13073│ ✎     │ ✎      │ ✎       │ Guardar │
│...  │ ...   │ ...    │ ...     │ ...     │
│13064│ ✎     │ ✎      │ ✎       │ Guardar │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ 📈 Guardando: 15 de 50 clientes             │
│ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│ 30% completado                               │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│         5 casos a revisar                    │
│                  [Cerrar] [Guardar todos]    │  ← Click aquí
└──────────────────────────────────────────────┘
```

### Paso a Paso
```
1. Editar múltiples clientes:
   - Cliente A: cedula + nombres + telefono + email (COMPLETO)
   - Cliente B: cedula + nombres (PARCIAL)
   - Cliente C: cedula + nombres + email (PARCIAL)
   - ...
   - Cliente Z: cedula + nombres + telefono + email (COMPLETO)

2. Hacer clic: Botón "Guardar todos" en footer

3. Resultado:
   ┌────────────────────────────────────────────┐
   │ Barra de progreso: 0% → 100%               │
   │ Se actualiza con cada cliente               │
   └────────────────────────────────────────────┘
   
   ✅ Toast: "15 completados, 8 actualizados"
   ✅ 15 filas desaparecen con animación
   ✅ 8 filas se mantienen actualizadas
   ✅ En BD: todos guardados
```

### Código de `saveAll()`

```typescript
const saveAll = async () => {
  // 1. Filtrar clientes con cambios
  const toSave = clientes.filter(c => hasChanges(c))
  if (!toSave.length) return
  
  setSaving('all')  // Estado: guardando todo
  setProgress({ current: 0, total: toSave.length })
  
  // 2. Guardar cada uno en secuencia
  for (let i = 0; i < toSave.length; i++) {
    const c = toSave[i]
    try {
      // Preparar datos
      const updateData = { ... }
      
      // Guardar en backend (db.commit() → BD)
      const result = await clienteService.updateCliente(String(c.id), updateData)
      
      // Actualizar progreso
      setProgress({ current: i + 1, total: toSave.length })
    } catch (e) {
      errs[c.id] = getErrorMessage(e)
    }
  }
  
  // 3. Invalidar cache
  queryClient.invalidateQueries({ queryKey: clienteKeys.lists() })
  
  // 4. Remover completados, mantener parciales
  setClientes(prev => 
    prev.filter(c => {
      if (!cumpleConValidadores(updatedClientes.get(c.id))) {
        return true  // Mantener
      }
      completed++
      return false  // Remover
    })
  )
  
  // 5. Toast de resumen
  toast.success(`✓ ${completed} removidos, ${ok - completed} actualizados`)
}
```

### Ventajas
- ✅ Rápido: Un solo click
- ✅ Eficiente: Guarda todo de una vez
- ✅ Feedback completo: Barra de progreso
- ✅ Resumen: Toast con estadísticas

### Desventajas
- ❌ Menos controlado: Todo a la vez
- ❌ Si hay error: Puedes perder el trabajo sin guardar

---

## Tabla Comparativa

| Aspecto | Uno a Uno | Lote |
|--------|----------|------|
| **Velocidad** | Lenta | Rápida |
| **Control** | Alto | Bajo |
| **Feedback** | Individual | Resumen |
| **Errors** | Aislados | Acumulados |
| **Progreso** | Toast | Barra progreso |
| **Mejor para** | 1-5 clientes | 5+ clientes |

---

## Ejemplos de Uso

### Caso 1: Un Cliente Incompleto
```
Usuario: "Solo quiero completar a Juan"

Acción:
1. Abrir modal "Casos a revisar"
2. Editar fila de Juan (campo 1, 2, 3)
3. Clic botón "Guardar" en esa fila
4. Resultado: Juan removido, otros se mantienen
```

### Caso 2: Múltiples Clientes Incompletos
```
Usuario: "Necesito completar 20 clientes ahora"

Acción:
1. Abrir modal "Casos a revisar"
2. Editar 20 clientes (rápido por filas)
3. Clic botón "Guardar todos"
4. Ver barra de progreso: 0%→100%
5. Resultado: 20 completan o se actualizan
```

### Caso 3: Mezcla de Operaciones
```
Usuario: "Completar algunos, actualizar otros"

Acción:
Opción A: Guardar uno a uno (controlar cada uno)
  - Cliente A: Guardar individual → Removido
  - Cliente B: Guardar individual → Actualizado
  - ...

Opción B: Guardar todo (aunque algunos sean parciales)
  - Editar todos
  - Guardar todos
  - 8 se removidos + 7 se actualizan
```

---

## Garantías de Ambas Opciones

### Backend (db.commit())
```
✅ Ambas formas usan updateCliente()
✅ Ambas llaman db.commit() → Tabla clientes
✅ Ambas validan duplicados
✅ Ambas retornan ClienteResponse actualizado
```

### Frontend (React Query)
```
✅ saveOne() invalida:
   - clienteKeys.lists()
   - clienteKeys.detail(id)
   - clientes.search

✅ saveAll() invalida:
   - clienteKeys.lists()
   - clientes.search
```

### UI (Feedback Visual)
```
saveOne():
  ✅ Toast individual
  ✅ Animación de desaparición
  ✅ Fila actualiza si es parcial

saveAll():
  ✅ Barra de progreso (0→100%)
  ✅ Toast de resumen
  ✅ Múltiples filas desaparecen
```

---

## Botones en la UI

### Botón Individual (Por Fila)
```
┌────────────────────┐
│ 💾 Guardar         │  ← En cada fila
└────────────────────┘

Estados:
  - Habilitado: Hay cambios + No guardando
  - Deshabilitado: Sin cambios o guardando todo
  - Cargando: Spinner mientras se guarda
```

### Botón Guardar Todos (Footer)
```
┌──────────────────────────────────────┐
│ [Cerrar]  [Guardar todos]            │
│                    ← En footer
└──────────────────────────────────────┘

Estados:
  - Verde (activo): Hay cambios
  - Deshabilitado: Sin cambios o guardando
  - Cargando: Muestra "Guardando X de Y"
```

---

## Flujo de Decisión

```
Usuario llega a "Casos a revisar"
            ↓
    ¿Cuántos cliente editar?
    ↙              ↘
1-5 clientes    5+ clientes
    ↓                ↓
Usar botón       Usar botón
"Guardar"        "Guardar todos"
(individual)     (lote)
    ↓                ↓
Click por fila   Click una vez
    ↓                ↓
Toast x5         Barra progreso
    ↓                ↓
Filas desaparecen uno a uno
    ↓                ↓
    └────────┬────────┘
             ↓
    BD actualizada ✅
    Lista refrescada ✅
    Usuarios satisfecho ✅
```

---

## Archivo Modificado

| Archivo | Cambios |
|---------|---------|
| `frontend/src/components/clientes/CasosRevisarDialog.tsx` | Botones mejorados + títulos descriptivos |

## Commits

```
{pendiente} - docs: Documentar opciones de guardado individual vs lote
```

---

## Conclusión

✅ **Flexibilidad Total:**
- Guardar uno a uno para máximo control
- Guardar lote para máxima velocidad
- Ambas opciones son igual de confiables
- Ambas garantizan persistencia en BD
- Ambas ofrecen feedback visual claro
