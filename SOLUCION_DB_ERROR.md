# Solución para Error de Conexión PostgreSQL en Render

## Problema
Error: `could not translate host name "dpg-d318tkuz433a730ouph0-a" to address: Name or service not known`

## Soluciones a Implementar

### 1. Verificar Variables de Entorno en Render

En tu dashboard de Render:

1. Ve a tu servicio PostgreSQL
2. En la pestaña "Info", copia la **External Connection String**
3. En tu servicio web, ve a "Environment"
4. Configura las siguientes variables:

```
DATABASE_URL=postgresql://usuario:contraseña@hostname-externo:5432/dbname
RENDER_DATABASE_URL=postgresql://usuario:contraseña@hostname-externo:5432/dbname
ENVIRONMENT=production
```

### 2. Usar Hostname Externo

El hostname `dpg-d318tkuz433a730ouph0-a` es interno. Necesitas usar el hostname externo que proporciona Render.

**Ejemplo de URL externa:**
```
postgresql://pagos_admin:contraseña@dpg-d318tkuz433a730ouph0-a.oregon-postgres.render.com:5432/pagos_db_zjer
```

### 3. Configurar Timeout y Pool de Conexiones

He actualizado el código para incluir:
- Timeout de conexión más largo
- Pool de conexiones optimizado para Render
- Verificación de conexión antes de usar (`pool_pre_ping=True`)

### 4. Variables de Entorno Recomendadas

```bash
# Base de datos (usa la URL externa completa)
DATABASE_URL=postgresql://usuario:contraseña@hostname.oregon-postgres.render.com:5432/dbname

# Configuración de aplicación
ENVIRONMENT=production
DEBUG=false

# Twilio (opcional)
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_PHONE_NUMBER=tu_numero
```

### 5. Pasos para Solucionar

1. **En Render Dashboard:**
   - Ve a tu base de datos PostgreSQL
   - Copia la "External Connection String"
   - Asegúrate de que incluya el hostname completo (con `.oregon-postgres.render.com` o similar)

2. **En tu servicio web:**
   - Ve a "Environment" 
   - Actualiza `DATABASE_URL` con la URL externa completa
   - Agrega `RENDER_DATABASE_URL` como variable de respaldo

3. **Redeploy:**
   - Haz un nuevo deploy después de actualizar las variables

### 6. Verificar Estado

Después del deploy, revisa los logs para ver:
```
✅ Conexión a base de datos exitosa
✅ Tablas creadas/verificadas exitosamente
```

En lugar de:
```
❌ Error conectando a base de datos
```

## Archivos Actualizados

- `backend/app/db/config.py` - Configuración mejorada de base de datos
- `backend/app/db/init_db.py` - Inicialización con mejor manejo de errores

## Próximos Pasos

1. Actualiza las variables de entorno en Render
2. Usa la URL externa de la base de datos 
3. Redeploy la aplicación
4. Verifica que la conexión sea exitosa en los logs