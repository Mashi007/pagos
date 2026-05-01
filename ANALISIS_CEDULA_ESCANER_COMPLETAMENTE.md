# Análisis Completo: Extracción de Cédula en Escáner Infopagos

## Estado Actual (Descubierto)

### Backend: ✅ FUNCIONA CORRECTAMENTE

1. **Prompt de Gemini** (`gemini_service.py`):
   - ✅ YA PIDE la `cedula_pagador_en_comprobante` explícitamente
   - ✅ Instruye extraer solo dígitos (sin prefijo V/E/J/G)
   - Línea aprox. 2320 del prompt

2. **Función `extract_infopagos_campos_desde_comprobante`**:
   - ✅ YA RETORNA `cedula_pagador_en_comprobante` correctamente
   - Procesa la respuesta JSON de Gemini sin filtros
   - Línea 2357-2368: extrae y devuelve el valor tal como viene de Gemini

3. **Endpoint `/escaner/extraer-comprobante`** (`cobros/routes.py`):
   - ✅ YA RECIBE `gem.get("cedula_pagador_en_comprobante")`
   - ✅ YA LA INCLUYE en la sugerencia devuelta (línea 3382)
   - Se devuelve en `response.sugerencia.cedula_pagador_en_comprobante`

### Frontend: ❌ NO LA UTILIZA COMPLETAMENTE

En `EscanerInfopagosPage.tsx`:

1. **Recibe correctamente** (línea 507):
   ```typescript
   setCedulaPagadorImg(s.cedula_pagador_en_comprobante || '')
   ```

2. **LA MUESTRA SOLO COMO INFORMACIÓN** (líneas 1242-1249):
   ```typescript
   {cedulaPagadorImg ? (
     <p className="text-xs text-slate-500">
       <span className="font-medium text-slate-700">
         Cédula en comprobante (pagador):
       </span>{' '}
       {cedulaPagadorImg}
     </p>
   ) : null}
   ```

3. **PROBLEMA**: No hay campo de entrada (input) en el formulario para que la cédula del pagador sea **editable** o **visible como valor sugerido**.

## El Requisito Real del Usuario

> "al editar pago en formulario el boton escanar debe escanaer la cedula tambien"
> "Mercantil y BNC si es posible en otros prompt es manual"

**Interpretación**:
- Al hacer clic en "Escanear", la cédula del **pagador** (extractada de la imagen) debe **rellenarse automáticamente** en un campo del formulario
- Esto debe funcionar **específicamente para Mercantil y BNC** (donde aparece frecuentemente)
- Para otros bancos, se acepta entrada manual

**Lo que falta**:
- Un campo de entrada (Input) para `cedula_pagador` en el formulario
- Lógica para pre-rellenarlo con el valor extraído (`cedulaPagadorImg`)
- (Opcional) Mostrar más visibilidad en el formulario

## Solución Necesaria

### 1. **Backend: SIN CAMBIOS NECESARIOS** ✅
La extracción, procesamiento y retorno ya funciona correctamente.

### 2. **Frontend: AGREGAR CAMPO DE ENTRADA**

En `EscanerInfopagosPage.tsx`:

#### a) Agregar estado para cédula editable:
```typescript
const [cedulaPagador, setCedulaPagador] = useState('')
```

#### b) Pre-llenarla al recibir extracción (en `aplicarExtraccionInfopagosAlFormulario`):
```typescript
setCedulaPagador(s.cedula_pagador_en_comprobante || '')
```

#### c) Agregar campo de entrada en el formulario (sección 3. Formulario):
```typescript
<div className="space-y-2 sm:col-span-2">
  <Label htmlFor="cedula-pagador">
    Cédula del pagador (detectada del comprobante)
  </Label>
  <Input
    id="cedula-pagador"
    value={cedulaPagador}
    onChange={e => setCedulaPagador(e.target.value)}
    placeholder="Ej. 12345678 (sin prefijo)"
    maxLength={30}
  />
  {cedulaPagadorImg && cedulaPagadorImg !== cedulaPagador ? (
    <p className="text-xs text-amber-700">
      Sugerencia desde imagen: <span className="font-mono">{cedulaPagadorImg}</span>
      (puede editar si es necesario)
    </p>
  ) : null}
</div>
```

#### d) Limpiar al reiniciar/cambiar cédula del deudor:
```typescript
// En función reiniciar():
setCedulaPagador('')

// En función handleCambiarCedula():
setCedulaPagador('')
```

#### e) (Opcional) Almacenar/enviar con el reporte si es necesario
- Revisar si el backend de `enviarReporteInfopagos` necesita este campo
- Si sí, agregarlo al FormData en `handleGuardar`

## Ventajas de esta Solución

✅ **Simple**: Solo agregar un campo de entrada + llenarla  
✅ **No invasiva**: El flujo actual sigue igual, solo se expone más información  
✅ **Transparente**: El usuario ve la cédula extraída y puede editarla si hace falta  
✅ **Coherente**: Sigue el patrón del resto del formulario (fecha, monto, etc. extraídos pero editables)  

## Nota sobre Mercantil y BNC

El prompt ya tiene instrucciones específicas para estos bancos (líneas con `_extra_prompt_plantilla_escaner`), así que Gemini **debería extraer la cédula** sin cambios adicionales. La visibilidad del campo en el formulario la harán evidente.

