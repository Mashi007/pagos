# 📝 Instrucciones para Actualizar Valores Pendientes

## ⚠️ Problema Actual

Tienes valores con marcadores `< >` que deben ser reemplazados:
- `smtp_user`: `<TU-EMAIL@gmail.com>` → Necesita tu email real
- `smtp_password`: `<TU-APP-PASSWORD>` → Necesita tu App Password
- `from_email`: `<noreply@rapicredit.com>` → Necesita email remitente
- `email_pruebas`: `<pruebas@ejemplo.com>` → Opcional

## ✅ Solución: Actualizar Manualmente

### Opción 1: Usar el Script SQL (Recomendado)

1. **Abre** `backend/scripts/actualizar_valores_pendientes.sql` en DBeaver

2. **Reemplaza** los valores entre comillas (incluyendo los `< >`):

   ```sql
   -- ANTES (con marcadores):
   SET valor = '<TU-EMAIL@gmail.com>', actualizado_en = NOW()

   -- DESPUÉS (con tu valor real):
   SET valor = 'miemail@gmail.com', actualizado_en = NOW()
   ```

3. **Ejecuta** cada UPDATE uno por uno o todo el script

### Opción 2: Actualizar Directamente en DBeaver

Ejecuta estos comandos SQL **reemplazando los valores**:

```sql
-- 1. Actualizar SMTP User
UPDATE configuracion_sistema
SET valor = 'TU-EMAIL-REAL@gmail.com', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'smtp_user';

-- 2. Actualizar SMTP Password (App Password de Gmail)
UPDATE configuracion_sistema
SET valor = 'TU-APP-PASSWORD-AQUI', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'smtp_password';

-- 3. Actualizar From Email
UPDATE configuracion_sistema
SET valor = 'noreply@rapicredit.com', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'from_email';

-- 4. Actualizar Email Pruebas (OPCIONAL)
UPDATE configuracion_sistema
SET valor = 'pruebas@ejemplo.com', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'email_pruebas';
```

## 📋 Ejemplo Completo con Valores Reales

```sql
-- Ejemplo con valores reales (NO uses estos, son solo ejemplos):
UPDATE configuracion_sistema
SET valor = 'usuario@gmail.com', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'smtp_user';

UPDATE configuracion_sistema
SET valor = 'abcd efgh ijkl mnop', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'smtp_password';

UPDATE configuracion_sistema
SET valor = 'noreply@rapicredit.com', actualizado_en = NOW()
WHERE categoria = 'EMAIL' AND clave = 'from_email';
```

## 🔑 Cómo Obtener App Password de Gmail

1. Ve a: https://myaccount.google.com/apppasswords
2. Selecciona "Correo" como aplicación
3. Selecciona "Otro (nombre personalizado)" como dispositivo
4. Escribe "RapiCredit" como nombre
5. Haz clic en "Generar"
6. Copia los 16 caracteres (puedes quitar los espacios)
7. Úsalo en `smtp_password`

## ✅ Verificar Después de Actualizar

Ejecuta esta query para verificar:

```sql
SELECT
    clave,
    CASE
        WHEN clave IN ('smtp_password', 'smtp_user') THEN '*** (oculto)'
        ELSE valor
    END AS valor,
    CASE
        WHEN clave IN ('smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'from_email')
        AND (valor IS NULL OR valor = '' OR valor LIKE '<%>')
        THEN '❌ PENDIENTE: Reemplaza el valor'
        WHEN clave IN ('smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'from_email')
        THEN '✅ Configurado'
        ELSE '⚠️ Opcional'
    END AS estado
FROM configuracion_sistema
WHERE categoria = 'EMAIL'
ORDER BY clave;
```

**Resultado esperado:** Todas las configuraciones requeridas deben mostrar "✅ Configurado"

## ⚠️ Errores Comunes

1. **Dejar los `< >` en los valores:**
   - ❌ Incorrecto: `'<TU-EMAIL@gmail.com>'`
   - ✅ Correcto: `'miemail@gmail.com'`

2. **Usar contraseña normal en lugar de App Password:**
   - ❌ No funciona con contraseña normal de Gmail
   - ✅ Debe ser App Password (16 caracteres)

3. **Olvidar las comillas simples:**
   - ❌ Incorrecto: `SET valor = miemail@gmail.com`
   - ✅ Correcto: `SET valor = 'miemail@gmail.com'`

