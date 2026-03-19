# Auditoría: observación "NO CLIENTES" en Pagos Reportados

## Objetivo

Entender por qué un pago reportado puede mostrar **"NO CLIENTES"** cuando el titular **sí existe** en la tabla `clientes` (y tiene préstamo en `prestamos`). Caso de referencia: **Carlos Eduardo Sanchez Ferrer**, cédula **V20149164**.

---

## Flujo del backend (GET /pagos-reportados)

1. **Consulta paginada** a `pagos_reportados` → `rows` (solo la página actual).

2. **Construcción del set de cédulas “en clientes”:**
   - `cedulas_en_clientes = _cedulas_en_clientes_set(db)`
   - Se ejecuta `SELECT cedula FROM clientes` (todas las filas).
   - Por cada cédula:
     - Se normaliza con `_normalize_cedula_for_client_lookup` (sin guión/espacios, mayúsculas, sin ceros a la izquierda en el número: `V08752971` → `V8752971`).
     - Se añade esa forma al set.
     - Si la cédula normalizada es **solo dígitos** (ej. `20149164` o `020149164`), además se añaden al set:
       - el número sin ceros a la izquierda (`20149164`),
       - y la variante `V` + número (`V20149164`).

3. **Por cada fila de la página** (`rows`):
   - `raw_cedula = (tipo_cedula + numero_cedula)` sin guión/espacios, en mayúsculas.
   - `cedula_norm = _normalize_cedula_for_client_lookup(raw_cedula)`.
   - Si `cedula_norm` **no está** en `cedulas_en_clientes` → se añade la observación **"NO CLIENTES"**.

4. Las observaciones se devuelven en el JSON del listado y el frontend las muestra en la columna "Observación".

---

## Comprobaciones en BD (caso V20149164)

Con el script `sql/verificar_no_clientes_V20149164.sql` se confirmó:

| Comprobación | Resultado |
|--------------|-----------|
| ¿Existe en `clientes` con cédula V20149164? | Sí. id=15034, cedula='V20149164', nombres=Carlos Eduardo Sanchez Ferrer. |
| ¿Cédula normalizada (sin espacios/guiones)? | V20149164 (9 caracteres). |
| ¿Tiene préstamo en `prestamos`? | Sí. prestamo id=1616, cliente_id=15034, estado=APROBADO, cedula=V20149164. |
| ¿Email del cliente? | carlos_sanchez154@hotmail.com. |

Conclusión: **los datos en BD son correctos**. El cliente existe y la cédula está guardada como `V20149164`. El set `cedulas_en_clientes` debería incluir `V20149164` y la regla **no** debería marcar "NO CLIENTES" para ese reporte.

---

## Posibles causas si sigue apareciendo "NO CLIENTES"

1. **Backend en producción desactualizado**  
   La versión desplegada (ej. Render) no incluye el código que:
   - usa `_cedulas_en_clientes_set(db)` (set con todas las cédulas de `clientes` y variantes V+numero),
   - y normaliza con `_normalize_cedula_for_client_lookup`.  
   **Acción:** redesplegar el backend (commit actual con estos cambios).

2. **Cédula del reporte distinta en origen**  
   En `pagos_reportados` el registro podría tener `tipo_cedula`/`numero_cedula` que al concatenar no dan exactamente `V20149164` (espacios, guión, caracteres raros, encoding).  
   **Acción:** ejecutar en BD:
   ```sql
   SELECT id, referencia_interna, tipo_cedula, numero_cedula,
          (COALESCE(tipo_cedula,'') || COALESCE(numero_cedula,'')) AS cedula_completa
   FROM pagos_reportados
   WHERE numero_cedula LIKE '%20149164%' OR (tipo_cedula || numero_cedula) LIKE '%20149164%';
   ```
   Revisar que `cedula_completa` (tras quitar espacios/guiones) sea equivalente a `V20149164`.

3. **Cache o datos viejos en el frontend**  
   El listado podría estar mostrando una respuesta antigua.  
   **Acción:** recarga forzada (Ctrl+F5) o vaciar caché; volver a abrir la lista de pagos reportados.

---

## Logs de auditoría añadidos

En el backend se añadieron logs para diagnosticar en producción:

- **Al construir el set** (nivel DEBUG):  
  `[COBROS] pagos-reportados: cedulas_en_clientes set_size=X V20149164_in_set=True/False`

- **Cada vez que se marca "NO CLIENTES"** (nivel INFO):  
  `[COBROS] NO CLIENTES: ref=... tipo_cedula=... numero_cedula=... raw=... cedula_norm=... | set_size=... V20149164_in_set=...`

Tras desplegar, al cargar la lista de pagos reportados:

- Si `V20149164_in_set=False` → el set no contiene esa cédula (revisar conexión a BD, que sea la misma BD donde está el cliente 15034, o posible bug en `_cedulas_en_clientes_set`).
- Si `V20149164_in_set=True` y aun así sale el log "NO CLIENTES" para ese ref → la cédula del reporte (`cedula_norm` en el log) no coincide con la del set (revisar `tipo_cedula`/`numero_cedula` de ese registro en `pagos_reportados`).

---

## Resumen

- La **lógica actual** del backend es coherente con la BD: si en `clientes` está `V20149164`, el set incluye `V20149164` y no se debería mostrar "NO CLIENTES".
- Las causas más probables si sigue apareciendo son: **backend no redesplegado** o **cédula del reporte guardada con otro formato** en `pagos_reportados`.
- Los **logs** permiten ver en producción el tamaño del set, si `V20149164` está en el set y, para cada "NO CLIENTES", la cédula normalizada del reporte.
