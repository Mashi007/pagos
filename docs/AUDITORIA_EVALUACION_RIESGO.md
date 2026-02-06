# Auditoría integral: Evaluación de Riesgo

**Componente:** `EvaluacionRiesgoForm.tsx`  
**Endpoints:** `POST /api/v1/prestamos/{id}/evaluar-riesgo`, `GET /api/v1/prestamos/{id}/evaluacion-riesgo`  
**Alcance:** Flujo frontend–backend, persistencia de criterios y resultado, UX, permisos y datos reales.  
**Fecha:** 2025-02-05.

---

## 1. Resumen ejecutivo

El módulo de **Evaluación de Riesgo** incluye un formulario frontend con 7 criterios (capacidad de pago, estabilidad laboral, referencias, arraigo, perfil sociodemográfico, edad, capacidad de maniobra), validación por secciones, bloqueo por mora y una vista de “Resultado” que espera puntuación, clasificación, sugerencias y predicción ML. La auditoría detecta una **desconexión crítica** entre frontend y backend: el frontend envía decenas de campos de criterios y espera una respuesta con puntuación y sugerencias; el backend solo acepta 4 campos opcionales (ML manual y estado) y devuelve el préstamo actualizado. No se persisten los criterios ni se calcula puntuación en backend; la pestaña Resultado muestra datos indefinidos y el estado del préstamo no pasa a EVALUADO salvo que se envíe explícitamente. Se recomienda alinear contrato (backend que calcule y devuelva resultado o frontend que calcule y envíe resumen + estado) y corregir obtención de cliente para edad y uso de filtros.

---

## 2. Arquitectura actual

| Capa | Detalle |
|------|--------|
| **Entrada** | Préstamos → botón “Evaluar riesgo” (calculadora) en préstamos DRAFT o EN_REVISION. Solo visible si `canViewEvaluacionRiesgo()` (rol administrador). |
| **Formulario** | `EvaluacionRiesgoForm`: 7 secciones (criterios), validación “todas completas”, confirmación con `window.confirm`, envío vía `prestamoService.evaluarRiesgo(prestamo.id, datosEvaluacion)`. |
| **Backend** | `POST /prestamos/{prestamo_id}/evaluar-riesgo` con body `EvaluarRiesgoBody`; `GET /prestamos/{prestamo_id}/evaluacion-riesgo` devuelve campos ML del préstamo. |

---

## 3. Contrato API vs uso real

### 3.1 Body que acepta el backend

```text
EvaluarRiesgoBody:
  ml_impago_nivel_riesgo_manual: Optional[str]
  ml_impago_probabilidad_manual: Optional[float]
  requiere_revision: Optional[bool]
  estado: Optional[str]
```

El backend **solo** actualiza en el préstamo: `ml_impago_nivel_riesgo_manual`, `ml_impago_probabilidad_manual`, `requiere_revision`, `estado`. No recibe ni persiste criterios (ingresos, referencias, edad, etc.) ni calcula puntuación.

### 3.2 Body que envía el frontend

El frontend envía `datosEvaluacion` con todos los criterios del formulario, por ejemplo:

- Criterio 1: `ingresos_mensuales`, `gastos_fijos_mensuales`, `otras_deudas`
- Criterio 2: `meses_trabajo`, `tipo_empleo`, `sector_economico`
- Criterio 3: `referencia1_observaciones`, `referencia1_calificacion`, … (3 referencias)
- Criterio 4: `familia_cercana`, `familia_pais`, `minutos_trabajo`
- Criterio 5: `tipo_vivienda_detallado`, `zona_urbana`, … (múltiples campos)
- Criterio 6: `edad`
- (Criterio 7 se calcula por backend en la lógica esperada; actualmente no se envía explícitamente)

**Conclusión:** El backend ignora todos esos campos (no forman parte del schema). Con Pydantic por defecto, no se produce 422; la petición puede ser 200 pero el body efectivo usado son solo los 4 campos anteriores, que el frontend **no** está enviando. Por tanto no se actualiza nivel/probabilidad ML ni `estado`, y el préstamo queda en DRAFT/EN_REVISION.

### 3.3 Respuesta que devuelve el backend

`POST .../evaluar-riesgo` devuelve **`PrestamoResponse`** (id, cliente_id, total_financiamiento, estado, concesionario, modelo, analista, fechas, etc.). No devuelve ningún objeto de “resultado de evaluación” (puntuación, clasificación, sugerencias, detalle por criterio, ML).

### 3.4 Respuesta que espera el frontend

Tras `evaluarRiesgo(prestamo.id, datosEvaluacion)` el frontend hace `setResultado(response)` y usa `resultado` en la pestaña “Resultado” para mostrar:

- `resultado.puntuacion_total` (ej. X/100)
- `resultado.clasificacion_riesgo` (A–E)
- `resultado.decision_final`
- `resultado.sugerencias` (tasa_interes_sugerida, plazo_maximo_sugerido, enganche_minimo_sugerido)
- `resultado.requisitos_adicionales`
- `resultado.prediccion_ml` (riesgo_level, confidence, recommendation, modelo_usado)
- `resultado.detalle_criterios` (puntos por criterio)

Como `response` es el préstamo, **todos estos campos son undefined**. La UI muestra “0 / 100”, clasificación vacía, sugerencias vacías, etc. El mensaje de éxito (“El préstamo ahora está en estado EVALUADO”) tampoco se cumple porque no se envía `estado: 'EVALUADO'`.

---

## 4. Flujo de datos y persistencia

- **Criterios de evaluación:** No se guardan en BD. El backend no tiene tabla ni campos para “evaluación 100 puntos” (solo columnas ML en `prestamos`).
- **Puntuación / clasificación:** No se calculan en backend; el frontend espera que las devuelva la API, por lo que nunca se muestran valores reales.
- **Estado del préstamo:** Para que pase a EVALUADO habría que enviar `estado: 'EVALUADO'` en el body. El frontend no lo envía, por lo que el estado no cambia tras “evaluar”.
- **GET evaluacion-riesgo:** Devuelve solo campos ML del préstamo (nivel/probabilidad manual y calculada, requiere_revision). No devuelve puntuación ni criterios porque no existen en el modelo.

---

## 5. Cálculo de edad del cliente

El formulario obtiene la edad desde la fecha de nacimiento del cliente:

- Llama a `clienteService.getClientes({ cedula: prestamo.cedula })`.
- El listado de clientes en backend usa el parámetro **`search`** (no `cedula`) para filtrar por cédula/nombres/email/teléfono.
- Si el frontend solo envía `cedula` en filters, el backend puede no aplicar filtro por cédula (según implementación del endpoint), con lo que `response.data[0]` podría ser un cliente cualquiera y la edad calculada sería incorrecta.
- **Recomendación:** Usar `getClientes({ search: prestamo.cedula })` para que el backend filtre, o que el backend acepte un parámetro `cedula` (exact match) y usarlo aquí.

---

## 6. Permisos y visibilidad

- El formulario se muestra solo si `usePermissions().isAdmin` es true (`if (!isAdmin) return null`). Coincide con “solo administrador puede evaluar riesgo”.
- En lista de préstamos el botón “Evaluar riesgo” se muestra con `canViewEvaluacionRiesgo()` y estados DRAFT o EN_REVISION. Correcto.

---

## 7. Validaciones y reglas de negocio en frontend

- Se exige que las 7 secciones estén “completas” según reglas (ingresos > 0, referencias con observaciones y calificación, edad > 0 desde cliente, etc.). Coherente con un score de 100 puntos.
- Si `resumenPrestamos` indica cuotas en mora (`total_cuotas_mora > 0`), se muestra bloqueo y no se permite evaluar. Correcto.
- Confirmación antes de enviar con `window.confirm` (texto con caracteres corruptos “âš ï¸”, “âœ“”). Debería sustituirse por modal accesible y corregir encoding.

---

## 8. UX y accesibilidad

- Uso de `window.confirm` para la declaración previa a la evaluación: poco accesible; mejor un modal con botones claros.
- Caracteres corruptos en el texto de confirmación y en la pestaña Resultado (“ðŸ"‹”, “ðŸ“Š”).
- Cierre automático del formulario a los 2 segundos tras “éxito” puede cortar la lectura del resultado; el usuario no llega a ver una pantalla de resultado útil porque además `resultado` está vacío de contenido real.
- Formulario largo con muchas secciones; la navegación por pestañas y el indicador de sección actual ayudan, pero no hay cálculo de puntuación en cliente ni en servidor, por lo que la experiencia de “ver resultado” está rota.

---

## 9. Resumen de hallazgos

| Severidad | Hallazgo |
|-----------|----------|
| **Crítica** | El backend no recibe los criterios ni calcula puntuación; devuelve el préstamo. El frontend interpreta esa respuesta como “resultado” y muestra undefined/0 en toda la pestaña Resultado. |
| **Crítica** | No se envía `estado: 'EVALUADO'`, por lo que el préstamo no cambia de estado tras la evaluación. |
| **Alta** | Los criterios de evaluación (30+ campos) no se persisten en ninguna tabla; no hay trazabilidad ni re-evaluación desde datos guardados. |
| **Alta** | Obtención de cliente para edad: filtro por cédula puede no aplicarse si el backend solo usa `search`; conviene alinear parámetro (search vs cedula). |
| **Media** | Confirmación con `window.confirm` y encoding en textos (confirmación y títulos de resultado). |
| **Media** | GET evaluacion-riesgo solo devuelve campos ML del préstamo; no hay endpoint que devuelva “última evaluación 100 puntos” porque no se guarda. |

---

## 10. Recomendaciones prioritarias

### Opción A: Backend calcula y devuelve resultado (recomendada si se quiere un solo lugar de verdad)

1. **Nuevo contrato para `POST .../evaluar-riesgo`:**
   - Aceptar en el body todos los criterios que hoy envía el frontend (o un schema estable que los represente).
   - En el servidor: calcular puntuación por criterio, puntuación total, clasificación (A–E), decisión (APROBADO/RECHAZADO/CONDICIONADO), sugerencias (tasa, plazo, enganche).
   - Persistir en el préstamo al menos: `estado = 'EVALUADO'`, opcionalmente `ml_impago_nivel_riesgo_manual` / `ml_impago_probabilidad_manual` derivados de la clasificación, y si existe modelo ML, llamarlo y guardar también predicción.
   - Opcional: tabla `evaluacion_riesgo` (prestamo_id, fecha, criterios JSON, puntuacion_total, clasificacion, sugerencias JSON, usuario_id) para historial.
   - Respuesta: objeto “resultado” con `puntuacion_total`, `clasificacion_riesgo`, `decision_final`, `sugerencias`, `detalle_criterios` (y `prediccion_ml` si aplica), además de poder devolver el préstamo actualizado.

2. **Frontend:** Mantener envío de `datosEvaluacion` y usar la nueva respuesta para `setResultado(...)`; enviar explícitamente `estado: 'EVALUADO'` solo si el backend no lo fija ya.

### Opción B: Frontend calcula y backend solo persiste resumen + estado

1. **En el frontend:** Implementar la lógica de los 100 puntos (por criterio), clasificación A–E y sugerencias en JavaScript/TypeScript. Antes de llamar a la API, calcular `puntuacion_total`, `clasificacion_riesgo`, `sugerencias`, `detalle_criterios`.

2. **Payload al backend:** Incluir en el body al menos: `estado: 'EVALUADO'`, y opcionalmente `ml_impago_nivel_riesgo_manual` / `ml_impago_probabilidad_manual` mapeados desde la clasificación. Opcional: enviar un resumen (puntuación, clasificación, sugerencias) en un campo JSON para que el backend lo persista (nueva columna o tabla).

3. **Resultado en pantalla:** Usar el objeto calculado en frontend para `setResultado(...)` y mostrar la pestaña Resultado con datos reales, sin depender de la respuesta del backend para puntuación/sugerencias.

4. **Backend:** Aceptar en `EvaluarRiesgoBody` (o en un DTO ampliado) al menos `estado` y, si se desea persistir resumen, un campo opcional de resultado (por ejemplo `resultado_evaluacion: Optional[dict]`). Seguir devolviendo el préstamo actualizado; el frontend ya no dependerá de que la respuesta traiga puntuación.

### Comunes a ambas opciones

5. **Edad del cliente:** Usar `getClientes({ search: prestamo.cedula })` o que el backend exponga `cedula` en el listado y usarlo aquí; validar que `response.data[0]` corresponda al cliente del préstamo (por ejemplo por cedula).

6. **Confirmación:** Sustituir `window.confirm` por un modal (Dialog) con el texto de declaración y botones “Cancelar” / “Proceder”.

7. **Encoding:** Corregir caracteres en strings de confirmación y en títulos de la pestaña Resultado (UTF-8, reemplazo de secuencias corruptas).

8. **GET evaluacion-riesgo:** Si se persiste resultado de evaluación (opción A con tabla o campo JSON), ampliar este endpoint para devolver la última evaluación (puntuación, clasificación, sugerencias) además de los campos ML actuales.

---

## 11. Verificación rápida

- Tras enviar el formulario con todos los criterios completos: comprobar en red que el body incluye todos los campos; comprobar que la respuesta es 200 y que el cuerpo es un objeto préstamo (sin puntuacion_total ni sugerencias).
- En la UI: comprobar que la pestaña “Resultado” muestra “0 / 100” y clasificación/sugerencias vacías.
- En BD: ver que el préstamo no cambia a EVALUADO si no se envía `estado`.
- Tras implementar una de las opciones anteriores: verificar que el estado pasa a EVALUADO y que la pantalla Resultado muestra puntuación y sugerencias coherentes con los criterios.

---

## 12. Conclusión

El módulo de **Evaluación de Riesgo** tiene un frontend rico en criterios y validaciones, pero el backend actual no procesa esos criterios ni devuelve un resultado de evaluación; solo permite actualizar 4 campos opcionales del préstamo. Eso deja la pantalla de resultado sin datos reales y el préstamo sin pasar a EVALUADO. Para que el flujo sea útil es necesario o bien que el backend calcule y devuelva (y opcionalmente persista) el resultado de la evaluación (opción A), o bien que el frontend calcule el resultado y envíe estado (y opcionalmente resumen) para persistir (opción B), además de corregir filtro de cliente para edad, confirmación y encoding.
