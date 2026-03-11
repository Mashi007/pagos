# Auditoría: Configuración Email – "Usuario o contraseña no aceptados"

## Resumen

Al guardar la configuración de email y probar envío o IMAP, el sistema devuelve **535 / AUTHENTICATIONFAILED** y el mensaje "Usuario o contraseña no aceptados", aunque el usuario cree haber guardado la contraseña correcta. La causa raíz es que **la contraseña no se está actualizando en el servidor** cuando el usuario no reescribe el campo.

---

## Flujo actual

1. **Carga de la página (GET /configuracion/email/configuracion)**  
   - El backend devuelve la config con `smtp_password: "***"` e `imap_password: "***"` (enmascarado por seguridad).  
   - El frontend pone en estado `config.smtp_password = "***"` y `config.imap_password = "***"`.

2. **Usuario hace clic en "Guardar configuración" (PUT)**  
   - El frontend envía el objeto completo, incluyendo `smtp_password: "***"` e `imap_password: "***"`.  
   - El backend en `put_email_configuracion` usa `_is_password_masked(v)`: si el valor es `""` o `"***"`, **no actualiza** ese campo en el stub ni en BD (para no sobrescribir la contraseña real con el placeholder).  
   - La respuesta es **200** y `"Configuracion guardada"` aunque la contraseña no se haya modificado.

3. **Usuario hace clic en "Enviar email de prueba" o "Probar conexión IMAP"**  
   - El backend usa la config almacenada (BD + holder).  
   - Si la contraseña almacenada es la antigua, está vacía o es incorrecta, Gmail responde **535** (SMTP) o **AUTHENTICATIONFAILED** (IMAP).  
   - El usuario ve "Usuario o contraseña no aceptados" y no entiende por qué, porque acaba de "guardar".

---

## Causa raíz

- **El campo de contraseña en la UI muestra `***`** (valor enmascarado que viene del API).  
- **El usuario interpreta que "ya tiene contraseña guardada"** y no la vuelve a escribir.  
- **Al guardar, se envía `smtp_password: "***"`** y el backend, por diseño, **no actualiza** la contraseña.  
- Resultado: en el servidor sigue la contraseña anterior (o ninguna). Si esa contraseña no es válida para la cuenta actual, SMTP/IMAP fallan.

Es decir: no es un bug de validación ni de envío de formulario; es una **confusión de UX** (*** parece “contraseña ya guardada”) unida al **diseño correcto** del backend de no aceptar `***` como nueva contraseña.

---

## Evidencia en logs

- **Frontend:** `Datos a enviar: { ..., smtp_password: "***", ... }` → se está enviando el valor enmascarado.  
- **Backend:** `Configuracion email actualizada y persistida en BD (campos: [..., 'smtp_password', ...])` → el *campo* va en el payload, pero el backend lo rechaza por `_is_password_masked` y no escribe nueva contraseña.  
- **Después:** `SMTPAuthenticationError: (535, b'5.7.8 Username and Password not accepted...')` → el servidor está usando la contraseña que tiene almacenada (antigua o vacía), no una “nueva” porque nunca se envió una nueva.

---

## Cambios realizados / recomendados

1. **Backend (configuracion_email.py)**  
   - En la respuesta del PUT, indicar cuando la contraseña **no** se actualizó porque venía enmascarada, por ejemplo:  
     `password_not_updated: true` y mensaje tipo:  
     "Configuración guardada. La contraseña no se modificó (reingrésala si quieres cambiarla)."  
   - Así el frontend puede mostrar un aviso explícito.

2. **Frontend (EmailConfig.tsx)**  
   - Si en el payload enviado `smtp_password === "***"` (o vacío), mostrar después de guardar un **toast de advertencia**:  
     "La contraseña no se actualizó porque el campo mostraba ***. Para cambiarla, escríbela de nuevo y guarda."  
   - Añadir una **nota visible** junto al campo Contraseña (y Contraseña IMAP):  
     "Si cambiaste de cuenta o contraseña, escríbela aquí. *** no actualiza la contraseña en el servidor."

3. **Usuario**  
   - Para **cambiar** la contraseña: borrar el contenido del campo (o escribir la nueva), guardar de nuevo.  
   - No confiar en que “guardar con ***” actualice la contraseña; el backend nunca la sustituye por `***`.

---

## Conclusión

El problema es **consistente** con el diseño actual (no guardar `***` como contraseña) y con el flujo real (envío de `***` en el PUT). La solución es **clarificar en la UI** que `***` no actualiza la contraseña y **avisar al usuario** cuando guarda sin reingresarla, además de que el backend opcionalmente informe en la respuesta que la contraseña no se modificó.
