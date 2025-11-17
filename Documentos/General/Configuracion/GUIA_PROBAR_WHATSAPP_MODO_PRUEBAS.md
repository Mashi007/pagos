# 🧪 Guía: Probar WhatsApp en Modo Pruebas y Verificar Conexión

## 🎯 Objetivo

Verificar que WhatsApp aceptó la conexión y que la configuración funciona correctamente antes de activar envíos a clientes reales.

---

## 📋 Paso 1: Activar Modo Pruebas

### En la Interfaz de Configuración:

1. **Ve a**: Configuración → WhatsApp
2. **Selecciona**: "Pruebas (Todos los mensajes a número de prueba)"
3. **Configura el Teléfono de Pruebas**: 
   - Ingresa tu número de WhatsApp con código de país
   - Ejemplo: `+593983000700` o `+584121234567`
   - **IMPORTANTE**: Este número debe estar registrado en WhatsApp y ser accesible
4. **Guarda la configuración**

### Verificación Visual:

Deberías ver un mensaje amarillo que dice:
```
⚠️ Modo Pruebas activo
El mensaje se redirigirá a la dirección de pruebas configurada (+593983000700).
```

---

## 🧪 Paso 2: Ejecutar Test Completo

### Opción A: Desde la Interfaz (Recomendado)

1. **En la página de configuración de WhatsApp**
2. **Haz clic en el botón "Test Completo"**
3. **Espera a que termine** (puede tardar 10-30 segundos)

### Opción B: Desde la API

```bash
GET /api/v1/configuracion/whatsapp/test-completo
```

---

## ✅ Paso 3: Verificar que WhatsApp Aceptó la Conexión

### 🔍 **Señales de que WhatsApp ACEPTÓ la Conexión:**

#### 1. **En el Test Completo - Test "Conexión con Meta API":**

Busca el test llamado **"Conexión con Meta API"**:

**✅ SI ACEPTÓ (Éxito):**
```json
{
  "nombre": "Conexión con Meta API",
  "exito": true,
  "mensaje": "Conexión exitosa con Meta Developers API",
  "detalles": {
    "respuesta": "Conexión exitosa con Meta Developers API",
    "api_url": "https://graph.facebook.com/v18.0",
    "phone_number_id": "6271892438...",
    "access_token": "✅ Configurado",
    "business_account_id": "3624385381..."
  }
}
```

**❌ SI RECHAZÓ (Error):**
```json
{
  "nombre": "Conexión con Meta API",
  "exito": false,
  "error": "Token de acceso inválido o expirado",
  "detalles": {
    "error_code": "META_UNAUTHORIZED",
    "respuesta": "Error de conexión: 401"
  }
}
```

#### 2. **En la Interfaz Visual:**

Si el test completo muestra:
- ✅ **"Conexión con Meta API"** con checkmark verde
- ✅ **"Exitosos: 5"** (o más)
- ❌ **"Fallidos: 0"**

**Esto significa que WhatsApp ACEPTÓ la conexión.**

---

## 📊 Paso 4: Enviar Mensaje de Prueba

### Para Verificar que Realmente Funciona:

1. **En la sección "Envío de Mensaje de Prueba"**
2. **Ingresa tu número de teléfono** (el mismo que configuraste en "Teléfono de Pruebas")
3. **Opcional**: Escribe un mensaje personalizado
4. **Haz clic en "Enviar Mensaje de Prueba"**

### ✅ Señales de Éxito:

**En la Interfaz:**
- Aparece un mensaje verde: "Mensaje de prueba enviado exitosamente a +593983000700"
- El resultado muestra: `"mensaje": "Mensaje enviado exitosamente"`

**En tu WhatsApp:**
- **Recibes el mensaje** en tu teléfono
- El mensaje incluye: `[PRUEBAS - Originalmente para: ...]` (si estaba en modo pruebas)

**En los Logs del Backend:**
```
✅ WhatsApp enviado a +593983000700 (Cliente X, PAGO_DIA_0)
```

---

## 🔍 Paso 5: Verificar en los Logs

### Logs que Indican Éxito:

#### 1. **Test de Conexión:**
```
INFO [TEST] Verificando conexión con Meta API...
INFO ✅ Conexión exitosa con Meta Developers API
```

#### 2. **Envío de Mensaje:**
```
INFO ✅ WhatsApp enviado a +593983000700 (Cliente X, PAGO_DIA_0)
```

#### 3. **Modo Pruebas Activo:**
```
WARNING 🧪 MODO PRUEBAS: Redirigiendo mensaje de +584121234567 a +593983000700
```

### Logs que Indican Error:

#### 1. **Token Inválido:**
```
ERROR ❌ Token de Meta inválido o expirado
ERROR ❌ Error de conexión: 401
```

#### 2. **Phone Number ID Incorrecto:**
```
ERROR ❌ Solicitud inválida: Invalid phone number ID
ERROR ❌ Error de conexión: 400
```

#### 3. **Rate Limit:**
```
WARNING ⚠️ Rate limit de Meta alcanzado. Esperar 60s
```

---

## 📱 Paso 6: Verificar en "Envíos Recientes"

### En la Interfaz:

1. **Ve a la sección "Verificación de Envíos Recientes"**
2. **Busca notificaciones con:**
   - **Canal**: `WHATSAPP`
   - **Estado**: `ENVIADA` (verde)
   - **Fecha de envío**: Reciente

### Ejemplo de Notificación Exitosa:

```
✅ ENVIADA
Prueba de configuración - RapiCredit
📅 17/11/2025 00:30:00
Tipo: WHATSAPP
```

---

## 🎯 Resumen: Cómo Saber que WhatsApp Aceptó

### ✅ **Señales de Éxito (WhatsApp ACEPTÓ):**

1. **Test Completo muestra:**
   - ✅ "Conexión con Meta API": **exito: true**
   - ✅ Mensaje: "Conexión exitosa con Meta Developers API"
   - ✅ Todos los tests pasan (5/5 exitosos)

2. **Mensaje de Prueba:**
   - ✅ Recibes el mensaje en tu WhatsApp
   - ✅ Estado: "ENVIADA" en la interfaz
   - ✅ Logs muestran: "✅ WhatsApp enviado a..."

3. **Envíos Recientes:**
   - ✅ Aparecen notificaciones WhatsApp con estado "ENVIADA"
   - ✅ Tienen fecha de envío reciente

### ❌ **Señales de Error (WhatsApp RECHAZÓ):**

1. **Test Completo muestra:**
   - ❌ "Conexión con Meta API": **exito: false**
   - ❌ Error: "Token de acceso inválido" o "401 Unauthorized"
   - ❌ Tests fallan (menos de 5/5 exitosos)

2. **Mensaje de Prueba:**
   - ❌ NO recibes el mensaje
   - ❌ Estado: "FALLIDA" en la interfaz
   - ❌ Logs muestran: "❌ Error enviando WhatsApp..."

3. **Errores Comunes:**
   - `401 Unauthorized`: Token inválido o expirado
   - `400 Bad Request`: Phone Number ID incorrecto
   - `403 Forbidden`: Permisos insuficientes
   - `429 Too Many Requests`: Rate limit alcanzado

---

## 🔧 Troubleshooting

### Si el Test de Conexión Falla:

1. **Verifica el Access Token:**
   - Ve a Meta Developers → WhatsApp → API Setup
   - Genera un nuevo token si expiró
   - Copia el token completo (comienza con `EAA...`)

2. **Verifica el Phone Number ID:**
   - Debe ser solo números (sin `+` ni espacios)
   - Ejemplo correcto: `627189243818989`
   - Ejemplo incorrecto: `+15556549812`

3. **Verifica que WhatsApp esté habilitado:**
   - En Meta Developers, verifica que WhatsApp Business API esté activo
   - Verifica que el número de teléfono esté verificado

### Si el Mensaje No Llega:

1. **Verifica el Modo Pruebas:**
   - Confirma que `modo_pruebas: 'true'`
   - Verifica que `telefono_pruebas` esté configurado correctamente

2. **Verifica el Número de Pruebas:**
   - Debe incluir código de país: `+593983000700`
   - Debe estar registrado en WhatsApp
   - Debe ser accesible (tener WhatsApp activo)

3. **Revisa los Logs:**
   - Busca errores específicos de Meta
   - Verifica rate limits
   - Revisa si hay problemas de red

---

## 📋 Checklist de Verificación

### Antes de Probar:

- [ ] Modo Pruebas activado: `modo_pruebas: 'true'`
- [ ] Teléfono de Pruebas configurado: `+593983000700` (o tu número)
- [ ] Access Token válido (no expirado)
- [ ] Phone Number ID correcto
- [ ] API URL correcta: `https://graph.facebook.com/v18.0`

### Después de Probar:

- [ ] Test Completo: "Conexión con Meta API" = ✅ **exito: true**
- [ ] Mensaje de prueba enviado exitosamente
- [ ] Mensaje recibido en WhatsApp
- [ ] Estado en BD: "ENVIADA"
- [ ] Logs muestran éxito

---

## 🚀 Próximos Pasos

Una vez que verifiques que WhatsApp aceptó la conexión:

1. **Prueba con varios mensajes** para asegurar consistencia
2. **Revisa los logs** para confirmar que no hay errores
3. **Cuando estés listo para producción:**
   - Cambia `modo_pruebas: 'false'`
   - Los mensajes se enviarán a clientes reales
   - Monitorea los primeros envíos

---

## ⚠️ Notas Importantes

1. **Modo Pruebas es Seguro:**
   - Todos los mensajes van al teléfono de pruebas
   - No se envían a clientes reales
   - Perfecto para probar sin riesgo

2. **Token Temporal:**
   - Los tokens temporales expiran en 1 hora
   - Para producción, usa tokens permanentes
   - Verifica que el token no haya expirado antes de probar

3. **Rate Limits:**
   - Meta limita a 1,000 mensajes/día (gratis)
   - 80 mensajes/segundo
   - El sistema maneja esto automáticamente

