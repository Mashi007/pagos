# Auditoría integral del código generado (módulo Cobros, integración Pagos, validadores, BD, enlace /rapicredit)

**Fecha:** 2025-03-10  
**Alcance:** Código creado o modificado en las sesiones recientes (Cobros, reporte de pago público, Gemini, integración con Pagos, validadores formulario, conexión BD, link /rapicredit).

---

## 1. Resumen ejecutivo

| Área | Estado | Notas |
|------|--------|--------|
| Cobros público (reporte de pago) | ✅ | Rate limit, honeypot, validación archivo, Gemini 100% → aprobado/en_revision |
| Cobros admin (aprobar/rechazar) | ✅ | Mensaje rechazo genérico con WhatsApp 424-4579934 |
| Integración Cobros → Pagos | ✅ | Solo aprobados; mismas reglas carga masiva; Excel revisión |
| Validadores formulario | ✅ | Cédula VEGJ 6-11, monto, fecha calendario, archivo; notificaciones por error |
| Conexión BD y health | ✅ | Tablas críticas incl. pagos_reportados, usuarios; ENVIRONMENT seguro |
| Enlace /rapicredit | ✅ | Ruta y link canónico terminan en /rapicredit |
| Consistencia PagoConError | ✅ | Añadido referencia_pago en importar-desde-cobros |

---

## 2. Backend

### 2.1 Cobros público (`cobros_publico.py`)

- **Seguridad:** Sin auth; rate limit por IP (validar-cedula, enviar-reporte); honeypot `contact_website`; validación magic bytes del archivo; sanitización de nombre de archivo.
- **Validación:** Cédula con `validate_cedula` (V/E/G/J + 6-11 dígitos); monto > 0 y ≤ 999_999_999.99; fecha no futura; moneda BS/USD; longitudes institución y numero_operacion.
- **Flujo Gemini:** `compare_form_with_image` → si `coincide_exacto`: estado aprobado, PDF generado, guardado en BD, envío a `cliente.email`. Si no: estado `en_revision`.
- **BD:** `get_db` inyectado; consultas a Cliente, Prestamo, PagoReportado. Comprobante y recibo en columnas BYTEA.

### 2.2 Cobros admin (`cobros.py`)

- **Auth:** Router con `Depends(get_current_user)`.
- **Rechazo:** Mensaje genérico sin motivo técnico al cliente; texto fijo con WhatsApp 424-4579934 y enlace https://wa.me/584244579934 (constantes en `recibo_pdf.py`).
- **Aprobar:** Genera PDF, guarda en BD, envía a `pr.correo_enviado_a`.
- **Búsqueda cédula:** Variantes tipo+numero, solo numero, con/sin guión.

### 2.3 Pagos – Importar desde Cobros (`pagos.py`)

- **Endpoint:** `POST /api/v1/pagos/importar-desde-cobros` (auth requerida).
- **Reglas:** Solo `estado == "aprobado"`; documento = `referencia_interna` (único en BD y en lote); cédula → Cliente; 1 préstamo APROBADO/DESEMBOLSADO; monto ≥ 0.01.
- **Fallos:** Se guardan en `pagos_con_errores` con `observaciones = "Cobros (reportados aprobados)"` y `referencia_pago` asignado (corrección aplicada en esta auditoría).
- **Éxito:** Se crea `Pago` y se aplica `_aplicar_pago_a_cuotas_interno`.
- **Respuesta:** `registros_procesados`, `registros_con_error`, `errores_detalle`, `ids_pagos_con_errores`, `cuotas_aplicadas`, `mensaje`.

### 2.4 Health y BD

- **GET /api/v1/health/db:** Tablas críticas incluyen `pagos_reportados` y `usuarios`; si falta alguna, `status: "error"` y lista de faltantes.
- **GET /api/v1/health/detailed:** Conteos incluyen `pagos_reportados` y `usuarios`; `environment` con `getattr(settings, "ENVIRONMENT", None)` para evitar AttributeError.
- **Startup:** `import app.models` antes de `create_all` para registrar todos los modelos (incl. PagoReportado, User).

---

## 3. Frontend

### 3.1 Formulario público (`ReportePagoPage.tsx`)

- **Validadores alineados con backend:**
  - Cédula: `CEDULA_REGEX = /^[VEGJ]\d{6,11}$/i` (mismo que validadores backend).
  - Monto: > 0.01, ≤ 999_999_999.99; mensajes específicos.
  - Fecha: obligatoria, no futura, `input type="date"` (solo calendario).
  - Institución: obligatoria; si "Otros", max 100 caracteres.
  - Nº documento: obligatorio, max 100 caracteres.
  - Archivo: JPG/PNG/PDF, max 5 MB; mensajes por tipo/tamaño.
- **Notificaciones:** Toast por cada error en cada paso y en envío final.
- **Honeypot:** Campo oculto; si viene rellenado, no se envía.

### 3.2 Cobros – Listado y detalle

- Listado: filtros estado/fechas/cédula/institución; acciones Ver detalle, Cambiar estado, Enviar recibo.
- Detalle: para `en_revision` título "Revisión manual" y texto explicativo; mismos botones Aprobar / Rechazar (rechazo → correo genérico WhatsApp).

### 3.3 Pagos – Importar desde Cobros

- En "Agregar pago" → "Importar reportados aprobados (Cobros)" se llama a `POST /api/v1/pagos/importar-desde-cobros`.
- Si `registros_con_error > 0` se muestra aviso y botón "Descargar Excel en revisión pagos" (export de `pagos_con_errores` sin borrar).

### 3.4 Enlace /rapicredit

- **Rutas:** `reporte-pago` y `rapicredit` renderizan `ReportePagoPage`; ambas públicas.
- **Constante:** `PUBLIC_REPORTE_PAGO_PATH = 'rapicredit'` en `config/env.ts`.
- **Link en Cobros:** "Link formulario público" apunta a `{origin}{BASE_URL}/rapicredit` (termina en `/rapicredit`).

---

## 4. Seguridad y buenas prácticas

- No se exponen secretos en frontend; WhatsApp y enlaces en constantes/backend.
- Endpoints públicos (reporte, health db) sin token; rate limit y honeypot en reporte.
- Validación de archivo por contenido (magic bytes) además de Content-Type.
- Cédula y documentos normalizados; sin inyección en nombres de archivo.

---

## 5. Posibles mejoras (no bloqueantes)

- **Cédula en BD:** Si en tabla `clientes` coexisten formatos con y sin guión, valorar normalizar en una única forma para todas las búsquedas (hoy cobros y importar usan sin guión).
- **Idioma de mensajes:** Algunos textos de validación están en español; mantener criterio único si se i18n.
- **Tests:** Añadir tests unitarios o de integración para: validar cédula pública, envío reporte (mock Gemini), importar-desde-cobros (reglas y PagoConError).

---

## 6. Correcciones aplicadas durante la auditoría

- En `importar_reportados_aprobados_a_pagos` se asigna `referencia_pago` en todos los `PagoConError` creados (consistencia con `pagos_con_errores` y uso en Revisar Pagos).

---

## 7. Conclusión

El código generado cumple los requisitos funcionales y de seguridad revisados. La auditoría no encontró errores críticos; se aplicó una corrección de consistencia (referencia_pago en PagoConError). Se recomienda desplegar y monitorear en entorno de staging antes de producción.
