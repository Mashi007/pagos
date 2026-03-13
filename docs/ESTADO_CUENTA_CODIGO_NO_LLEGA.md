# Estado de cuenta público: el código no llega por correo

Cuando en https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta el usuario solicita el código y **no recibe el correo**, revisar lo siguiente.

## 1. Logs del backend (Render)

Tras desplegar los cambios recientes, el backend escribe en log el motivo por el que el correo no se envió:

| Mensaje en log | Causa | Qué hacer |
|----------------|--------|-----------|
| `estado_cuenta solicitar: codigo NO enviado (servicio estado_cuenta desactivado)` | El envío de emails para "Estado de cuenta" está desactivado. | En la app: **Configuración > Email** y activar **Estado de cuenta** (email_activo_estado_cuenta). |
| `estado_cuenta solicitar: codigo NO enviado por correo a ...: No hay servidor SMTP configurado` | No hay SMTP configurado. | Configurar SMTP en **Configuración > Email** (host, usuario, contraseña). |
| `estado_cuenta solicitar: codigo NO enviado por correo a ...: Falta contrasena SMTP` | Contraseña SMTP vacía o no guardada. | Completar y guardar la contraseña en **Configuración > Email**. |
| `outcome=ok_email_fail` | `send_email` devolvió error (SMTP rechazó, red, etc.). | Revisar el mensaje de error inmediatamente anterior en el log; verificar credenciales SMTP y que el servidor permita envío desde la app. |

En Render: **Dashboard > servicio > Logs** y buscar `estado_cuenta solicitar`.

## 2. Configuración en la aplicación

- **Configuración > Email**
  - **Estado de cuenta** debe estar **activado** (checkbox o equivalente).
  - SMTP: host, puerto, usuario y contraseña correctos.
  - Si usas **Modo pruebas**, los correos se redirigen al email de pruebas; el cliente no los recibe en su correo real.

## 3. Datos del cliente

- El código solo se envía si el cliente existe en la tabla `clientes` y tiene un **email** no vacío.
- Si la cédula no está registrada o no tiene email, la API responde igual (por seguridad) pero no se envía correo. En log puede aparecer `outcome=ok_sin_email`.

## 4. Spam y bandeja de entrada

- Indicar al usuario que revise **carpeta de spam/correo no deseado** y que el remitente no esté bloqueado.
