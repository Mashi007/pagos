# Checklist operadores: huella funcional de pagos (anti-duplicado)

La **huella funcional** es la combinacion que la base de datos usa para evitar dos pagos
"iguales" en el mismo credito: **prestamo + fecha de pago (dia) + monto (USD en BD) +
referencia normalizada** (`ref_norm`). El sistema quita prefijos tipicos (BNC/, BINANCE/, VE/, etc.)
antes de comparar.

## Antes de cargar o editar

1. **Mismo comprobante, dos formatos**  
   No registrar dos filas si solo cambia el formato del texto, por ejemplo:
   - `BNC/101619796` y `101619796`
   - `VE/REF123` y `REF123`  
   En la practica cuentan como **la misma huella** y el segundo movimiento debe rechazarse o
   marcarse como duplicado/anulado segun politica contable.

2. **Numero de documento unico**  
   Sigue siendo obligatorio: dos pagos no pueden compartir el mismo `numero_documento` en toda la tabla.

3. **Carga masiva (Excel / lote)**  
   - No repita la misma huella en **dos filas del mismo archivo** (se valida antes de guardar).
   - Si una fila falla por huella, revise si ya existe un pago activo con la misma fecha, monto y
     referencia normalizada.

4. **Cobros / import desde reportados**  
   Misma regla: un lote de importacion comparte deteccion de huella duplicada entre filas del lote.

## Donde ver metricas

- **GET `/pagos/kpis`** incluye `calidad_carga_pagos_huella`:
  - `rechazos_409_huella_funcional_desde_arranque`: rechazos por API desde el ultimo reinicio del backend.
  - `prestamos_con_alerta_control_huella_funcional_duplicada`: prestamos con colision en BD (misma regla
    que auditoria cartera, control `pagos_huella_funcional_duplicada`).

## Si el usuario insiste en "son dos pagos distintos"

Deben diferir en algo que sobreviva a la normalizacion: por ejemplo **otro numero de operacion bancario
real** en `numero_documento` / referencia, o **otro dia** o **otro monto**. No basta con agregar o quitar
solo el prefijo `BNC/` si el resto es identico.
