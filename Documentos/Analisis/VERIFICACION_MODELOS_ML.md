# Verificación de Modelos ML - Problemas y Soluciones

## 📋 Análisis de Errores

Según los logs HTTP proporcionados:

### 1. **ML Riesgo - Error 500 al Entrenar**
```
XHRPOST /api/v1/ai/training/ml-riesgo/entrenar [HTTP/3 500]
```

**Causa posible:**
- scikit-learn no está instalado o no está disponible
- Error al procesar los datos de entrenamiento
- Error al entrenar el modelo

**Solución aplicada:**
- ✅ Validación temprana de `ML_SERVICE_AVAILABLE` al inicio del endpoint
- ✅ Mensaje de error claro si scikit-learn no está disponible

### 2. **ML Impago - Error 503 al Listar Modelos**
```
XHRGET /api/v1/ai/training/ml-impago/modelos [HTTP/3 503]
```

**Causa posible:**
- La tabla `modelos_impago_cuotas` no existe en la base de datos
- Error de base de datos (tabla no creada)
- scikit-learn no está instalado

**Solución:**
- El código ya maneja este caso y retorna un mensaje claro
- Necesita ejecutar migraciones: `alembic upgrade head`

### 3. **ML Impago - Error 500 al Entrenar**
```
XHRPOST /api/v1/ai/training/ml-impago/entrenar [HTTP/3 500]
```

**Causa posible:**
- scikit-learn no está instalado
- Error al procesar los datos
- Error al entrenar el modelo

## ✅ Cambios Realizados

### 1. Validación Temprana en ML Riesgo

**Antes:**
```python
@router.post("/ml-riesgo/entrenar")
async def entrenar_modelo_riesgo(...):
    try:
        # Procesar datos primero...
        # Validar ML_SERVICE_AVAILABLE después
```

**Después:**
```python
@router.post("/ml-riesgo/entrenar")
async def entrenar_modelo_riesgo(...):
    try:
        # Verificar que MLService esté disponible PRIMERO
        if not ML_SERVICE_AVAILABLE or MLService is None:
            raise HTTPException(
                status_code=503,
                detail="scikit-learn no está instalado. Instala con: pip install scikit-learn",
            )
        # Luego procesar datos...
```

### 2. Eliminación de Validación Duplicada

Se eliminó la validación duplicada de `ML_SERVICE_AVAILABLE` que estaba después de procesar los datos.

## 🔍 Diagnóstico de Problemas

### Verificar si scikit-learn está instalado

En el servidor, ejecutar:
```bash
python -c "import sklearn; print('scikit-learn instalado:', sklearn.__version__)"
```

Si no está instalado:
```bash
pip install scikit-learn==1.6.1
```

### Verificar si las tablas existen

Verificar en la base de datos:
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_name IN ('modelos_riesgo', 'modelos_impago_cuotas');
```

Si no existen, ejecutar migraciones:
```bash
cd backend
alembic upgrade head
```

### Verificar logs del servidor

Los logs del servidor mostrarán el error específico:
- Si es un error de importación: `ImportError: No module named 'sklearn'`
- Si es un error de base de datos: `ProgrammingError: relation "modelos_impago_cuotas" does not exist`
- Si es un error de datos: Mensaje específico del error

## 📊 Estados de los Servicios ML

### ML_SERVICE_AVAILABLE
- **True**: scikit-learn está instalado y disponible
- **False**: scikit-learn no está instalado o no se puede importar

### ML_IMPAGO_SERVICE_AVAILABLE
- **True**: scikit-learn está instalado y MLImpagoCuotasService está disponible
- **False**: scikit-learn no está instalado o no se puede importar

## 🎯 Soluciones Recomendadas

### 1. Instalar Dependencias ML

Si los servicios no están disponibles, instalar:
```bash
pip install scikit-learn==1.6.1
pip install xgboost==2.1.3  # Opcional pero recomendado
```

### 2. Ejecutar Migraciones

Si las tablas no existen:
```bash
cd backend
alembic upgrade head
```

### 3. Verificar Datos de Entrenamiento

Para ML Riesgo:
- Se necesitan al menos 10 préstamos aprobados
- Los préstamos deben tener datos de cliente válidos

Para ML Impago:
- Se necesitan préstamos aprobados con cuotas
- Los préstamos deben tener historial de pagos

## ⚠️ Notas Importantes

1. **scikit-learn es opcional**: El sistema funciona sin ML, pero las funcionalidades de ML no estarán disponibles
2. **Errores 503**: Indican que el servicio no está disponible (scikit-learn no instalado)
3. **Errores 500**: Indican un error en el procesamiento (datos, entrenamiento, etc.)
4. **Errores de base de datos**: Indican que las tablas no existen (ejecutar migraciones)

## 🔄 Próximos Pasos

1. Verificar logs del servidor para el error específico
2. Instalar scikit-learn si no está instalado
3. Ejecutar migraciones si las tablas no existen
4. Verificar que hay suficientes datos para entrenar (mínimo 10 préstamos aprobados)

