# Verificacion: 4 cuentas con clave de aplicacion

## Flujo verificado

### 1. Guardado (PUT /api/v1/configuracion/email/cuentas)
- Cada cuenta 1-4 puede tener su propio `smtp_user` y `smtp_password` (clave de aplicacion).
- Si envias contraseña nueva: se copia al objeto a guardar (`base[k] = v`) y se persiste (encriptada si hay ENCRYPTION_KEY, si no en texto plano).
- Si envias "***" (no cambiaste la contraseña): se reutiliza la contraseña ya guardada desde BD.
- Si la encriptacion falla: se conserva el `_encriptado` anterior para no perder la clave.

### 2. Carga (sync_from_db)
- Se lee la config de la tabla `configuracion` (clave=email_config).
- Para cada cuenta, si existe `smtp_password_encriptado` se desencripta y se deja en `_cuentas_data["cuentas"][i]["smtp_password"]`.
- Si no hay encriptado (guardado sin ENCRYPTION_KEY), se usa el valor en texto plano del JSON.

### 3. Uso por servicio (get_smtp_config)
- **Cobros** (formulario publico) -> cuenta asignada en `asignacion.cobros` (por defecto 1).
- **Estado de cuenta** (PDF, codigo) -> cuenta en `asignacion.estado_cuenta` (por defecto 2).
- **Notificaciones** (plantillas) -> cuenta por pestaña en `asignacion.notificaciones_tab` (3 o 4).
- **Enviar prueba** -> primera cuenta con SMTP/usuario/contraseña valida (1, 2 o 3/4).

Cada llamada a `send_email(..., servicio=..., tipo_tab=...)` obtiene la config de la cuenta que corresponde; esa config incluye `smtp_password` (la clave de aplicacion guardada para esa cuenta).

### 4. Login SMTP (email.py)
- Se usa `cfg["smtp_user"]` y `cfg["smtp_password"]` tal cual para `server.login()`.
- No se hace strip ni modificacion del password (por si la clave de aplicacion tuviera formato especial).

## Checklist para ti

- [ ] Cuenta 1 (Cobros): correo + clave de aplicacion guardados; Servidor SMTP (ej. smtp.gmail.com), Puerto 587.
- [ ] Cuenta 2 (Estado de cuenta): correo + clave de aplicacion; mismo servidor/puerto si es Gmail/Workspace.
- [ ] Cuentas 3 y 4 (Notificaciones): correo + clave de aplicacion cada una; asignacion de pestañas correcta en la UI.
- [ ] En cada cuenta, la clave de aplicacion es la generada para **esa** cuenta en Google (no reutilizar la de otra).
- [ ] Tras guardar, probar "Enviar prueba" y/o el flujo real (cobros, estado de cuenta, notificaciones) para confirmar que no sale 535.

Si aun sale 535 para una cuenta, es que Google rechaza usuario/contraseña de esa cuenta (revisar que la clave de aplicacion sea la correcta y que la cuenta tenga 2 pasos activados si exige app password).
