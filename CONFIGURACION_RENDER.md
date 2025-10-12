# Configuración de Variables de Entorno en Render

## Problema Actual
Tu aplicación usa el hostname interno: `dpg-d318tkuz433a730ouph0-a`
Pero necesita el hostname externo: `dpg-d318tkuz433a730ouph0-a.oregon-postgres.render.com`

## URL Correcta para Render
```
postgresql://pagos_admin:F31OLGHBnP8NBhojFmpA6vCwCngGUzGt@dpg-d318tkuz433a730ouph0-a.oregon-postgres.render.com:5432/pagos_db_zjer
```

## Pasos para Configurar en Render

### 1. En tu Dashboard de Render:

1. **Ve a tu servicio PostgreSQL**
   - Busca "dpg-d318tkuz433a730ouph0"
   - Ve a la pestaña "Info" o "Connect"
   - Copia la **External Connection String** (debería incluir `.oregon-postgres.render.com` o `.ohio-postgres.render.com`)

### 2. En tu servicio Web (FastAPI):

1. **Ve a Environment Variables**
2. **Agrega/actualiza estas variables:**

```bash
# Variable principal de base de datos
DATABASE_URL=postgresql://pagos_admin:F31OLGHBnP8NBhojFmpA6vCwCngGUzGt@dpg-d318tkuz433a730ouph0-a.oregon-postgres.render.com:5432/pagos_db_zjer

# Variables adicionales
ENVIRONMENT=production
DEBUG=false

# Credenciales Twilio (si las necesitas)
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_PHONE_NUMBER=tu_numero_twilio
```

### 3. Importante: Verificar el Hostname Correcto

El hostname puede variar según la región:
- `.oregon-postgres.render.com` (Oregon)
- `.ohio-postgres.render.com` (Ohio)
- `.singapore-postgres.render.com` (Singapore)

**Para verificar el correcto:**
1. En tu base de datos PostgreSQL en Render
2. Ve a "Info" → "External Connection String"
3. Copia el hostname completo que aparece ahí

### 4. Después de Configurar

1. **Guarda las variables de entorno**
2. **Redeploy tu aplicación** (botón "Manual Deploy")
3. **Verifica los logs** - deberías ver:
   ```
   ✅ Conexión a base de datos exitosa
   ✅ Tablas creadas/verificadas exitosamente
   ```

## Solución Automática en el Código

He actualizado `backend/app/db/config.py` para que:
- Convierta automáticamente hostnames internos a externos
- Use la URL externa por defecto
- Maneje mejor los errores de conexión

## Verificar que Funciona

Después del deploy, en los logs deberías ver:
```
🚀 Sistema de Préstamos y Cobranza v1.0.0
🗄️  Base de datos: postgresql://pagos_admin:***@dpg-d318tkuz433a730ouph0-a.oregon-postgres.render.com:5432/pagos_db_zjer
✅ Conexión a base de datos exitosa
✅ Tablas creadas/verificadas exitosamente
🌍 Entorno: production
```

En lugar de:
```
❌ Error conectando a base de datos: could not translate host name
```