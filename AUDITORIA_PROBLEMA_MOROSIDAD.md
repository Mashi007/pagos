# 🔍 AUDITORÍA INTEGRAL: Problema de Morosidad y Cobranzas

## 📋 RESUMEN EJECUTIVO

**Problema Principal**: La línea de "Morosidad Mensual" en el gráfico "MONITOREO FINANCIERO" no se actualiza correctamente y muestra 0 para la mayoría de meses, aunque el backend calcula correctamente los valores.

**Problemas Secundarios**: 
- Gráfico "Cobranzas Mensuales" muestra "No hay datos disponibles"
- Gráfico "Cobranzas Semanales" muestra "No hay datos disponibles"

---

## 🔴 PROBLEMA 1: Morosidad Mensual No Se Actualiza

### ✅ Lo que FUNCIONA:
1. **Backend calcula correctamente**: Los logs muestran que el backend calcula correctamente la morosidad:
   - 10 meses con morosidad > 0
   - Nov 2025: Morosidad=$69,285.22
   - El cálculo sigue la lógica: `morosidad_mensual = MAX(0, programado - pagado)`

2. **Backend devuelve correctamente**: El endpoint `/financiamiento-tendencia-mensual` devuelve:
   ```python
   {
       "morosidad": float(morosidad_acumulada),
       "morosidad_mensual": float(morosidad_mensual),  # ✅ Convertido a float
   }
   ```

3. **Frontend recibe correctamente**: El tipo TypeScript incluye `morosidad_mensual: number`

4. **Gráfico configurado correctamente**: 
   - Usa `dataKey="morosidad_mensual"`
   - Tiene YAxis secundario (`yAxisId="right"`)
   - Tiene color rojo (#ef4444)

### ❌ PROBLEMA IDENTIFICADO:
**El frontend está usando `response.meses` directamente, pero el backend devuelve `{ meses: [...] }`**

**Archivo**: `frontend/src/pages/DashboardMenu.tsx:149-150`
```typescript
const response = await apiClient.get(...) as { meses: Array<...> }
return response.meses  // ✅ CORRECTO - response.data es el objeto JSON
```

**VERIFICACIÓN**: El backend devuelve:
```json
{
  "meses": [
    {
      "mes": "Ene 2024",
      "morosidad_mensual": 0.0,
      ...
    }
  ]
}
```

**CONCLUSIÓN**: El mapeo está correcto. El problema puede ser:
1. **Cache del navegador**: Los datos antiguos están en cache
2. **Escala del gráfico**: Los valores pequeños no se ven por la escala
3. **Renderizado de Recharts**: La línea puede estar renderizándose pero no visible

---

## 🔴 PROBLEMA 2: Cobranzas Mensuales No Carga

### ❌ PROBLEMA CRÍTICO ENCONTRADO:

**Archivo**: `frontend/src/pages/DashboardMenu.tsx:288-302`
```typescript
const response = (await apiClient.get(...)) as {
  data: {
    meses: Array<{...}>
  }
}
return response.data  // ❌ ERROR: response.data es undefined
```

**Backend devuelve** (`dashboard.py:2229`):
```python
return {
    "meses": meses_data,
    "meta_actual": meta_actual,
}
```

**Problema**: `apiClient.get()` en Axios devuelve `{ data: {...} }`, pero el código está usando `response.data` cuando debería usar `response.data` que contiene `{ meses: [...], meta_actual: ... }`.

**Luego en línea 1089**:
```typescript
datosCobranzas && datosCobranzas.length > 0
```

**Error**: `datosCobranzas` es `{ meses: [...], meta_actual: ... }`, no un array. Debería ser:
```typescript
datosCobranzas && datosCobranzas.meses && datosCobranzas.meses.length > 0
```

**Y en línea 1091**:
```typescript
<BarChart data={datosCobranzas}>
```

**Error**: Debería ser:
```typescript
<BarChart data={datosCobranzas.meses}>
```

---

## 🔴 PROBLEMA 3: Cobranzas Semanales No Carga

**Archivo**: `frontend/src/pages/DashboardMenu.tsx:317-323`
```typescript
const response = (await apiClient.get(...)) as {
  data: {
    semanas: Array<{...}>
  }
}
return response.data
```

**Backend devuelve** (`dashboard.py:4091`):
```python
return {
    "semanas": semanas_data,
    "fecha_inicio": fecha_inicio_query.isoformat(),
    "fecha_fin": fecha_fin_query.isoformat(),
}
```

**Frontend usa** (línea 1169):
```typescript
datosCobranzasSemanales && datosCobranzasSemanales.semanas && datosCobranzasSemanales.semanas.length > 0
```

**Frontend usa** (línea 1174):
```typescript
<BarChart data={datosCobranzasSemanales.semanas}>
```

**CONCLUSIÓN**: ✅ Este parece estar correcto, pero necesita verificar que `response.data` contenga la estructura correcta.

---

## 🔧 SOLUCIONES REQUERIDAS

### 1. **Corregir Cobranzas Mensuales** (CRÍTICO)
```typescript
// ANTES (línea 288-302):
const response = (await apiClient.get(...)) as {
  data: { meses: Array<{...}> }
}
return response.data

// DESPUÉS:
const response = await apiClient.get(...)
return response.data as {
  meses: Array<{...}>
  meta_actual: number
}

// Y en línea 1089:
datosCobranzas && datosCobranzas.meses && datosCobranzas.meses.length > 0

// Y en línea 1091:
<BarChart data={datosCobranzas.meses}>
```

### 2. **Verificar Cobranzas Semanales**
```typescript
// Verificar que response.data tenga la estructura correcta
const response = await apiClient.get(...)
return response.data as {
  semanas: Array<{...}>
  fecha_inicio: string
  fecha_fin: string
}
```

### 3. **Mejorar Renderizado de Morosidad Mensual**
- Agregar `domain` al YAxis derecho para asegurar que se muestren valores pequeños
- Agregar `min={0}` para asegurar que empiece en 0
- Verificar que los datos lleguen correctamente con console.log

---

## 📊 VERIFICACIÓN DE DATOS

### Backend Logs (Confirmados):
```
📊 [financiamiento-tendencia] RESUMEN: 10 meses con morosidad > 0
  ✅ Nov 2025: Programado=$130,640.22, Pagado=$61,355.00, Morosidad=$69,285.22
```

### Frontend (A Verificar):
- ¿Los datos llegan al componente?
- ¿El gráfico recibe los datos?
- ¿Hay errores en la consola del navegador?

---

## ✅ CHECKLIST DE CORRECCIONES

- [ ] Corregir mapeo de datos en `cobranzas-mensuales`
- [ ] Corregir uso de `datosCobranzas.meses` en lugar de `datosCobranzas`
- [ ] Verificar estructura de respuesta en `cobranzas-semanales`
- [ ] Agregar logging en frontend para verificar datos recibidos
- [ ] Agregar `domain` al YAxis derecho de morosidad
- [ ] Limpiar cache del navegador después de cambios
- [ ] Reiniciar servidor backend después de cambios

---

## 🎯 PRIORIDADES

1. **ALTA**: Corregir Cobranzas Mensuales (bloquea funcionalidad)
2. **ALTA**: Verificar y corregir Cobranzas Semanales (nueva funcionalidad)
3. **MEDIA**: Mejorar visualización de Morosidad Mensual (funciona pero no se ve bien)
4. **BAJA**: Agregar más logging para debugging futuro

