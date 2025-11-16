# Verificación de Conexión a BD - Modelos ML

## 📋 Resumen de Verificación

### Estado de Conexión

Los modelos ML están **conectados a la base de datos** a través de SQLAlchemy ORM:

1. **Modelo SQLAlchemy**: `ModeloRiesgo` y `ModeloImpagoCuotas` heredan de `Base`
2. **Tablas en BD**: `modelos_riesgo` y `modelos_impago_cuotas`
3. **Migraciones**: Existen migraciones para crear ambas tablas
4. **Imports**: Ambos modelos están importados en `app/models/__init__.py`

## ✅ Verificaciones Realizadas

### 1. Modelos SQLAlchemy

**ModeloRiesgo:**
- ✅ Definido en `backend/app/models/modelo_riesgo.py`
- ✅ Tabla: `modelos_riesgo`
- ✅ Hereda de `Base` (SQLAlchemy)
- ✅ Importado en `app/models/__init__.py`

**ModeloImpagoCuotas:**
- ✅ Definido en `backend/app/models/modelo_impago_cuotas.py`
- ✅ Tabla: `modelos_impago_cuotas`
- ✅ Hereda de `Base` (SQLAlchemy)
- ✅ Importado en `app/models/__init__.py` (corregido)

### 2. Migraciones

**ML Riesgo:**
- ✅ Migración: `20251114_04_create_modelos_riesgo.py`
- ✅ Crea tabla `modelos_riesgo` con todas las columnas necesarias
- ✅ Crea índices necesarios

**ML Impago:**
- ✅ Migración: `20251114_05_create_modelos_impago_cuotas.py`
- ✅ Crea tabla `modelos_impago_cuotas` con todas las columnas necesarias
- ✅ Crea índices necesarios

### 3. Endpoints de Verificación

**Nuevo Endpoint: `/api/v1/ai/training/verificar-bd`**
- ✅ Verifica existencia de ambas tablas
- ✅ Muestra estructura de columnas e índices
- ✅ Cuenta registros en cada tabla
- ✅ Verifica disponibilidad de servicios ML (scikit-learn)

### 4. Validaciones en Endpoints

**ML Riesgo:**
- ✅ Valida existencia de tabla antes de entrenar
- ✅ Retorna respuesta vacía con mensaje si tabla no existe
- ✅ Valida `ML_SERVICE_AVAILABLE` antes de usar servicios ML

**ML Impago:**
- ✅ Valida existencia de tabla antes de entrenar
- ✅ Retorna respuesta vacía con mensaje si tabla no existe
- ✅ Valida `ML_IMPAGO_SERVICE_AVAILABLE` antes de usar servicios ML

## 🔍 Cómo Verificar la Conexión

### Opción 1: Usar el Endpoint de Verificación

```bash
GET /api/v1/ai/training/verificar-bd
```

**Respuesta esperada:**
```json
{
  "conexion_bd": true,
  "todas_existen": true,
  "servicios_ml": {
    "scikit_learn_disponible": true,
    "ml_impago_disponible": true
  },
  "tablas": {
    "modelos_riesgo": {
      "existe": true,
      "nombre": "Modelos de Riesgo ML",
      "columnas": [...],
      "indices": [...],
      "total_registros": 0
    },
    "modelos_impago_cuotas": {
      "existe": true,
      "nombre": "Modelos de Impago de Cuotas ML",
      "columnas": [...],
      "indices": [...],
      "total_registros": 0
    }
  }
}
```

### Opción 2: Usar el Script de Verificación

```bash
cd backend
python scripts/verificar_modelos_ml_bd.py
```

### Opción 3: Verificar en la Base de Datos Directamente

```sql
-- Verificar si las tablas existen
SELECT table_name 
FROM information_schema.tables 
WHERE table_name IN ('modelos_riesgo', 'modelos_impago_cuotas');

-- Verificar estructura de modelos_riesgo
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'modelos_riesgo';

-- Verificar estructura de modelos_impago_cuotas
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'modelos_impago_cuotas';
```

## ⚠️ Problemas Comunes

### 1. Tablas No Existen

**Síntoma:**
- Error 503 al listar modelos
- Mensaje: "La tabla 'modelos_riesgo' no está creada"

**Solución:**
```bash
cd backend
alembic upgrade head
```

### 2. Modelo No Importado

**Síntoma:**
- Error al importar `ModeloImpagoCuotas`
- Alembic no detecta el modelo

**Solución:**
- ✅ Ya corregido: `ModeloImpagoCuotas` está importado en `app/models/__init__.py`

### 3. scikit-learn No Instalado

**Síntoma:**
- Error 503 al entrenar modelos
- Mensaje: "scikit-learn no está instalado"

**Solución:**
```bash
pip install scikit-learn==1.6.1
```

## 📊 Estado Actual

### Conexión a BD
- ✅ **ModeloRiesgo**: Conectado correctamente
- ✅ **ModeloImpagoCuotas**: Conectado correctamente (import agregado)

### Tablas en BD
- ⚠️ **modelos_riesgo**: Depende de migraciones
- ⚠️ **modelos_impago_cuotas**: Depende de migraciones

### Servicios ML
- ⚠️ **scikit-learn**: Depende de instalación
- ⚠️ **ML Services**: Dependen de scikit-learn

## 🎯 Conclusión

**Los modelos ML están correctamente configurados para conectarse a la BD**, pero:

1. **Las tablas deben existir**: Ejecutar `alembic upgrade head` si no existen
2. **scikit-learn debe estar instalado**: Para que los servicios ML funcionen
3. **Los endpoints manejan errores**: Retornan mensajes claros si hay problemas

**Para verificar el estado completo:**
- Usar el endpoint `/api/v1/ai/training/verificar-bd`
- O ejecutar el script `verificar_modelos_ml_bd.py`

