# Adjuntos PDF fijos en Render

## Problema

Los correos envían el PDF variable (Carta_Cobranza.pdf) pero **no anexan los PDFs fijos** (Documentos PDF anexos por pestaña, ej. CUENTAS_RAPICREDIT.pdf).

## Causa

Los archivos subidos en **Configuración → Plantillas → Documentos PDF anexos** se guardan en el servidor en `uploads/adjuntos_fijos/` (o en la ruta indicada por `ADJUNTO_FIJO_COBRANZA_BASE_DIR`). En **Render el sistema de archivos es efímero**: todo lo escrito fuera del build se pierde en cada deploy o al reiniciar el servicio. La base de datos sí conserva la configuración (qué archivo va a cada pestaña), pero el archivo físico ya no está en disco, por eso el backend no puede adjuntarlo.

## Solución: disco persistente en Render

1. En el **Dashboard de Render**, abre el servicio **pagos-backend**.
2. En **Disks** (Discos), añade un **Persistent Disk**.
   - Nombre: p. ej. `adjuntos-fijos`
   - Montar en: `/data` (o la ruta que prefieras, p. ej. `/opt/render/project/data`).
3. Añade una **variable de entorno** en el servicio:
   - **Key:** `ADJUNTO_FIJO_COBRANZA_BASE_DIR`
   - **Value:** `/data/adjuntos_fijos` (o `<montar_en>/adjuntos_fijos`).
4. Redespliega el backend para que tome la variable y cree la carpeta al subir el primer PDF.

A partir de ahí, las subidas de la pestaña «Documentos PDF anexos» se guardan en ese disco y seguirán disponibles después de deploys y reinicios, y el envío de correos podrá adjuntar los PDFs fijos.

## Comprobar en logs

Tras desplegar, al enviar notificaciones:

- Si los adjuntos fijos **sí se cargan**, verás en logs:  
  `Adjuntos fijos caso dias_1_retraso: N archivo(s) anexados`
- Si **no** se cargan (ruta incorrecta o disco no montado), verás:  
  `Adjunto por caso ... no encontrado (en Render usar disco persistente). base_dir=... path=...`  
  y/o  
  `Adjuntos fijos caso ...: config tiene entradas pero ningun archivo encontrado. base_dir=...`

Revisa esos mensajes para confirmar que `base_dir` es la ruta del disco persistente que configuraste.
