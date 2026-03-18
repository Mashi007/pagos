# Verificación: uso de `modalidad_pago` para generar tabla de amortización

**Fuente:** `backend/app/api/v1/endpoints/prestamos.py` (funciones `_resolver_monto_cuota`, `_generar_cuotas_amortizacion`, `_validate_modalidad_pago`).

---

## Valores permitidos de `modalidad_pago`

Solo se aceptan tres valores (validación en `_validate_modalidad_pago`):

| Valor       | Descripción |
|------------|-------------|
| **MENSUAL**   | 12 periodos al año, vencimiento cada 30 días |
| **QUINCENAL** | 24 periodos al año, vencimiento cada 15 días |
| **SEMANAL**   | 52 periodos al año, vencimiento cada 7 días |

Si `modalidad_pago` es `NULL` o vacío, se trata como **MENSUAL** (`(p.modalidad_pago or "MENSUAL").upper()`).

---

## 1. Cálculo del monto de cuota (`_resolver_monto_cuota`)

- **Tasa = 0 (o NULL):** cuota plana → `total / numero_cuotas`.
- **Tasa > 0:** amortización francesa. La tasa se guarda como **porcentaje anual** (ej. 12 = 12% anual). Se pasa a tasa por periodo según `modalidad_pago`:

  | modalidad_pago | periodos_por_anio | tasa_periodo        |
  |----------------|-------------------|----------------------|
  | MENSUAL        | 12                | tasa_anual / 12       |
  | QUINCENAL      | 24                | tasa_anual / 24       |
  | SEMANAL        | 52                | tasa_anual / 52       |

  Luego se usa `_calcular_monto_cuota_frances(total, tasa_periodo, numero_cuotas)`.

---

## 2. Fechas de vencimiento de cada cuota (`_generar_cuotas_amortizacion`)

La fecha de vencimiento de la cuota `n` es:

`fecha_base + (delta_dias * n - 1)` días.

`delta_dias` depende de `modalidad_pago`:

| modalidad_pago | delta_dias | Ejemplo (fecha_base = día 0)     |
|----------------|------------|-----------------------------------|
| **MENSUAL**    | 30         | Cuota 1 → día 29, Cuota 2 → día 59, … |
| **QUINCENAL**  | 15         | Cuota 1 → día 14, Cuota 2 → día 29, … |
| **SEMANAL**    | 7          | Cuota 1 → día 6, Cuota 2 → día 13, …  |

Código:

```python
modalidad = (p.modalidad_pago or "MENSUAL").upper()
delta_dias = 30 if modalidad == "MENSUAL" else (15 if modalidad == "QUINCENAL" else 7)
# ...
next_date = fecha_base + timedelta(days=delta_dias * n - 1)
```

---

## 3. Dónde se genera la tabla de amortización (cuotas)

La generación de cuotas (tabla de amortización) se hace siempre con `_generar_cuotas_amortizacion`, que usa `p.modalidad_pago` para `delta_dias` (y el monto de cuota viene de `_resolver_monto_cuota`, que también usa `modalidad_pago`). Se llama desde:

1. **POST `/{prestamo_id}/generar-amortizacion`** – Genera tabla si aún no hay cuotas.
2. **Aprobación manual** – Al aprobar con `AprobarManualBody` (incluye `modalidad_pago` opcional) se actualiza `p.modalidad_pago` si viene en el payload y luego se generan cuotas.
3. **POST `/generar-cuotas-aprobados-sin-cuotas`** – Genera cuotas para todos los aprobados que no tienen.
4. **Carga masiva Excel** – Cada préstamo creado con `modalidad_pago` del Excel; al final se generan cuotas con `_generar_cuotas_amortizacion`.
5. **Creación/actualización de préstamo** – Si queda en APROBADO y no tiene cuotas, se generan usando `modalidad_pago` del préstamo.

---

## Resumen

| Uso de `modalidad_pago` | Efecto |
|-------------------------|--------|
| **Monto de cuota (con interés)** | Define periodos por año (12 / 24 / 52) para convertir tasa anual a tasa por periodo en amortización francesa. |
| **Fechas de vencimiento** | Define el intervalo entre vencimientos: 30, 15 o 7 días (MENSUAL, QUINCENAL, SEMANAL). |
| **Default** | Si es NULL o vacío → se usa **MENSUAL** (30 días, 12 periodos/año). |

Valores no válidos (distintos de MENSUAL, QUINCENAL, SEMANAL) se rechazan en carga masiva y en validaciones que usan `_validate_modalidad_pago`; en el resto del código el fallback es MENSUAL.
