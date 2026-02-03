# Configurar Google Sheet para que aparezcan las papeletas

Si la hoja **Papeletas_WhatsApp** (o la que uses para el informe) está vacía, la app no está escribiendo en ella. Hay que configurar **ID de la hoja** y **acceso con Google** en la aplicación.

---

## 1. Obtener el ID de la hoja

1. Abre tu hoja en el navegador (ej. **Papeletas_WhatsApp**).
2. Mira la URL. Tiene esta forma:
   ```
   https://docs.google.com/spreadsheets/d/1PwYB4-e2-Uh69gCj0sla9_tl2b4qUHI4/edit
   ```
3. El **ID** es la parte entre `/d/` y `/edit`. En el ejemplo:  
   `1PwYB4-e2-Uh69gCj0sla9_tl2b4qUHI4`  
   Copia ese valor (el tuyo puede ser distinto).

---

## 2. Configurar en la app (RapiCredit)

1. Entra a **Configuración** (menú o `/pagos/configuracion`).
2. Abre la pestaña **Informe pagos** (Drive, Sheets, OCR).
3. En **ID Google Sheet** pega el ID que copiaste (ej. `1PwYB4-e2-Uh69gCj0sla9_tl2b4qUHI4`).
4. (Opcional) En **Pestaña donde escribir** escribe **Hoja 1** si quieres que las filas se escriban en la primera pestaña. Si lo dejas vacío, la app usará pestañas por horario (6am, 1pm, 4h30); si no existen, las crea.
5. Haz clic en **Guardar** (o el botón que guarde la configuración de Informe pagos).

---

## 3. Conectar con Google (OAuth)

Para que la app pueda **escribir** en la hoja, tiene que tener acceso a tu cuenta de Google:

1. En la misma pantalla **Informe pagos**, usa el botón **Conectar con Google (OAuth)**.
2. Autoriza el acceso cuando Google lo pida.
3. Tras autorizar, la app guarda un token y podrá escribir en la hoja cuyo ID configuraste.

Si en lugar de OAuth usas **cuenta de servicio** (JSON), asegúrate de que ese JSON esté guardado en la configuración y que la hoja **Papeletas_WhatsApp** esté compartida con el email de la cuenta de servicio (ej. `xxx@yyy.iam.gserviceaccount.com`) con permiso de **Editor**.

---

## 4. Comprobar

- Envía de nuevo una **foto de papeleta** por WhatsApp (flujo cobranza).
- Si todo está bien, en la hoja debería aparecer una **nueva fila** con: Cédula, Fecha, Nombre en cabecera (banco), Número depósito, Número de documento, Cantidad, HUMANO, Link imagen, Observación.
- En los **logs del backend** (Render) puedes buscar: `Sheets append_row OK` o `Sheets no configurado` / `google_sheets_id vacío` si algo falla.

---

## Resumen

| Qué | Dónde |
|-----|--------|
| ID de la hoja | URL: `docs.google.com/spreadsheets/d/`**ESTE_ID**`/edit` |
| Pegar el ID | Configuración → Informe pagos → **ID Google Sheet** |
| Pestaña | Opcional: **Pestaña donde escribir** = `Hoja 1` |
| Permiso para escribir | **Conectar con Google (OAuth)** o cuenta de servicio + compartir la hoja |
