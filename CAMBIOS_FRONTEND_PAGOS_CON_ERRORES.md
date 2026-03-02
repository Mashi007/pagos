# Cambios Frontend: Integración Pagos con Errores

## Archivos a Actualizar

### 1. `src/hooks/useExcelUploadPagos.ts`

#### Agregar estado para pagos_con_errores:
```typescript
// Agregar después de otros useState
const [pagosConErrores, setPagosConErrores] = useState<Array<{
  id: number
  fila_origen: number
  cedula: string
  monto: number
  errores: string[]
  accion: string
}>>([])

const [registrosConError, setRegistrosConError] = useState(0)
```

#### En función `saveAllValid()`, procesar respuesta:
```typescript
// Dentro del try block, después de recibir respuesta:
if (response.pagos_con_errores && response.pagos_con_errores.length > 0) {
  setPagosConErrores(response.pagos_con_errores)
  setRegistrosConError(response.registros_con_error || 0)
  addToast('warning', `${response.registros_con_error} fila(s) con error guardada(s) en revisión`)
}
```

#### Agregar función para mover a revisar_pagos:
```typescript
const moveErrorToReviewPagos = useCallback(
  async (id: number) => {
    try {
      await pagoConErrorService.moveToReviewPagos(id)
      setPagosConErrores(prev => prev.filter(p => p.id !== id))
      addToast('success', 'Movido a Revisar Pagos')
    } catch (error) {
      addToast('error', 'Error al mover a revisar pagos')
    }
  },
  []
)

const dismissError = useCallback(
  (id: number) => {
    setPagosConErrores(prev => prev.filter(p => p.id !== id))
  },
  []
)
```

#### Retornar nuevas variables y funciones:
```typescript
return {
  // ... existentes ...
  pagosConErrores,
  registrosConError,
  moveErrorToReviewPagos,
  dismissError,
}
```

---

### 2. `src/components/pagos/ExcelUploaderPagosUI.tsx`

#### En props del componente, agregar:
```typescript
const {
  // ... existentes ...
  pagosConErrores,
  registrosConError,
  moveErrorToReviewPagos,
  dismissError,
} = useExcelUploadPagos(props)
```

#### Después de la sección de "Guardados", agregar nueva sección:

```typescript
{/* SECCION: PAGOS CON ERRORES */}
{registrosConError > 0 && (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    className="space-y-4"
  >
    <Card className="border-orange-300 bg-orange-50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-5 w-5 text-orange-600" />
            <CardTitle className="text-orange-600">
              Pagos para Revisar ({registrosConError})
            </CardTitle>
          </div>
          <Badge variant="secondary" className="bg-orange-200 text-orange-800">
            ⚠️ Requiere Revision
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {pagosConErrores.map((pago) => (
            <motion.div
              key={pago.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="p-3 bg-white border border-orange-200 rounded-lg flex items-start justify-between hover:shadow-md transition-shadow"
            >
              <div className="flex-1 space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-gray-700">
                    Fila {pago.fila_origen}
                  </span>
                  <span className="text-sm text-gray-600">
                    {pago.cedula} | ${pago.monto.toLocaleString('es-VE')}
                  </span>
                </div>
                <div className="text-sm text-orange-700 flex items-start space-x-2">
                  <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                  <ul className="space-y-0.5">
                    {pago.errores.map((error, idx) => (
                      <li key={idx}>{error}</li>
                    ))}
                  </ul>
                </div>
              </div>
              
              <div className="ml-4 flex items-center space-x-2 flex-shrink-0">
                <Button
                  size="sm"
                  variant="outline"
                  className="text-orange-600 border-orange-200 hover:bg-orange-50"
                  onClick={() => moveErrorToReviewPagos(pago.id)}
                  disabled={isProcessing}
                >
                  <Eye className="h-4 w-4 mr-1" />
                  Revisar
                </Button>
                
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-gray-500 hover:text-red-600 hover:bg-red-50"
                  onClick={() => dismissError(pago.id)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </motion.div>
          ))}
        </div>
        
        <div className="mt-4 pt-4 border-t border-orange-200 flex items-center justify-between">
          <p className="text-sm text-gray-600">
            {registrosConError} fila(s) con error guardada(s) en la tabla de errores
          </p>
          {pagosConErrores.length > 0 && (
            <Button
              size="sm"
              variant="outline"
              className="text-orange-600 border-orange-300 hover:bg-orange-50"
              onClick={() => {
                // Mover todos a revisar
                pagosConErrores.forEach(p => moveErrorToReviewPagos(p.id))
              }}
              disabled={isProcessing}
            >
              Revisar Todos
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  </motion.div>
)}
```

---

### 3. `src/services/pagoConErrorService.ts`

#### Agregar función para mover a revisar_pagos:
```typescript
export const pagoConErrorService = {
  // ... existentes ...
  
  moveToReviewPagos: async (id: number) => {
    const response = await apiClient.post(
      `/pagos_con_errores/${id}/mover-a-revisar`,
      {}
    )
    return response.data
  },

  delete: async (id: number) => {
    const response = await apiClient.delete(`/pagos_con_errores/${id}`)
    return response.data
  },
}
```

---

## Flujo de Datos

```
1. Usuario sube Excel
   ↓
2. Hook: saveAllValid()
   ├─ Envía a backend: /pagos/upload
   ├─ Recibe:
   │  ├─ registros_procesados: 18
   │  ├─ registros_con_error: 2
   │  └─ pagos_con_errores: [{id, cedula, monto, errores}]
   ├─ setPagosConErrores(respuesta.pagos_con_errores)
   └─ setRegistrosConError(respuesta.registros_con_error)
   ↓
3. UI: ExcelUploaderPagosUI
   ├─ Muestra sección "Pagos para Revisar (2)"
   ├─ Lista cada pago con:
   │  ├─ Fila del Excel
   │  ├─ Cédula
   │  ├─ Monto
   │  └─ Errores (lista)
   ├─ Botones para cada fila:
   │  ├─ [Revisar] → moveErrorToReviewPagos(id)
   │  └─ [X] → dismissError(id)
   └─ Botón "Revisar Todos"
   ↓
4. Usuario click [Revisar]
   ├─ POST /pagos_con_errores/{id}/mover-a-revisar
   ├─ Se mueve a tabla 'revisar_pago'
   ├─ Se elimina de lista visual
   └─ Toast: "Movido a Revisar Pagos"
```

---

## Mejoras Visuales

### Colores
- **Guardados**: Verde (✅)
- **Para Revisar**: Naranja (⚠️)
- **Errores**: Rojo (❌)

### Iconos
- `AlertTriangle` para advertencias
- `Eye` para revisar
- `X` para descartar
- `CheckCircle` para éxito

### Animaciones
- Entrada suave de nuevos errores
- Salida suave al revisar/descartar
- Transiciones en hover

---

## Testing

### Casos de Prueba

1. **Excel válido (sin errores)**
   - Sube 20 filas válidas
   - Resultado: "Guardados: 20", sin sección de errores

2. **Excel con 2 errores**
   - Sube 20 filas, 18 OK, 2 con error
   - Resultado: 
     - "Guardados: 18"
     - "Pagos para Revisar: 2"
     - Muestra lista de errores

3. **Revisar uno**
   - Click en [Revisar] para Fila 5
   - Resultado: Se mueve a revisar_pagos, desaparece de lista

4. **Revisar todos**
   - Click en [Revisar Todos]
   - Resultado: Todos los errores se mueven, sección desaparece

5. **Descartar**
   - Click en [X]
   - Resultado: Se elimina de lista (no se guarda en revisar_pagos)

---

## Commits Necesarios

```
- Actualizar useExcelUploadPagos con pagos_con_errores
- Actualizar ExcelUploaderPagosUI con sección de errores
- Actualizar pagoConErrorService con moveToReviewPagos
- Agregar funciones de dismiss y moveError
```
