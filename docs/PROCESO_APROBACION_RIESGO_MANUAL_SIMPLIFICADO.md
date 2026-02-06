# Proceso simplificado: Aprobación de riesgo manual

**Objetivo:** Sustituir el flujo actual (Evaluación 7 criterios + Aplicar condiciones + Asignar fecha) por un **único paso manual**: el aprobador revisa/edita datos del préstamo, ingresa la fecha de aprobación, confirma análisis de documentos y declaración de políticas, y el sistema guarda registrando quién aprobó y registra en auditoría.

---

## 1. Decisiones del usuario (definitivas)

| # | Pregunta | Respuesta |
|---|----------|-----------|
| 1 | Estado final del préstamo | **APROBADO** (luego puede existir paso "Desembolsar" por separado). |
| 2 | ¿Una o dos fechas? | **Una sola**: fecha de aprobación = fecha base para tabla de amortización. |
| 3 | Texto de la declaración | **Fijo** en frontend. |
| 4 | Quién puede aprobar | **Solo administración** (rol admin). |
| 5 | Datos editables | Los datos vienen del **formulario de nuevo crédito** al formulario de aprobación; **solo en este paso** se pueden editar (cuotas, monto de financiamiento, etc.). Incluye confirmación: "Se analizaron los documentos" (garantía de que alguien lo hizo). |
| 6 | Auditoría | Se guarda en **tabla de auditoría** (modulo=prestamos, accion=APROBACION_MANUAL). |

---

## 2. Proceso simplificado (diseño final)

### Flujo en una sola pantalla

1. **Desde la lista de Préstamos:** para préstamos en estado **DRAFT** o **EN_REVISION**, un solo botón **"Aprobar préstamo"** abre el formulario de aprobación (reemplaza "Evaluar riesgo", "Aprobar crédito" y "Asignar fecha").

2. **Modal "Aprobar préstamo (riesgo manual)":**
   - **Datos del préstamo (editables):** traídos del préstamo (formulario nuevo crédito). El aprobador puede modificar: monto de financiamiento, número de cuotas, modalidad de pago, cuota por periodo, tasa de interés.
   - **Fecha de aprobación** (obligatoria): una sola; se usa como fecha de aprobación y como base para la tabla de amortización.
   - **Checkbox:** "Confirmo que se analizaron los documentos del cliente."
   - **Checkbox (texto fijo):** "Al aprobar, usted asegura que el cliente cumple las políticas de RapiCredit y que su riesgo está dentro de parámetros normales."
   - **Botón "Guardar y aprobar"** (habilitado solo si fecha y ambos checkboxes están completos y datos válidos).

3. **Al guardar (backend):**
   - Actualizar préstamo con valores editados; `estado = 'APROBADO'`; `fecha_aprobacion` y `fecha_base_calculo` = misma fecha; `usuario_aprobador` = email del usuario actual.
   - Eliminar cuotas existentes (si hay) y generar tabla de amortización con datos actualizados.
   - **Registrar en tabla de auditoría:** modulo=prestamos, accion=APROBACION_MANUAL, registro_id=prestamo_id, usuario_email.

4. **Qué se retira o se oculta:** Evaluación de riesgo (7 criterios), Aplicar condiciones, Asignar fecha de aprobación. La nueva UI solo muestra "Aprobar préstamo" para DRAFT/EN_REVISION.

---

## 3. Backend

- **Endpoint:** `POST /api/v1/prestamos/{prestamo_id}/aprobar-manual`
- **Body:** `fecha_aprobacion` (date), `acepta_declaracion` (bool), `documentos_analizados` (bool), y opcionales para editar: `total_financiamiento`, `numero_cuotas`, `modalidad_pago`, `cuota_periodo`, `tasa_interes`, `observaciones`.
- **Lógica:** Validar estado DRAFT o EN_REVISION; validar ambos checkboxes; actualizar préstamo (campos editables + fechas + usuario_aprobador); borrar cuotas existentes y generar nuevas; insertar en tabla `auditoria`.
- Los endpoints antiguos (`evaluar-riesgo`, `aplicar-condiciones-aprobacion`, `asignar-fecha-aprobacion`) se mantienen por compatibilidad pero la nueva UI no los usa.

---

## 4. Frontend

- **Componente:** `AprobarPrestamoManualModal` con datos editables del préstamo, una fecha, dos checkboxes y botón "Guardar y aprobar".
- **Lista de préstamos:** para DRAFT y EN_REVISION un solo botón "Aprobar préstamo" que abre este modal (sustituye Evaluar riesgo, Aprobar crédito, Asignar fecha).
- Mostrar en detalle/lista quién aprobó y cuándo (`usuario_aprobador`, `fecha_aprobacion`).
