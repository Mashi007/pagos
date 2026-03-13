# Auditoría: variables de plantillas conectadas a BD

Verificación de que **todas** las variables usadas en plantillas (email y PDF) tienen su valor desde la base de datos o derivados únicamente de BD (sin valores demo/placeholder en producción).

---

## 1. Plantilla cuerpo email (y asunto) – tipo COBRANZA

Motor: `render_plantilla_cobranza` en `backend/app/services/plantilla_cobranza.py`.  
Contexto: `construir_contexto_cobranza` (mismo módulo), rellenado por `build_contexto_cobranza_para_item` en `backend/app/api/v1/endpoints/notificaciones.py`.

| Variable | Origen (BD o derivado) |
|----------|------------------------|
| `{{CLIENTES.TRATAMIENTO}}` | `item.get("tratamiento")` (si existe en item) o `"Sr/Sra."`. **Nota:** La tabla `clientes` no tiene columna `tratamiento`; si se añade, basta incluirla en `format_cuota_item` y ya se usará aquí. |
| `{{CLIENTES.NOMBRE_COMPLETO}}` | `item["nombre"]` → `Cliente.nombres` (BD). |
| `{{CLIENTES.CEDULA}}` | `item["cedula"]` → `Cliente.cedula` (BD). |
| `{{PRESTAMOS.ID}}` / `{{IDPRESTAMO}}` | `item["prestamo_id"]` → `Cuota.prestamo_id` (BD). |
| `{{NUMEROCORRELATIVO}}` | `EnvioNotificacion` (BD): máximo por préstamo + lote actual. |
| `{{TOTAL_ADEUDADO}}` | Suma de montos de `cuotas_vencidas` (lista desde BD: Cuota sin pagar, vencida). |
| `{{FECHA_CARTA}}` | `date.today()` (fecha real del envío; no tabla, pero dato operativo). |
| `{{CUOTAS.VENCIMIENTOS}}` (bloque) / `{{TABLA_CUOTAS_PENDIENTES}}` | Lista de cuotas no pagadas y ya vencidas por préstamo (consulta Cuota en BD). |
| `{{CUOTA.NUMERO}}`, `{{CUOTA.FECHA_VENCIMIENTO}}`, `{{CUOTA.MONTO}}` | Dentro del bloque: cada elemento de esa lista (numero_cuota, fecha_vencimiento, monto desde Cuota). |
| `{{CUOTAS_VENCIDAS}}` | `len(cuotas_vencidas)` (derivado de lista desde BD). |
| `{{FECHAS_CUOTAS_PENDIENTES}}` | String de fechas de esas cuotas (derivado de BD). |
| `{{LOGO_URL}}` | `settings.FRONTEND_PUBLIC_URL` + ruta fija del logo (configuración; no tabla de negocio). |

---

## 2. Plantilla cuerpo email (y asunto) – tipo no COBRANZA / variables simples

Motor: `_sustituir_variables` en `backend/app/api/v1/endpoints/notificaciones.py`.  
Datos: `item` (por ítem de envío).

| Variable | Origen (BD o derivado) |
|----------|------------------------|
| `{{nombre}}` | `item["nombre"]` → `Cliente.nombres` (BD). |
| `{{cedula}}` | `item["cedula"]` → `Cliente.cedula` (BD). |
| `{{fecha_vencimiento}}` | `item["fecha_vencimiento"]` → `Cuota.fecha_vencimiento` (BD). |
| `{{numero_cuota}}` | `item["numero_cuota"]` → `Cuota.numero_cuota` (BD). |
| `{{monto}}` / `{{monto_cuota}}` | `item["monto_cuota"]` / `item["monto"]` → `Cuota.monto` (BD). |
| `{{dias_atraso}}` | `item["dias_atraso"]` (calculado desde Cuota.fecha_vencimiento vs hoy). |
| Cualquier otra `{{k}}` con `k` en `item` | `item` se construye con `format_cuota_item(Cliente, Cuota)` o equivalente desde `get_notificaciones_tabs_data` / `get_clientes_retrasados` (BD). |

---

## 3. Asunto/cuerpo por defecto (sin plantilla)

`asunto_default` y `cuerpo_default` se rellenan con `.format(nombre=..., cedula=..., fecha_vencimiento=..., numero_cuota=..., monto=...)`. Esos valores vienen del mismo `item` (Cliente + Cuota desde BD).

---

## 4. Plantilla anexo PDF

Motor: `_reemplazar_variables_plantilla_pdf` en `backend/app/services/carta_cobranza_pdf.py`.  
Diccionario de reemplazo: `_dict_reemplazo_pdf(contexto, datos)` con `datos = _datos_desde_contexto(contexto, plantilla_override)`.  
`contexto` es el mismo contexto de cobranza (construido desde ítem + BD).  
`plantilla_override` viene de configuración (clave `plantilla_pdf_cobranza`, tabla `configuracion`).

| Variable | Origen (BD o derivado) |
|----------|------------------------|
| `{{CIUDAD}}` / `ciudad` | `plantilla_override["ciudad_default"]` (configuración en BD) o por defecto `"Guacara"`. |
| `{{CLIENTES.TRATAMIENTO}}` | Contexto (desde item; si no, `"Sr/Sra."` o `"Sr(a)."`). |
| `{{CLIENTES.NOMBRE_COMPLETO}}` | Contexto → BD (Cliente.nombres). |
| `{{CLIENTES.CEDULA}}` | Contexto → BD (Cliente.cedula). |
| `{{PRESTAMOS.ID}}` / `{{IDPRESTAMO}}` | Contexto → BD (Cuota.prestamo_id). |
| `{{FECHA_CARTA}}` | Contexto (fecha real del envío). |
| `{{NUMEROCORRELATIVO}}` | Contexto → EnvioNotificacion (BD). |
| `{{TOTAL_ADEUDADO}}` | Contexto (suma cuotas desde BD). |
| `{{LOGO_URL}}` | Contexto (configuración frontend). |
| `monto_total_usd` | Suma de montos de cuotas del contexto (BD). |
| `num_cuotas` | `len(cuotas)` del contexto (BD). |
| `fechas_str` / `fechas_cuotas` | Fechas de cuotas del contexto (BD). |

---

## 5. Resumen de excepciones (no son tablas de negocio)

- **CLIENTES.TRATAMIENTO:** Si el ítem no trae `tratamiento`, se usa `"Sr/Sra."` porque la tabla `clientes` no tiene esa columna. El código ya usa `item.get("tratamiento")` cuando exista (p. ej. si en el futuro se añade la columna y se incluye en `format_cuota_item`).
- **LOGO_URL:** Viene de configuración (URL del frontend), no de una tabla de clientes/cuotas.
- **FECHA_CARTA:** Fecha del día del envío; dato operativo, no almacenado en BD.
- **CIUDAD (default):** Si no está en la configuración `plantilla_pdf_cobranza`, se usa `"Guacara"` por defecto; si está en configuración, viene de BD (tabla `configuracion`).

---

## 6. Conclusión

- **Todas** las variables que representan datos de cliente, préstamo, cuotas o envíos están conectadas a BD (tablas `clientes`, `cuotas`, `prestamos`, `envios_notificacion`, `configuracion` según corresponda).
- Las únicas “excepciones” son: valor por defecto de tratamiento (hasta que exista en BD), URL del logo (config), fecha de la carta (fecha de envío) y ciudad por defecto cuando no hay configuración. Ninguna usa datos demo o placeholders en producción.
