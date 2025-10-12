# Despliegue en Render.com

## Problemas Actuales y Soluciones

### ❌ Error de Importación (SOLUCIONADO)
**Error:** `ImportError: cannot import name 'TipoAccion' from 'app.models.auditoria'`

**Solución:** Se corrigieron las inconsistencias en el modelo de auditoría:
- Nombres de columnas unificados (`usuario_id`, `tabla`, `registro_id`, `fecha`)
- Relaciones corregidas entre User y Auditoria
- Enum TipoAccion disponible correctamente

### ❌ Error de Conexión a Base de Datos
**Error:** `could not translate host name "dpg-d318tkuz433a730ouph0-a" to address`

**Causa:** La URL de base de datos no es accesible desde el contenedor de Render.

**Soluciones:**

#### 1. Verificar Configuración de PostgreSQL en Render
1. **Dashboard de Render → Tu Servicio PostgreSQL**
2. **Verificar que el servicio PostgreSQL esté activo**
3. **Copiar la URL interna correcta**
4. **Configurar DATABASE_URL en el Web Service**

#### 2. Variables de Entorno Necesarias
Configurar en **Render Dashboard → Web Service → Environment**:

```bash
# CRÍTICO: Esta URL debe venir del servicio PostgreSQL de Render
DATABASE_URL=postgresql://usuario:contraseña@host-interno:5432/nombre_db

# Otras variables importantes
SECRET_KEY=generar-clave-segura-de-32-caracteres
ENVIRONMENT=production
PORT=10000
```

#### 3. Configuración del Build
En **Render Dashboard → Settings**:
- **Build Command:** `cd backend && pip install -r requirements.txt`
- **Start Command:** `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### ✅ Mejoras Implementadas

#### 1. Manejo Robusto de Errores de DB
- La aplicación ya no falla completamente si no puede conectar a la DB
- Inicia en modo de funcionalidad limitada
- Endpoints de health check informativos

#### 2. Health Checks Mejorados
- `/health` - Check básico (sin DB, rápido)
- `/health/full` - Check completo con DB (con cache)
- `/health/ready` - Readiness probe
- `/health/live` - Liveness probe

#### 3. Logging Mejorado
- Información clara sobre el estado de la conexión
- No expone credenciales en logs
- Mensajes informativos para debugging

## Configuración Paso a Paso

### 1. Servicio PostgreSQL
1. Crear PostgreSQL Database en Render
2. Anotar la URL de conexión interna
3. Verificar que esté en la misma región que el Web Service

### 2. Web Service
1. Conectar repositorio Git
2. Configurar build:
   ```
   Build Command: cd backend && pip install -r requirements.txt
   Start Command: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

### 3. Variables de Entorno
Copiar y configurar las variables del archivo `.env.render`:
- `DATABASE_URL` - **CRÍTICO:** Obtener del servicio PostgreSQL
- `SECRET_KEY` - Generar nueva clave segura
- Otras variables según necesidades

### 4. Verificación
1. **Logs de Deploy:** Verificar que no hay errores de importación
2. **Health Check:** `GET https://tu-app.onrender.com/health/full`
3. **Documentación:** `https://tu-app.onrender.com/docs`

## Comandos Útiles para Debug

```bash
# En el shell de Render o localmente
python -c "from app.models.auditoria import TipoAccion; print('OK')"
python -c "from app.core.config import settings; print(settings.get_database_url(hide_password=True))"
```

## Notas Importantes

1. **No subir archivos .env al repositorio**
2. **Configurar todas las variables en el Dashboard de Render**
3. **Usar URLs internas de Render para servicios conectados**
4. **Verificar que los servicios estén en la misma región**
5. **El archivo render.yaml existente puede tener configuración conflictiva**

## Estado Actual

✅ **Errores de importación:** RESUELTOS
✅ **Manejo de errores de DB:** MEJORADO  
🔄 **Conexión a DB:** REQUIERE CONFIGURACIÓN EN RENDER
🔄 **Variables de entorno:** REQUIERE CONFIGURACIÓN EN RENDER
