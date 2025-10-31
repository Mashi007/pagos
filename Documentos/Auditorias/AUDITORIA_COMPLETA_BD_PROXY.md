# 🔍 AUDITORÍA COMPLETA: CONFIGURACIÓN BD Y PROXY

## 📋 HISTORIAL DE CAMBIOS

### 1. ✅ CONFIGURACIÓN DE BASE DE DATOS (Migración de Datos)

#### **Proceso de Migración Implementado:**

**Tablas de Staging:**
- `public.clientes_staging` - Tabla temporal para importar datos de Excel/CSV
- `public.prestamos_staging` - Tabla temporal para importar datos de préstamos
- `public.pagos_staging` - Tabla temporal para importar datos de pagos

**Flujo de Migración:**
1. Importar Excel/CSV → Tabla `_staging` (vía DBeaver Import Wizard)
2. Normalizar datos en `_staging` (convertir 'nn'/'NN' → '', fechas, etc.)
3. INSERT desde `_staging` → Tabla `public.*` con validaciones

#### **Normalización de Datos 'NN':**
- Regla: Si un campo contiene 'nn' o 'NN' (cualquier caso, con espacios), convertir a `''` (string vacío)
- Aplicado en:
  - ✅ Frontend: `ExcelUploader.tsx`, `CrearClienteForm.tsx` (función `blankIfNN`)
  - ✅ SQL: CTEs en scripts de INSERT que normalizan 'nn' → NULL o valores por defecto

#### **Problemas Resueltos Durante Migración:**

1. **Foreign Key Constraints:**
   - Problema: `TRUNCATE TABLE public.clientes` fallaba por FK en `public.notificaciones`
   - Solución: `TRUNCATE TABLE public.notificaciones, public.clientes RESTART IDENTITY;`

2. **Formato de Fechas:**
   - Problema: `ERROR: date/time field value out of range: "10/30/2025"`
   - Solución: Scripts SQL detectan MM/DD/YYYY y DD/MM/YYYY, convierten a DATE usando `make_date`

3. **Validación de Nombres:**
   - Problema: `violates check constraint "chk_nombres_palabras"` (nombre tenía >4 palabras)
   - Solución: CTE que trunca nombres a las primeras 4 palabras

4. **Validación de Email:**
   - Problema: `violates check constraint "chk_email_valido"` (email tenía 'ñ')
   - Solución: CTE que normaliza email a ASCII (reemplaza 'ñ'→'n', etc.)

5. **Tamaño de Campo `numero_documento`:**
   - Problema: `value too long for type character varying(100)` en `pagos.numero_documento`
   - Solución: `ALTER TABLE public.pagos ALTER COLUMN numero_documento TYPE VARCHAR(255);`

---

### 2. ✅ CONFIGURACIÓN DEL PROXY (Frontend → Backend)

#### **Archivos Modificados:**

**`frontend/server.js`:**
- ✅ Configurado `http-proxy-middleware` para redirigir `/api/*` → Backend URL
- ✅ Variable `API_URL` desde `VITE_API_BASE_URL` o `VITE_API_URL`
- ✅ `pathRewrite` para re-agregar `/api` que Express elimina
- ✅ Logging extensivo para debug (onProxyReq, onProxyRes, onError)
- ✅ Wrapper de error handling para capturar errores silenciosos
- ✅ Security headers (OWASP best practices)
- ✅ Proxy registrado **ANTES** de `express.static`

**`frontend/src/config/env.ts`:**
- ✅ En **producción**: Fuerza `API_URL = ''` (rutas relativas)
- ✅ En **desarrollo**: Usa `VITE_API_URL` si está configurada (validación de formato)
- ✅ Logs warnings si `VITE_API_URL` no está configurada

**`frontend/package.json`:**
- ✅ Agregado `"http-proxy-middleware": "^3.0.3"` a dependencies

#### **Configuración de Variables de Entorno (Render Frontend):**
- `VITE_API_BASE_URL=https://pagos-f2qf.onrender.com` (URL pública del backend)
- `VITE_API_URL=https://pagos-f2qf.onrender.com` (opcional, fallback)

#### **Problemas Resueltos:**

1. **Proxy no interceptaba peticiones:**
   - Problema: Las peticiones `/api/*` no llegaban al backend
   - Solución: Proxy middleware movido ANTES de `express.static`

2. **PathRewrite incorrecto:**
   - Problema: Path venía con query string incluido: `"/v1/clientes?page=1&per_page=20"`
   - Solución: `pathRewrite` extrae solo el path sin query: `path.split('?')[0]`

3. **Missing dependency:**
   - Problema: `Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'http-proxy-middleware'`
   - Solución: Agregado a `package.json` dependencies

4. **CORS Errors:**
   - Problema: Frontend hacía llamadas absolutas al backend, causando CORS
   - Solución: `env.ts` fuerza rutas relativas en producción, proxy maneja `/api/*`

5. **307 Redirect de FastAPI:**
   - Problema: FastAPI redirigía `/api/v1/clientes` → `/api/v1/clientes/` (trailing slash)
   - Solución: `backend/app/main.py` → `redirect_slashes=False` en FastAPI()

---

### 3. ✅ CAMBIOS EN FRONTEND (Manejo de 'NN')

#### **Archivos Modificados:**

**`frontend/src/components/clientes/ExcelUploader.tsx`:**
- ✅ Función `blankIfNN(value)` que convierte 'nn'/'NN' → ''
- ✅ Aplicado a todos los campos antes de `saveIndividualClient` y `handleSaveData`
- ✅ Validación actualizada: `validateField` acepta 'nn' como válido (luego se normaliza)

**`frontend/src/components/clientes/CrearClienteForm.tsx`:**
- ✅ Función `blankIfNN(value)` que convierte 'nn'/'NN' → ''
- ✅ Aplicado a todos los campos en `handleSubmit`:
  - `cedula`, `nombres`, `telefono`, `email`
  - `callePrincipal`, `calleTransversal`, `descripcion`
  - `parroquia`, `municipio`, `ciudad`, `estadoDireccion`
  - `fechaNacimiento`, `ocupacion`, `notas`
- ✅ Validaciones actualizadas: `isNN` es considerado "válido vacío" en:
  - `validateNombres`, `validateOcupacion`, `validateDireccion`, `validateTelefono`, `validateFechaNacimiento`

---

### 4. ✅ BACKEND (FastAPI)

**`backend/app/main.py`:**
- ✅ `redirect_slashes=False` agregado a FastAPI() para evitar redirects 307

---

## 🔍 DIAGNÓSTICO ACTUAL DEL PROXY

### **Logs Esperados (Si funciona):**
```
📥 [GET] Petición API recibida: /api/v1/clientes
🔄 Proxy middleware ejecutándose para: GET /v1/clientes
🔄 Path rewrite:
   Path recibido (con query?): "/v1/clientes?page=1&per_page=20"
   Path sin query: "/v1/clientes"
   Path reescrito: "/api/v1/clientes"
➡️  [GET] Proxying hacia backend
   Target URL completa: https://pagos-f2qf.onrender.com/api/v1/clientes?page=1&per_page=20
✅ [GET] Proxy response: 200 para /api/v1/clientes?page=1&per_page=20
```

### **Problema Actual Detectado:**
- ❌ `onProxyReq` NO se ejecuta (no aparece en logs)
- ❌ `onProxyRes` NO se ejecuta (no aparece en logs)
- ✅ `pathRewrite` SÍ se ejecuta (aparece en logs)
- ✅ El wrapper del middleware SÍ se ejecuta (aparece `🔄 Proxy middleware ejecutándose`)

### **Posibles Causas:**
1. El `proxyMiddleware` retornado por `createProxyMiddleware` no se está ejecutando correctamente
2. Hay un error silencioso después del `pathRewrite` que impide que `onProxyReq` se ejecute
3. El `http-proxy-middleware` tiene un problema con la configuración actual

---

## 🔧 CHECKLIST DE AUDITORÍA PARA PRÓXIMOS LOGS

### **1. Verificar Inicio del Servidor:**
- [ ] `🔍 API_URL configurado: https://pagos-f2qf.onrender.com`
- [ ] `➡️  Proxy de /api hacia: https://pagos-f2qf.onrender.com`
- [ ] `✅ Proxy middleware registrado para rutas /api/*`

### **2. Verificar Intercepción de Peticiones:**
- [ ] `📥 [GET] Petición API recibida: /api/v1/clientes`
- [ ] `🔄 Proxy middleware ejecutándose para: GET /v1/clientes`

### **3. Verificar PathRewrite:**
- [ ] `🔄 Path rewrite:` aparece
- [ ] `Path sin query: "/v1/clientes"` (sin query string)
- [ ] `Path reescrito: "/api/v1/clientes"` (correcto)

### **4. Verificar Envío al Backend:**
- [ ] `➡️  [GET] Proxying hacia backend` aparece
- [ ] `Target URL completa: https://pagos-f2qf.onrender.com/api/v1/clientes?page=1&per_page=20`

### **5. Verificar Respuesta del Backend:**
- [ ] `✅ [GET] Proxy response: 200` (o código de status)

### **6. Si Hay Errores:**
- [ ] `❌ Error en proxy para...` (mensaje de error específico)
- [ ] `❌ Error al ejecutar proxy middleware:` (error del wrapper)

---

## 📊 CONFIGURACIÓN ACTUAL

### **Variables de Entorno (Render Frontend):**
```
VITE_API_BASE_URL=https://pagos-f2qf.onrender.com
VITE_API_URL=https://pagos-f2qf.onrender.com (opcional)
```

### **Dependencias (frontend/package.json):**
```json
{
  "http-proxy-middleware": "^3.0.3",
  "express": "^4.18.2"
}
```

### **Backend URL:**
- Pública: `https://pagos-f2qf.onrender.com`
- Service ID: `srv-d3l90jb3fgac73adc570` (NO usar en config)

---

## 🚨 ACCIONES RECOMENDADAS

1. **Si `onProxyReq` NO aparece:**
   - Revisar versión de `http-proxy-middleware`
   - Probar sin `pathRewrite` para ver si el problema está ahí
   - Revisar si hay errores en `onError` que no estamos viendo

2. **Si el backend NO recibe peticiones:**
   - Verificar conectividad: `curl https://pagos-f2qf.onrender.com/api/v1/health`
   - Verificar que el backend está activo en Render
   - Verificar logs del backend para ver si llegan peticiones

3. **Si hay 403/404:**
   - Verificar que el endpoint `/api/v1/clientes` existe en el backend
   - Verificar autenticación: headers `Authorization` se están pasando
   - Verificar CORS en el backend

---

## 📝 NOTAS FINALES

- **BD Migration:** ✅ Completa - clientes, prestamos, pagos migrados
- **Normalización 'NN':** ✅ Implementada en frontend y SQL
- **Proxy Configuration:** ⚠️ En proceso de debug - falta confirmar que `onProxyReq` se ejecuta
- **Backend Configuration:** ✅ `redirect_slashes=False` configurado

