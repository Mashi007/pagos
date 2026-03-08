# Revisión endpoints de carga masiva: Pagos, Préstamos, Clientes

## 1. PAGOS – POST /api/v1/pagos/upload

**Archivo:** `backend/app/api/v1/endpoints/pagos.py` (aprox. líneas 393-775)

**Conexión BD:** `db: Session = Depends(get_db)` y `current_user = Depends(get_current_user)`. OK.

**Tablas usadas:**
- **pagos** (Pago): inserciones de pagos válidos.
- **pagos_con_errores** (PagoConError): filas con error de validación.
- **prestamos** (Prestamo) y **clientes** (Cliente): validar cédula con múltiples préstamos (count).

**Validaciones:**
- Formato Excel: .xlsx/.xls, tamaño máx 10 MB, máx 10.000 filas (recomendado 2.500).
- Varios formatos de columnas (D: Cédula,Monto,Fecha,Doc; A/B/C alternativos).
- Documento: normalizado con `normalize_documento`; no duplicados en archivo ni en BD.
- Monto: _validar_monto (0.01 a máx NUMERIC).
- Si cédula tiene más de un préstamo, se exige prestamo_id.

**Transacción:** Un solo `db.commit()` al final; `db.rollback()` en except. OK.

**Corrección aplicada:** Se inicializaba `pagos_con_error_list` en FASE 2 pero se usaba en FASE 1 (append en filas con error). Se añadió `pagos_con_error_list: list[dict] = []` antes del bucle FASE 1 y se eliminó la reasignación en FASE 2 para no vaciar la lista.

**Nota:** Uso de `db.query(PagoConError)` en la respuesta (línea ~761). En SQLAlchemy 2 el patrón estándar es `db.execute(select(...))`; si el proyecto usa aún el estilo 1.x, no hay cambio necesario.

---

## 2. CLIENTES – POST /api/v1/clientes/upload-excel

**Archivo:** `backend/app/api/v1/endpoints/clientes.py` (aprox. líneas 636-812)

**Conexión BD:** `db: Session = Depends(get_db)` y `current_user = Depends(get_current_user)`. OK.

**Tablas usadas:**
- **clientes** (Cliente): inserciones de clientes válidos.
- **clientes_con_errores** (ClienteConError): filas con error de validación.

**Validaciones:**
- Excel: .xlsx/.xls.
- Cédula: V|E|J|Z + 6-11 dígitos, única en BD y en lote.
- Email: formato válido, único en BD y en lote.
- Nombres, dirección, ocupación, teléfono: requeridos.
- Fecha nacimiento: _parse_fecha.

**Datos previos:** Se cargan en memoria `cedulas_existentes` y `emails_existentes` con `db.execute(select(Cliente.cedula)).scalars().all()` y análogo para email. Correcto para lotes no gigantes.

**Transacción:** Un `db.commit()` al final; `db.rollback()` en except. OK.

**Sin cambios aplicados.**

---

## 3. PRÉSTAMOS – POST /api/v1/prestamos/upload-excel

**Archivo:** `backend/app/api/v1/endpoints/prestamos.py` (aprox. líneas 1469-1666)

**Conexión BD:** `db: Session = Depends(get_db)` y `current_user = Depends(get_current_user)`. OK.

**Tablas usadas:**
- **prestamos** (Prestamo): inserciones.
- **clientes** (Cliente): existencia de cédula y datos del cliente.
- **cuotas** (Cuota): generación por _generar_cuotas_amortizacion.
- **prestamos_con_errores** (PrestamoConError): filas con error.
- **revision_manual_prestamos**: _registrar_en_revision_manual.

**Validaciones:**
- Excel: .xlsx/.xls.
- Cédula: debe existir en BD (mapa clientes_cedulas).
- Monto > 0, modalidad MENSUAL|QUINCENAL|SEMANAL, número de cuotas 1-12, producto y analista requeridos.

**Transacción:** Un `db.commit()` al final; `db.rollback()` en except. OK.

**Sin cambios aplicados.**

---

## Resumen

| Endpoint | BD (get_db) | Tablas principales | Transacción | Observaciones |
|----------|-------------|---------------------|-------------|----------------|
| POST /pagos/upload | Sí | pagos, pagos_con_errores, prestamos, clientes | commit/rollback | Corregido init de pagos_con_error_list |
| POST /clientes/upload-excel | Sí | clientes, clientes_con_errores | commit/rollback | OK |
| POST /prestamos/upload-excel | Sí | prestamos, clientes, cuotas, prestamos_con_errores, revision_manual | commit/rollback | OK |
