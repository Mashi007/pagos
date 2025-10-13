# 🔍 Guía de Verificación Backend-Frontend

## 📋 Verificación Manual Paso a Paso

### 1. **Verificar Backend (API)**

#### A. Health Check
```bash
# Abrir en navegador o usar curl
https://pagos-f2qf.onrender.com/api/v1/health
```
**Resultado esperado:** Status 200 con información del sistema

#### B. Documentación API
```bash
# Abrir en navegador
https://pagos-f2qf.onrender.com/docs
```
**Resultado esperado:** Interfaz Swagger/OpenAPI funcionando

#### C. Endpoint raíz
```bash
# Abrir en navegador
https://pagos-f2qf.onrender.com/
```
**Resultado esperado:** Status 200 (puede ser un mensaje de bienvenida)

### 2. **Verificar Frontend**

#### A. Acceso al sitio
```bash
# Abrir en navegador (ajustar URL según tu despliegue)
https://tu-frontend-url.onrender.com
```
**Resultado esperado:** Página principal cargando correctamente

#### B. Consola del navegador
1. Abrir DevTools (F12)
2. Ir a la pestaña "Console"
3. Buscar errores relacionados con:
   - CORS
   - Failed to fetch
   - Network errors
   - 404/500 errors

### 3. **Verificar Comunicación API**

#### A. Probar autenticación
```bash
# POST request a login
curl -X POST https://pagos-f2qf.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

#### B. Probar endpoints protegidos
```bash
# GET request con token (reemplazar TOKEN)
curl -X GET https://pagos-f2qf.onrender.com/api/v1/clientes \
  -H "Authorization: Bearer TOKEN"
```

### 4. **Verificar CORS**

#### A. Preflight request
```bash
# OPTIONS request
curl -X OPTIONS https://pagos-f2qf.onrender.com/api/v1/clientes \
  -H "Origin: https://tu-frontend-url.onrender.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization"
```

**Resultado esperado:** Headers CORS en la respuesta

### 5. **Verificar Base de Datos**

#### A. Endpoint que requiere BD
```bash
# GET request a clientes
curl -X GET https://pagos-f2qf.onrender.com/api/v1/clientes?page=1&per_page=1
```

**Resultado esperado:** 
- Status 401 (sin autenticación) = BD conectada
- Status 200 (con datos) = BD funcionando perfectamente
- Status 503 = Error de BD

## 🛠️ Herramientas de Verificación

### 1. **Postman**
- Importar colección de la API
- Probar todos los endpoints
- Verificar respuestas y códigos de estado

### 2. **Browser DevTools**
- Network tab: Ver todas las requests
- Console tab: Ver errores JavaScript
- Application tab: Verificar tokens y storage

### 3. **Script Automatizado**
```bash
# Ejecutar el script de verificación
python verificar_conexion.py
```

## 🚨 Problemas Comunes y Soluciones

### 1. **Error CORS**
**Síntomas:** 
- "Access to fetch at '...' has been blocked by CORS policy"
- Requests fallan en el navegador pero funcionan en Postman

**Solución:**
- Verificar configuración CORS en el backend
- Asegurar que el frontend URL esté en la lista de origins permitidos

### 2. **Error 503 Service Unavailable**
**Síntomas:**
- Backend responde con 503
- Logs muestran errores de base de datos

**Solución:**
- Verificar conexión a PostgreSQL
- Revisar variables de entorno de la BD
- Verificar que las migraciones estén aplicadas

### 3. **Error 401 Unauthorized**
**Síntomas:**
- Endpoints protegidos devuelven 401
- Login no funciona

**Solución:**
- Verificar configuración de JWT
- Revisar secret key
- Verificar que el usuario admin exista

### 4. **Error de Red**
**Síntomas:**
- "Failed to fetch"
- Timeout errors

**Solución:**
- Verificar URLs del frontend y backend
- Comprobar conectividad de red
- Verificar que los servicios estén activos

## 📊 Checklist de Verificación

- [ ] Backend responde en `/api/v1/health`
- [ ] Documentación API accesible en `/docs`
- [ ] Frontend carga correctamente
- [ ] No hay errores CORS en la consola
- [ ] Login funciona correctamente
- [ ] Endpoints protegidos requieren autenticación
- [ ] Base de datos conectada (no errores 503)
- [ ] Requests del frontend llegan al backend
- [ ] Respuestas del backend llegan al frontend
- [ ] Datos se muestran correctamente en la UI

## 🎯 Pruebas Específicas del Sistema

### 1. **Flujo de Login**
1. Ir al frontend
2. Intentar hacer login
3. Verificar que el token se guarde
4. Verificar redirección después del login

### 2. **Flujo de Clientes**
1. Navegar a la sección de clientes
2. Verificar que se carguen los datos
3. Probar filtros y búsqueda
4. Verificar paginación

### 3. **Flujo de Carga Masiva**
1. Ir a carga masiva
2. Descargar template
3. Subir archivo de prueba
4. Verificar procesamiento

### 4. **Flujo de Dashboard**
1. Acceder al dashboard
2. Verificar que se muestren KPIs
3. Verificar gráficos y estadísticas
4. Probar filtros de fecha

## 📞 Contacto y Soporte

Si encuentras problemas:
1. Revisar logs del backend en Render
2. Revisar logs del frontend en Render
3. Verificar configuración de variables de entorno
4. Comprobar estado de los servicios en Render Dashboard
