# Análisis de Fallo de Jobs de Fine-Tuning

## 📋 Resumen

Se han identificado 2 jobs de fine-tuning que fallaron:
- `ftjob-DwyHzLGC5l4c3078Ryu9AndT`
- `ftjob-SCFTqQQRf2tU3yiaM2SCRuIM`

## 🔍 Causa del Fallo

Según los emails de OpenAI y el error típico, el fallo más probable es:

**Error: `invalid_n_examples`**
- **Mensaje**: "Training file has 1 example(s), but must have at least 10 examples"
- **Causa**: El archivo de entrenamiento subido a OpenAI contenía menos de 10 conversaciones

## 🕐 Cuándo Ocurrió

Estos jobs fueron creados **antes** de implementar la validación de mínimo 10 conversaciones:
- El job fallido más antiguo: `16/11/2025, 3:31:21 p.m.`
- Los jobs actuales en ejecución: `17/11/2025, 2:23:55 a.m.` y `17/11/2025, 2:24:30 a.m.`

## ✅ Validaciones Implementadas

### 1. Frontend (`FineTuningTab.tsx`)
- ✅ Validación temprana que muestra cuántas conversaciones quedarán después del filtrado
- ✅ Advertencia si después del filtrado quedarían menos de 10 conversaciones
- ✅ Badge visual que muestra el impacto del filtrado de feedback negativo

### 2. Backend - Preparación de Datos (`preparar_datos_entrenamiento`)
- ✅ Validación de mínimo 10 conversaciones **antes** de filtrar feedback negativo
- ✅ Validación de mínimo 10 conversaciones **después** de filtrar feedback negativo
- ✅ Mensaje de error claro indicando cuántas conversaciones se excluyeron

### 3. Backend - Inicio de Job (`iniciar_fine_tuning`)
- ✅ Logging detallado del archivo de entrenamiento antes de iniciar el job
- ✅ Logging del job ID y modelo base cuando se crea exitosamente

### 4. Backend - Manejo de Errores
- ✅ Parseo mejorado de errores de OpenAI (extrae `code`, `message`, `param`)
- ✅ Logging de errores cuando un job falla
- ✅ Formato legible de errores en la UI

## 🔧 Mejoras Técnicas Implementadas

### Parseo de Errores Mejorado

**Antes:**
```python
job.error = str(estado["error"])
# Resultado: "{'code': 'invalid_n_examples', 'message': '...', 'param': '...'}"
```

**Ahora:**
```python
if isinstance(error_data, dict):
    error_msg = error_data.get("message", str(error_data))
    if error_data.get("code"):
        error_msg = f"[{error_data.get('code')}] {error_msg}"
    if error_data.get("param"):
        error_msg += f" (param: {error_data.get('param')})"
    job.error = error_msg
# Resultado: "[invalid_n_examples] Training file has 1 example(s)... (param: training_file)"
```

### Visualización de Errores en Frontend

**Antes:**
- Texto simple en rojo
- Difícil de leer si el error es un objeto JSON

**Ahora:**
- Tarjeta con fondo rojo claro y borde
- Icono de alerta
- Soporte para errores en formato string o JSON
- Texto formateado y legible

## 📊 Prevención de Fallos Futuros

### 1. Validación en Múltiples Capas

```
Frontend (Validación Temprana)
    ↓
Backend - Preparar Datos (Validación Pre-Filtrado)
    ↓
Backend - Preparar Datos (Validación Post-Filtrado)
    ↓
OpenAI (Validación Final)
```

### 2. Feedback Visual al Usuario

- Badge que muestra cuántas conversaciones se excluirán
- Advertencia si después del filtrado quedarían menos de 10
- Confirmación antes de continuar si hay riesgo

### 3. Logging Detallado

- Log del archivo de entrenamiento antes de crear el job
- Log del job ID cuando se crea exitosamente
- Log de errores cuando un job falla

## 🎯 Recomendaciones

### Para Usuarios

1. **Siempre verifica el badge de conversaciones disponibles** antes de preparar datos
2. **Si el filtrado de feedback negativo excluye muchas conversaciones**, considera:
   - Desactivar temporalmente el filtro
   - Calificar más conversaciones con 4+ estrellas
   - Revisar y mejorar el feedback negativo de conversaciones existentes

3. **Espera a tener al menos 12-15 conversaciones calificadas** para tener margen después del filtrado

### Para Desarrolladores

1. **Monitorear logs** cuando se crean jobs de fine-tuning
2. **Revisar errores** en la UI para identificar patrones
3. **Considerar agregar métricas** sobre:
   - Tasa de éxito de jobs
   - Razones más comunes de fallo
   - Tiempo promedio de entrenamiento

## 📝 Notas Adicionales

- Los jobs fallidos **no afectan** los jobs nuevos que se creen con la validación actualizada
- El sistema ahora **previene** la creación de jobs con menos de 10 conversaciones
- Los errores se muestran de forma **más clara y legible** en la UI

## 🔗 Referencias

- [OpenAI Fine-tuning Guide](https://platform.openai.com/docs/guides/fine-tuning)
- [OpenAI Fine-tuning API Reference](https://platform.openai.com/docs/api-reference/fine-tuning)

