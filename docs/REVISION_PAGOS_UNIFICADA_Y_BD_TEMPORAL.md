# Revisión de pagos unificada y BD temporal

## Objetivo

Centralizar en una sola pantalla de `Pagos > Revisión` los casos que no pasan validadores y asegurar persistencia temporal de los comprobantes escaneados para revisión manual.

## Estado implementado

- Interfaz unificada:
  - Se eliminó la pestaña visible `Revision global`.
  - Todo acceso legacy `?pestana=revision-global` redirige internamente a `revision`.
  - Punto único operativo: `Pagos > Revisión`.

- Escáner individual y escáner lote:
  - Si Gemini no digitaliza, se crea borrador temporal y se devuelve `borrador_id`.
  - Si hay incumplimiento de validadores (`validacion_campos`, `validacion_reglas`) o duplicado, también se crea borrador temporal.
  - El flujo de frontend mantiene la revisión en la misma pestaña y permite continuar edición manual.

## BD temporal usada

Tabla temporal:

- `infopagos_escaner_borrador`

Modelo:

- `backend/app/models/infopagos_escaner_borrador.py`

Regla de persistencia:

- `backend/app/services/cobros/infopagos_escaner_borrador_service.py`
- función `debe_persistir_borrador_escaneo(...)`:
  - persiste cuando hay:
    - `duplicado_en_pagos == True`, o
    - `validacion_campos` con contenido, o
    - `validacion_reglas` con contenido.

Creación de borrador:

- `crear_borrador_escaneo(...)` guarda:
  - metadatos de cédula/usuario/cliente,
  - comprobante (vía `pago_comprobante_imagen`),
  - `payload_json` con sugerencia/validaciones/colisiones.

## Confirmación de cumplimiento

Se confirma que los pagos provenientes de:

- escaneo individual (`/cobros/escaner/extraer-comprobante`)
- escaneo lote (`/cobros/escaner/lote/drive-digitalizar`)

cuando no cumplen validadores o no digitalizan, quedan en BD temporal (`infopagos_escaner_borrador`) para revisión manual desde la pestaña unificada de `Pagos > Revisión`.

