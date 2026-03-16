# Diagnóstico: "No se pudo procesar el reporte. Intente de nuevo o contacte por WhatsApp 424-4579934."

## Dónde aparece el mensaje

- **URL**: `https://rapicredit.onrender.com/pagos/rapicredit-cobros`
- **Momento**: Al confirmar los datos y hacer clic en **"Sí, enviar"** en la pantalla "Confirma los siguientes datos".
- **Origen**: El backend responde con `ok: false` y `error: "No se pudo procesar el reporte..."`; el frontend muestra ese texto en el banner rojo.

---

## Dónde se genera en el código

| Capa | Archivo | Ubicación |
|------|---------|-----------|
| **Backend** | `backend/app/api/v1/endpoints/cobros_publico.py` | Endpoint `POST /api/v1/cobros/public/enviar-reporte`, bloque `except Exception as e` (aprox. líneas 388-393). |
| **Frontend** | `frontend/src/pages/ReportePagoPage.tsx` | Muestra `res.error` cuando `enviarReportePublico()` devuelve `ok: false`. |
| **Frontend** | `frontend/src/services/cobrosService.ts` | `enviarReportePublico()` llama al backend y devuelve la respuesta tal cual (incl. 429, 503 y body no JSON). |

Ese mensaje es **genérico**: se devuelve cuando **cualquier excepción no capturada** ocurre dentro del `try` del endpoint (después de validaciones y honeypot). El traceback real se registra con `logger.exception("[COBROS_PUBLIC] Error en enviar-reporte: %s", e)` en los logs del servidor.

---

## Flujo al hacer "Sí, enviar"

1. **Frontend**  
   - Construye `FormData` con: cédula, fecha, institución, monto, moneda, número de operación, archivo comprobante, honeypot.  
   - `POST` a `${API_URL}/api/v1/cobros/public/enviar-reporte`.  
   - Si la respuesta es JSON con `ok: false`, muestra `error` en el banner rojo.

2. **Backend** (`enviar_reporte_publico`)  
   - Rate limit (5 envíos/hora por IP).  
   - Honeypot: si `contact_website` tiene valor → responde `"No se pudo procesar el envío. Intente de nuevo."` (mensaje distinto al del título).  
   - Validaciones: cédula, cliente, préstamo, longitudes, moneda, monto, fecha, tamaño/tipo del archivo, magic bytes del comprobante.  
   - **Dentro del `try` (aquí cualquier fallo cae en el mensaje genérico):**  
     - Generar referencia interna (`_generar_referencia_interna`).  
     - Crear registro `PagoReportado` y `db.commit()`.  
     - Llamar a Gemini `compare_form_with_image()`.  
     - Si Gemini coincide: generar PDF (`generar_recibo_pago_reportado`), adjuntar y enviar email (`send_email`), actualizar estado a "aprobado".  
     - Si no coincide: estado "en_revision".  
     - Segundo `db.commit()`.  
     - Respuesta exitosa.  
   - Cualquier **excepción** en ese `try` → `db.rollback()` y respuesta con el mensaje:  
     **"No se pudo procesar el reporte. Intente de nuevo o contacte por WhatsApp 424-4579934."**

---

## Causas probables del error genérico

1. **Generación de referencia (`_generar_referencia_interna`)**  
   - Crea/usa la tabla `secuencia_referencia_cobros` con SQL crudo (PostgreSQL: `ON CONFLICT`, `RETURNING`, `TO_CHAR`, `SUBSTRING`).  
   - Si la tabla no existe en el entorno (p. ej. en Render no se ejecutó `sql/secuencia_referencia_cobros.sql` o equivalente), o hay error en el `INSERT ... RETURNING`, puede lanzar.  
   - Si la BD no es PostgreSQL, la sintaxis puede fallar.  
   - Si `.scalar_one()` no obtiene fila, también lanzaría.

2. **Gemini (`compare_form_with_image`)**  
   - Sin API key retorna un resultado por defecto (no lanza).  
   - Puede lanzar por: red, timeout, cuota/rate limit de la API, clave inválida en tiempo de ejecución, o error interno de `google.genai`.

3. **Generación del PDF (`generar_recibo_pago_reportado`)**  
   - Depende de `reportlab` y del logo en `backend/static/logo.png`.  
   - Fallos posibles: import, datos con caracteres problemáticos, o error al construir el PDF.

4. **Email (`send_email`)**  
   - Si en algún punto lanza (SMTP, configuración, destinatario), la excepción no está capturada y cae en el `except` genérico.

5. **Base de datos**  
   - Desconexión, timeout o constraint no manejado en el segundo `commit()` o en operaciones previas dentro del mismo `try`.

---

## Cómo ver la causa real

- En **Render** (o donde esté desplegado el backend): revisar los **logs del servicio** en el momento en que el usuario hace "Sí, enviar".  
- Buscar la línea:  
  `[COBROS_PUBLIC] Error en enviar-reporte: ...`  
  y el traceback que aparece debajo. Eso indica la excepción concreta (tabla faltante, Gemini, PDF, email, BD, etc.).

---

## Recomendaciones

1. **Asegurar que la tabla de secuencia exista en producción**  
   - Ejecutar en la BD de Render el script `sql/secuencia_referencia_cobros.sql` (o incluir esa tabla en una migración Alembic) para que `_generar_referencia_interna` no falle por tabla inexistente.

2. **Revisar variables de entorno en Render**  
   - `DATABASE_URL` correcta y accesible.  
   - `GEMINI_API_KEY` (y opcionalmente `GEMINI_MODEL`) si se usa validación con Gemini.  
   - Configuración de email (SMTP / servicio usado por `send_email`) para evitar excepciones al enviar el recibo.

3. **Mejorar diagnóstico en producción (opcional)**  
   - En el `except` del endpoint, además del mensaje genérico al usuario, seguir registrando el traceback completo con `logger.exception`.  
   - Opcional: en entorno de desarrollo/staging, devolver en el JSON un campo `debug_error` con el tipo o mensaje de la excepción (nunca en producción con datos sensibles).

Con esto se puede ver de forma integral por qué salen esos mensajes y actuar sobre la causa real (tabla, Gemini, PDF, email o BD) según lo que aparezca en los logs.
