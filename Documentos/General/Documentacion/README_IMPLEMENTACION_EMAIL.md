# 📧 Guía de Implementación de Configuración de Email

## 📋 Orden de Implementación

### **PASO 1: Verificar Estado Actual** ✅
**Script:** `verificar_email_simple.sql` o `verificar_configuracion_email.sql`

**Objetivo:** Confirmar que no hay configuraciones de email en la base de datos.

**Cómo ejecutar:**
1. Abrir DBeaver
2. Conectar a la base de datos
3. Abrir `backend/scripts/verificar_email_simple.sql`
4. Ejecutar todas las queries (una por una o todas juntas)
5. Verificar que todas las configuraciones muestren "❌ FALTANTE" o "NO CONFIGURADO"

**Resultado esperado:** Confirmar que no hay configuraciones (como ya verificaste)

---

### **PASO 2: Preparar Valores de Configuración** 📝

Antes de ejecutar los scripts de inserción, necesitas tener listos estos valores:

#### **Para Gmail:**
- ✅ `smtp_host`: `smtp.gmail.com`
- ✅ `smtp_port`: `587` (TLS) o `465` (SSL)
- ✅ `smtp_user`: Tu email completo (ej: `usuario@gmail.com`)
- ✅ `smtp_password`: **App Password de Gmail** (16 caracteres, sin espacios)
  - Cómo obtener: https://myaccount.google.com/apppasswords
  - Requiere 2FA activado
- ✅ `from_email`: Email remitente (ej: `noreply@rapicredit.com`)
- ✅ `from_name`: `RapiCredit` (o el nombre que prefieras)
- ✅ `smtp_use_tls`: `true` (para puerto 587) o `false` (para puerto 465)
- ✅ `modo_pruebas`: `false` (producción) o `true` (desarrollo)
- ✅ `email_pruebas`: Solo si `modo_pruebas = true`

#### **Para Otros Proveedores:**
- **Outlook/Hotmail:**
  - `smtp_host`: `smtp-mail.outlook.com`
  - `smtp_port`: `587`
  - `smtp_use_tls`: `true`
- **Yahoo:**
  - `smtp_host`: `smtp.mail.yahoo.com`
  - `smtp_port`: `587`
  - `smtp_use_tls`: `true`

---

### **PASO 3: Insertar Configuración** 🚀

**Elige UNA de estas opciones:**

#### **Opción A: Script de Gmail (Recomendado si usas Gmail)**
**Script:** `ejemplo_configuracion_gmail.sql`

**Pasos:**
1. Abrir `backend/scripts/ejemplo_configuracion_gmail.sql` en DBeaver
2. **REEMPLAZAR** los siguientes valores:
   - `<TU-EMAIL@gmail.com>` → Tu email de Gmail real
   - `<TU-APP-PASSWORD>` → Tu App Password de Gmail
   - `<noreply@rapicredit.com>` → Email remitente deseado
   - `<pruebas@ejemplo.com>` → Email para pruebas (si modo_pruebas = true)
3. Ejecutar TODO el script (Ctrl+Enter o botón "Execute SQL Script")
4. Verificar que no haya errores

#### **Opción B: Script Genérico (Para cualquier proveedor)**
**Script:** `insertar_configuracion_email.sql`

**Pasos:**
1. Abrir `backend/scripts/insertar_configuracion_email.sql` en DBeaver
2. **REEMPLAZAR** todos los valores entre `< >` con tus datos reales
3. Ejecutar TODO el script
4. Verificar que no haya errores

#### **Opción C: Configurar desde la Interfaz Web** 🌐
1. Ir a: `https://rapicredit.onrender.com/configuracion?tab=email`
2. Llenar todos los campos requeridos
3. Hacer clic en "Guardar"
4. El sistema insertará automáticamente en la base de datos

---

### **PASO 4: Verificar Configuración Insertada** ✅

**Script:** `verificar_email_simple.sql` (Query 1 y Query 2)

**Pasos:**
1. Ejecutar la Query 1 de `verificar_email_simple.sql`:
   ```sql
   SELECT
       clave,
       CASE
           WHEN clave IN ('smtp_password', 'smtp_user') THEN '*** (oculto)'
           ELSE valor
       END AS valor
   FROM configuracion_sistema
   WHERE categoria = 'EMAIL'
   ORDER BY clave;
   ```

2. **Resultado esperado:**
   - Debe mostrar todas las configuraciones con valores (no "NO CONFIGURADO")
   - `smtp_password` y `smtp_user` deben mostrar "*** (oculto)"

3. Ejecutar la Query 2 de `verificar_email_simple.sql`:
   ```sql
   SELECT
       'smtp_host' AS configuracion,
       CASE WHEN EXISTS (SELECT 1 FROM configuracion_sistema WHERE categoria = 'EMAIL' AND clave = 'smtp_host' AND valor IS NOT NULL AND valor != '')
            THEN '✅ OK'
            ELSE '❌ FALTANTE'
       END AS estado
   -- ... (resto de la query)
   ```

4. **Resultado esperado:**
   - Todas las configuraciones requeridas deben mostrar "✅ OK"
   - Solo las opcionales pueden mostrar "⚠️ OPCIONAL"

---

### **PASO 5: Probar Conexión SMTP** 🔌

**Método 1: Desde la API (Recomendado)**
1. Ir a: `https://rapicredit.onrender.com/api/v1/configuracion/email/estado`
2. Debe mostrar:
   ```json
   {
     "configurada": true,
     "mensaje": "Configuración completa y válida",
     "conexion_smtp": {
       "success": true,
       "message": "Conexión SMTP exitosa"
     }
   }
   ```

**Método 2: Desde la Interfaz Web**
1. Ir a: `https://rapicredit.onrender.com/configuracion?tab=email`
2. Hacer clic en "Probar Configuración"
3. Verificar que muestre éxito

---

### **PASO 6: Enviar Email de Prueba** 📨

**Método 1: Desde la API**
```bash
POST https://rapicredit.onrender.com/api/v1/configuracion/email/probar
Content-Type: application/json
Authorization: Bearer <tu_token>

{
  "email_destino": "tu-email@ejemplo.com"
}
```

**Método 2: Desde la Interfaz Web**
1. Ir a: `https://rapicredit.onrender.com/configuracion?tab=email`
2. Hacer clic en "Enviar Email de Prueba"
3. Ingresar email destino
4. Verificar que el email llegue

---

## 📁 Archivos de Scripts Disponibles

1. **`verificar_email_simple.sql`** - Verificación rápida (4 queries simples)
2. **`verificar_configuracion_email.sql`** - Verificación completa (6 queries detalladas)
3. **`ejemplo_configuracion_gmail.sql`** - Inserción para Gmail (listo para usar)
4. **`insertar_configuracion_email.sql`** - Inserción genérica (para cualquier proveedor)

## ⚠️ Problemas Comunes y Soluciones

### **Error: "ON CONFLICT DO NOTHING" no funciona**
**Solución:** Cambiar a `ON CONFLICT (categoria, clave) DO UPDATE SET valor = EXCLUDED.valor`

### **Error: "App Password no funciona"**
**Solución:**
1. Verificar que 2FA esté activado en Google
2. Generar nueva App Password
3. Usar los 16 caracteres sin espacios

### **Error: "Conexión SMTP falla"**
**Solución:**
1. Verificar que el puerto esté abierto (587 o 465)
2. Verificar que `smtp_use_tls` coincida con el puerto
3. Verificar credenciales

### **Emails no se envían pero conexión es exitosa**
**Solución:**
1. Verificar `modo_pruebas`:
   - Si es `true`, verificar que `email_pruebas` esté configurado
   - Si es `false`, los emails van a destinatarios reales
2. Revisar logs del servidor para errores específicos

## ✅ Checklist Final

- [ ] Paso 1: Verificación inicial completada
- [ ] Paso 2: Valores de configuración preparados
- [ ] Paso 3: Configuración insertada en BD
- [ ] Paso 4: Verificación de configuración exitosa
- [ ] Paso 5: Conexión SMTP probada y exitosa
- [ ] Paso 6: Email de prueba enviado y recibido

## 🆘 Soporte

Si encuentras problemas:
1. Revisar logs del servidor
2. Ejecutar `verificar_email_simple.sql` para diagnóstico
3. Verificar que todos los valores estén correctos (sin `< >`)
4. Probar conexión SMTP desde otro cliente (ej: Thunderbird) para aislar el problema

