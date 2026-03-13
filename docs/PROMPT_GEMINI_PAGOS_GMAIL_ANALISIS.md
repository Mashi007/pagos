# Análisis y ajuste del prompt Gemini (Pagos Gmail)

## Objetivo

Permitir que Gemini extraiga datos de pago **del asunto del correo, del cuerpo y de las imágenes/PDF descargados**, para organizar la información en el Excel sin ser restrictivo solo a "imagen de comprobante".

## Fuentes que analiza Gemini

1. **Asunto del correo (subject)** — a menudo incluye referencia, monto o identificación.
2. **Cuerpo del correo** — texto plano o HTML convertido a texto.
3. **Imágenes o PDF descargados** — comprobantes (recibo bancario, Pago Móvil, transferencia, etc.).

El prompt indica que extraiga de **cualquiera** de estas fuentes (asunto, cuerpo, imágenes o combinación).

## Cambios realizados

### 1. Prompt (`GEMINI_PROMPT` en `gemini_service.py`)

- Indica que puede recibir **una o más** de estas fuentes:
  1. El **ASUNTO** del correo (subject; a veces incluye referencia, monto o datos del pagador).
  2. El **CUERPO** del correo (texto plano o HTML convertido a texto).
  3. Una o más **imágenes o PDFs** (comprobantes).
- Instruye a extraer los 4 campos (**fecha_pago, cedula, monto, numero_referencia**) de **asunto, cuerpo, imágenes o combinación**.
- Aclara que el asunto a menudo contiene número de referencia, monto o identificación y debe usarse cuando el cuerpo o la imagen no lo tengan.
- Reglas por campo aplican a asunto, cuerpo e imágenes; pistas para texto (ej. "En asunto/cuerpo busca...").
- `'NA'` solo cuando el dato no aparece en **ninguna** de las fuentes.

### 2. Asunto y cuerpo en el pipeline

- **`get_message_body_text(payload)`** en `gmail_service.py`: obtiene el cuerpo desde el payload de Gmail (prefiere `text/plain`, si no hay usa `text/html` convertido a texto). Límite 15.000 caracteres.
- **Pipeline** (`pipeline.py`): por cada mensaje se tiene `subject` (asunto) y `body_text` (cuerpo) y se pasan a Gemini:
  - Si **no hay adjuntos**: se llama a `extract_payment_data(subject=..., body_text=...)` y se guarda una fila con lo extraído del asunto/cuerpo (o NA si no hay nada útil).
  - Si **hay adjuntos**: cada imagen/PDF se procesa con `extract_payment_data(file_content=..., filename=..., body_text=..., subject=...)` para que Gemini combine asunto + cuerpo + imagen.

### 3. Función `extract_payment_data`

- Acepta **parámetros opcionales**: `file_content`, `filename`, `body_text`, **`subject`**, `api_key`.
- Si se envía **solo asunto y/o cuerpo**: se hace una llamada solo con texto (asunto y cuerpo se envían en bloques "--- Asunto ---" y "--- Cuerpo ---").
- Si se envían **imagen + asunto/cuerpo**: `contents` = [prompt, bloque asunto+cuerpo, imagen]; Gemini puede usar las tres fuentes.
- Si solo se envían **imagen**: comportamiento previo (solo imagen).

## Resumen

- El prompt **no es restrictivo**: permite **asunto del correo + cuerpo + una o más imágenes/PDF**.
- Gemini analiza **asunto, cuerpo e imágenes descargadas** para rellenar **fecha_pago, cedula, monto, numero_referencia** en el Excel.
- Los datos se organizan en las mismas columnas del Excel; el origen puede ser asunto, cuerpo, imagen o cualquier combinación.
