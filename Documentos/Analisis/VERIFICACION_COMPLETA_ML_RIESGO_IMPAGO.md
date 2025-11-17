# Verificación Completa: ML Riesgo y ML Impago

## 📋 Resumen de Verificación

### ML Riesgo ✅

#### Endpoints Verificados:

1. **GET `/ml-riesgo/modelos`**
   - ✅ Lista modelos de riesgo
   - ✅ Maneja errores de base de datos
   - ⚠️ No valida existencia de tabla (debería ser consistente con ML Impago)

2. **GET `/ml-riesgo/modelo-activo`**
   - ✅ Obtiene modelo activo
   - ✅ Retorna `null` si no hay modelo activo
   - ✅ Maneja errores correctamente

3. **POST `/ml-riesgo/entrenar`**
   - ✅ Valida `ML_SERVICE_AVAILABLE` al inicio
   - ✅ Valida mínimo 10 préstamos aprobados
   - ✅ Procesa datos de entrenamiento
   - ✅ Maneja errores específicos (scikit-learn, stratify, etc.)

4. **POST `/ml-riesgo/activar`**
   - ✅ Valida `ML_SERVICE_AVAILABLE` antes de activar
   - ✅ Desactiva otros modelos
   - ✅ Carga modelo en servicio ML
   - ✅ Maneja errores correctamente

5. **POST `/ml-riesgo/predecir`**
   - ✅ Valida `ML_SERVICE_AVAILABLE`
   - ✅ Verifica que haya modelo activo
   - ✅ Carga modelo y predice
   - ✅ Maneja errores correctamente

### ML Impago ✅

#### Endpoints Verificados:

1. **GET `/ml-impago/modelos`**
   - ✅ Lista modelos de impago
   - ✅ Retorna respuesta vacía con mensaje si tabla no existe
   - ✅ Maneja errores de base de datos correctamente
   - ✅ Permite que frontend funcione aunque tabla no exista

2. **POST `/ml-impago/entrenar`**
   - ✅ Valida `ML_IMPAGO_SERVICE_AVAILABLE` al inicio
   - ✅ Valida existencia de tabla antes de procesar datos
   - ✅ Requiere permisos de administrador
   - ✅ Valida que haya préstamos aprobados
   - ✅ Maneja errores específicos

3. **POST `/ml-impago/activar`**
   - ✅ Requiere permisos de administrador
   - ✅ Desactiva otros modelos
   - ✅ Activa modelo seleccionado
   - ✅ Maneja errores correctamente
   - ⚠️ No valida `ML_IMPAGO_SERVICE_AVAILABLE` (no es necesario para activar)

4. **POST `/ml-impago/predecir`**
   - ✅ Valida `ML_IMPAGO_SERVICE_AVAILABLE`
   - ✅ Verifica que haya modelo activo
   - ✅ Valida que préstamo esté aprobado
   - ✅ Valida que préstamo tenga cuotas
   - ✅ Carga modelo y predice
   - ✅ Maneja errores correctamente

## 🔍 Comparación de Validaciones

### Validación de Servicios Disponibles

| Endpoint | ML Riesgo | ML Impago | Estado |
|----------|-----------|-----------|--------|
| Listar modelos | ❌ No valida | ✅ Maneja tabla no existe | ⚠️ Inconsistente |
| Entrenar | ✅ Valida al inicio | ✅ Valida al inicio | ✅ Correcto |
| Activar | ✅ Valida antes de cargar | ❌ No valida (no necesario) | ✅ Correcto |
| Predecir | ✅ Valida | ✅ Valida | ✅ Correcto |

### Validación de Tabla

| Endpoint | ML Riesgo | ML Impago | Estado |
|----------|-----------|-----------|--------|
| Listar modelos | ❌ No valida | ✅ Retorna vacío con mensaje | ⚠️ Inconsistente |
| Entrenar | ❌ No valida | ✅ Valida antes de procesar | ⚠️ Inconsistente |

## ⚠️ Inconsistencias Encontradas

### 1. Listar Modelos - Validación de Tabla

**ML Riesgo:**
- No valida si la tabla existe
- Si la tabla no existe, retorna error 500 genérico

**ML Impago:**
- Valida si la tabla existe
- Retorna respuesta vacía con mensaje si no existe

**Recomendación:** Hacer consistente ML Riesgo con ML Impago

### 2. Entrenar - Validación de Tabla

**ML Riesgo:**
- No valida si la tabla existe antes de procesar datos
- Puede procesar datos innecesariamente si la tabla no existe

**ML Impago:**
- Valida si la tabla existe antes de procesar datos
- Evita procesamiento innecesario

**Recomendación:** Agregar validación de tabla en ML Riesgo

## ✅ Mejoras Aplicadas

### ML Riesgo
1. ✅ Validación temprana de `ML_SERVICE_AVAILABLE` en entrenar
2. ✅ Validación de `ML_SERVICE_AVAILABLE` en activar
3. ✅ Validación de `ML_SERVICE_AVAILABLE` en predecir
4. ✅ Manejo de errores específicos

### ML Impago
1. ✅ Validación temprana de `ML_IMPAGO_SERVICE_AVAILABLE` en entrenar
2. ✅ Validación de existencia de tabla en entrenar
3. ✅ Retorno de respuesta vacía con mensaje en listar modelos
4. ✅ Manejo de errores específicos
5. ✅ Validación de `ML_IMPAGO_SERVICE_AVAILABLE` en predecir

## 🔧 Recomendaciones

### 1. Hacer Consistente ML Riesgo con ML Impago

**Agregar validación de tabla en ML Riesgo:**

```python
@router.get("/ml-riesgo/modelos")
async def listar_modelos_riesgo(...):
    try:
        try:
            modelos = db.query(ModeloRiesgo).order_by(ModeloRiesgo.entrenado_en.desc()).all()
            return {"modelos": [m.to_dict() for m in modelos]}
        except (ProgrammingError, OperationalError) as db_error:
            error_msg = str(db_error).lower()
            if any(term in error_msg for term in ["does not exist", "no such table", "relation", "table"]):
                return {
                    "modelos": [],
                    "error": "La tabla 'modelos_riesgo' no está creada. Ejecuta las migraciones: alembic upgrade head",
                }
            raise
```

**Agregar validación de tabla en entrenar ML Riesgo:**

```python
@router.post("/ml-riesgo/entrenar")
async def entrenar_modelo_riesgo(...):
    try:
        # Verificar que MLService esté disponible
        if not ML_SERVICE_AVAILABLE or MLService is None:
            raise HTTPException(...)

        # Verificar que la tabla existe
        try:
            db.query(ModeloRiesgo).limit(1).all()
        except (ProgrammingError, OperationalError) as db_error:
            error_msg = str(db_error).lower()
            if any(term in error_msg for term in ["does not exist", "no such table", "relation", "table"]):
                raise HTTPException(
                    status_code=503,
                    detail="La tabla 'modelos_riesgo' no está creada. Ejecuta las migraciones: alembic upgrade head",
                )
            raise

        # Continuar con el procesamiento...
```

### 2. Verificar Migraciones

Asegurarse de que ambas tablas existan:
- `modelos_riesgo`
- `modelos_impago_cuotas`

Ejecutar:
```bash
cd backend
alembic upgrade head
```

### 3. Verificar Instalación de scikit-learn

Ambos modelos requieren scikit-learn:
```bash
pip install scikit-learn==1.6.1
```

## 📊 Estado Final

### ML Riesgo
- ✅ Validación de servicios: Completa
- ⚠️ Validación de tabla: Parcial (solo en algunos endpoints)
- ✅ Manejo de errores: Bueno
- ✅ Mensajes de error: Claros

### ML Impago
- ✅ Validación de servicios: Completa
- ✅ Validación de tabla: Completa
- ✅ Manejo de errores: Excelente
- ✅ Mensajes de error: Muy claros

## 🎯 Conclusión

**ML Impago** está mejor implementado que **ML Riesgo** en términos de:
- Validación de tabla
- Manejo de errores
- Consistencia

**Recomendación:** Aplicar las mismas mejoras de ML Impago a ML Riesgo para mantener consistencia.

