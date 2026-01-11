# 📋 Instrucciones para Verificar Modelos ML

## 🚀 Scripts Disponibles

### Opción 1: Script desde la raíz del proyecto

```bash
python verificar_modelos_ml.py
```

### Opción 2: Script desde el directorio backend

```bash
cd backend
python scripts/verificar_modelos_ml_bd.py
```

### Opción 3: Endpoint API (requiere autenticación)

```bash
GET /api/v1/ai/training/verificar-bd
```

**Nota:** Este endpoint requiere autenticación. Usa el token de sesión en los headers.

## ✅ Qué Verifica el Script

1. **Conexión a Base de Datos**
   - Verifica que DATABASE_URL esté configurado
   - Intenta conectar a la base de datos

2. **Existencia de Tablas**
   - `modelos_riesgo` - Tabla para modelos ML de riesgo crediticio
   - `modelos_impago_cuotas` - Tabla para modelos ML de impago de cuotas

3. **Estructura de Tablas**
   - Verifica que todas las columnas críticas existan
   - Cuenta índices y registros

4. **Servicios ML**
   - Verifica si `scikit-learn` está instalado
   - Verifica si los servicios ML están disponibles

5. **Estado de Migraciones**
   - Muestra la versión actual de Alembic
   - Lista las migraciones requeridas

## 📊 Ejemplo de Salida

```
[INFO] 🔍 Verificando conexión a base de datos y tablas de modelos ML...
[INFO] 📊 Conectando a: tu-base-de-datos

======================================================================
[INFO] 📋 Estado de las tablas de modelos ML:
======================================================================
  ✅ modelos_riesgo                    Modelos de Riesgo ML          EXISTE
  ✅ modelos_impago_cuotas             Modelos de Impago de Cuotas ML EXISTE
======================================================================

----------------------------------------------------------------------
[INFO] 🔍 Verificando estructura de las tablas...
----------------------------------------------------------------------

  📊 modelos_riesgo (Modelos de Riesgo ML):
     - Columnas: 18
     - Índices: 3
     ✅ Todas las columnas críticas existen
     - Registros: 0

  📊 modelos_impago_cuotas (Modelos de Impago de Cuotas ML):
     - Columnas: 18
     - Índices: 3
     ✅ Todas las columnas críticas existen
     - Registros: 0

----------------------------------------------------------------------
[INFO] 🔍 Verificando servicios ML disponibles...
----------------------------------------------------------------------
  ✅ scikit-learn instalado: 1.6.1
  ✅ MLService disponible
  ✅ MLImpagoCuotasService disponible

----------------------------------------------------------------------
[INFO] 🔄 Verificando estado de migraciones Alembic...
----------------------------------------------------------------------
  Versión actual de Alembic: 20251114_05_modelos_impago_cuotas

  Migraciones de modelos ML requeridas:
    - 20251114_04_modelos_riesgo
    - 20251114_05_modelos_impago_cuotas

======================================================================
✅ RESULTADO: Todas las tablas de modelos ML están conectadas a la BD

💡 Próximos pasos:
   1. Verificar que scikit-learn esté instalado (ver arriba)
   2. Probar entrenar un modelo desde la interfaz
   3. Verificar que los endpoints funcionen correctamente
======================================================================
```

## ⚠️ Solución de Problemas

### Error: "No se pudo conectar a la base de datos"

**Causa:** DATABASE_URL no está configurado o es incorrecto.

**Solución:**
1. Verifica que el archivo `.env` exista en `backend/.env`
2. Verifica que `DATABASE_URL` esté configurado correctamente
3. Verifica que la base de datos esté accesible

### Error: "Tabla no existe"

**Causa:** Las migraciones no se han ejecutado.

**Solución:**
```bash
cd backend
alembic upgrade head
```

### Error: "scikit-learn NO está instalado"

**Causa:** La librería scikit-learn no está instalada.

**Solución:**
```bash
pip install scikit-learn==1.6.1
```

### Error de Encoding en Windows

**Causa:** Windows PowerShell no soporta UTF-8 por defecto.

**Solución:** El script ya maneja esto automáticamente. Si aún hay problemas:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

## 📝 Notas

- El script se puede ejecutar desde cualquier directorio
- No requiere autenticación (a diferencia del endpoint API)
- Funciona en Windows, Linux y macOS
- Muestra información detallada sobre el estado de las tablas

