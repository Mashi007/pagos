# Investigación: descarga Excel Gmail (mensaje "Sin datos")

## Problema reportado

El usuario descargaba un Excel que en vez de contener datos de pagos mostraba solo el mensaje:

> "Sin datos para 2026-03-09. En la app: pulse «Generar Excel desde Gmail»..."

## Causas identificadas

### 1. Desajuste de fechas (principal)

- **Pipeline**: Guarda los ítems según la **fecha del correo** (header `Date`).
- **Descarga**: Usaba la **fecha actual en Caracas** (después de 23:50 se considera el día siguiente).

Cuando:
- Se ejecuta el pipeline a las 00:30 del 9 de marzo,
- Los correos procesados son del 8 de marzo,

los datos quedan en `Pagos_Cobros_8Marzo2026` pero la descarga pedía `9Marzo2026` → sin registros.

### 2. Excel vacío con mensaje

Ante la ausencia de datos, el backend generaba un Excel con una fila de instrucciones. La descarga se producía, pero el archivo no tenía datos útiles.

### 3. Posibles causas adicionales

- **Sin correos procesables**: Solo se consideran correos **no leídos** con adjuntos (imagen/PDF).
- **Credenciales / GEMINI_API_KEY**: OAuth o API Key mal configurados impiden procesar correos o extraer datos.

## Cambios realizados

### Backend (`pagos_gmail.py`)

1. **Fallback de fechas**: Si no hay datos para la fecha pedida, se buscan datos en los 3 días anteriores.
2. **404 en lugar de Excel vacío**: Si no hay datos en ninguna de esas fechas, se responde 404 con un mensaje claro en lugar de un Excel con instrucciones.
3. **Parámetro `fecha`**: Se mantiene el soporte para `?fecha=YYYY-MM-DD` para forzar una fecha concreta.

### Frontend (`pagoService.ts`)

1. **Tratamiento del 404**: Si la descarga responde 404, se muestra el mensaje del backend en el toast en vez de un genérico "Recurso no encontrado".
2. **Parámetro `fecha`**: `downloadGmailExcel(fecha?: string)` permite pasar una fecha al backend.

## Flujo actual

1. Usuario hace clic en «Generar Excel desde Gmail».
2. Pipeline ejecuta Gmail → Drive → Gemini → Sheets y guarda en BD.
3. Aparece el diálogo "¿Quiere borrar la información del día?"
4. Usuario elige Sí o No.
5. Se llama a `downloadGmailExcel()`:
   - Si hay datos (hoy o en los últimos 3 días): se descarga el Excel con los pagos.
   - Si no hay datos: toast con mensaje claro, sin descargar Excel.

## Requisitos para que haya datos

- Correos **no leídos** con adjuntos (imagen o PDF) o imágenes en el cuerpo.
- Credenciales OAuth de Gmail correctas (Configuración > Informe de pagos).
- `GEMINI_API_KEY` configurada en el servidor para extraer información de comprobantes.
