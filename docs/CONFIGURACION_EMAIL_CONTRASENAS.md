# Configuración de email: guardado de contraseñas

## Causa del error "no guardar clave y solo pasar ***"

El fallo **no** se debía a la falta de `ENCRYPTION_KEY`. La causa era un **bug en el backend** al guardar las 4 cuentas de correo:

1. **No se copiaba la contraseña nueva**: cuando el usuario escribía la contraseña en el formulario y pulsaba Guardar, el backend no asignaba ese valor al objeto que se persiste (`base[k] = v` faltaba cuando el valor no era "***").
2. **Asignación incorrecta**: había un `base[k] = v` dentro del bucle que rellena contraseñas existentes, lo que podía sobrescribir campos con valores equivocados.

Con eso, al guardar:
- El frontend enviaba la contraseña real solo si el usuario la acababa de escribir; si el campo se mostraba como "***", enviaba "***".
- El backend, al no copiar bien los valores del payload, terminaba guardando contraseña vacía o reutilizando mal valores, y al cargar después parecía que "solo pasaba ***".

**Corrección aplicada**: se añadió la asignación correcta `base[k] = v` para todos los campos no enmascarados y se eliminó la asignación errónea dentro del bucle de campos sensibles. Además, cuando el usuario no cambia la contraseña (envía "***"), se reutiliza la contraseña ya guardada (desencriptada desde BD) antes de volver a encriptar y guardar.

## ¿Hace falta ENCRYPTION_KEY?

**No es obligatorio** para que el envío de correo funcione.

- **Sin `ENCRYPTION_KEY`**: las contraseñas se guardan en la base de datos en **texto plano** (el intento de encriptar devuelve `None` y se persiste el valor tal cual). El flujo de guardado y de uso para SMTP funciona.
- **Con `ENCRYPTION_KEY`** (recomendado en producción): las contraseñas se encriptan antes de guardar y se desencriptan al cargar; así no quedan en claro en la BD.

Si todas las cuentas son Workspace y antes solo usabas "clave de aplicación" sin configurar `ENCRYPTION_KEY`, el problema era el bug de guardado anterior, no la falta de esa variable. Con el bug corregido, al volver a guardar las cuentas con sus contraseñas (o claves de aplicación), deberían persistirse bien y dejar de "caducar" o mostrarse como "***" sin guardar.

## Resumen

| Antes (bug) | Después (corregido) |
|-------------|----------------------|
| Contraseña nueva no se copiaba al objeto a guardar | Se copia con `base[k] = v` |
| "***" o vacío podía sobrescribir la contraseña guardada | Si viene "***", se reutiliza la contraseña existente desde BD |
| Contraseñas parecían no guardarse o caducar | Se persisten correctamente (en claro si no hay ENCRYPTION_KEY, encriptadas si sí) |

Documentación disponible en el repo: este archivo y los comentarios en `backend/app/api/v1/endpoints/configuracion_email_cuentas.py` y `backend/app/core/email_config_holder.py`.
