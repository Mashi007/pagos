# Estado de cuenta público: flujo de inicio a fin

Documento de referencia del flujo **consulta pública de estado de cuenta** (URL: [https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta](https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta)). Sin login; solo validación por cédula y generación de PDF con envío al email del cliente.

---

## 1. Resumen del flujo (inicio → fin)

| Fase | Qué ocurre |
|------|------------|
| **Entrada** | Usuario abre la URL pública `/pagos/rapicredit-estadocuenta` (o `/rapicredit-estadocuenta` si la app tiene basename vacío). No requiere login. |
| **Paso 0** | Pantalla de bienvenida: texto explicativo y botón "Iniciar". |
| **Paso 1** | Usuario ingresa cédula (V/E/G/J + 6–11 dígitos). Frontend normaliza y llama `GET /api/v1/estado-cuenta/public/validar-cedula?cedula=...`. Si OK: se muestra nombre (opcional) y se pasa al paso 2. Si error: mensaje de validación o "cédula no registrada". |
| **Paso 2** | Al entrar en paso 2, el frontend llama automáticamente `POST /api/v1/estado-cuenta/public/solicitar-estado-cuenta` con `{ cedula }`. Backend: busca cliente por cédula, préstamos, cuotas pendientes (sin fecha_pago), tablas de amortización (préstamos APROBADOS/DESEMBOLSADOS), genera PDF, envía email si hay correo registrado, devuelve `pdf_base64` y mensaje. Frontend muestra el PDF en un iframe y opciones "Termina", "Consultar otra cédula", "Descargar PDF". |
| **Salida** | Usuario ve el PDF en pantalla, puede descargarlo y/o consultar otra cédula. El proceso termina siempre en PDF (visualización + descarga y, si hay email, envío al correo). |

---

## 2. Endpoints (prefijo base: `/api/v1/estado-cuenta/public`)

**Públicos, sin autenticación.** Rate limiting por IP.

| Método | Ruta | Descripción | Rate limit |
|--------|------|-------------|------------|
| **GET** | `/validar-cedula?cedula=...` | Valida formato de cédula (validadores) y verifica que exista en tabla `clientes`. Retorna `ok`, `nombre`, `email` (o `error`). | 30 req/min por IP |
| **POST** | `/solicitar-estado-cuenta` | Body: `{ "cedula": "V12345678" }`. Genera PDF (cliente, préstamos, cuotas pendientes, tablas de amortización), envía copia al email del cliente si está registrado, devuelve `ok`, `pdf_base64`, `mensaje`. | 5 req/hora por IP |

Respuestas 429: mismo mensaje que en frontend ("Demasiadas consultas..." / "límite de consultas por hora").

---

## 3. Procesos clarificados

### 3.1 Validación de cédula (validar-cedula)

1. Rate limit: 30/min por IP (`cobros_public_rate_limit.check_rate_limit_estado_cuenta_validar`).
2. Longitud cédula ≤ 20 caracteres.
3. Validación de formato con `validate_cedula` (validadores): formato V/E/G/J + dígitos; se obtiene `valor_formateado`.
4. Lookup en BD: `Cliente` donde `replace(cedula, '-', '') == cedula_lookup` (cédula normalizada sin guión).
5. Si no hay cliente: `ok=False`, error "no se encuentra registrada en nuestro sistema".
6. Si hay cliente: `ok=True`, `nombre` (nombres), `email`.

### 3.2 Solicitud de estado de cuenta (solicitar-estado-cuenta)

1. Rate limit: 5/hora por IP (`check_rate_limit_estado_cuenta_solicitar`).
2. Misma validación de cédula y mismo lookup a `Cliente`.
3. **Préstamos:** todos los `Prestamo` con `cliente_id == cliente.id`; se arma lista con id, producto, total_financiamiento, estado.
4. **Cuotas pendientes:** `Cuota` con `prestamo_id in (ids)` y `fecha_pago is None`; orden por prestamo_id, numero_cuota. Se calcula `total_pendiente`.
5. **Tablas de amortización:** solo para préstamos con estado `APROBADO` o `DESEMBOLSADO`. Por cada uno se llama `_obtener_amortizacion_prestamo(db, prestamo_id)` (todas las cuotas del préstamo con numero_cuota, fecha_vencimiento, monto_capital, monto_interes, monto_cuota, saldo_capital_final, estado).
6. **PDF:** `_generar_pdf_estado_cuenta(cedula, nombre, prestamos, cuotas_pendientes, total_pendiente, fecha_corte, amortizaciones_por_prestamo)`. Incluye: título, fecha de corte, cédula, cliente; tabla Préstamos; sección Cuotas pendientes y total; sección Tablas de amortización (por préstamo, misma estructura que en "Detalles del Préstamo").
7. **Email:** si el cliente tiene `email`, se envía el PDF adjunto con `send_email` (asunto "Estado de cuenta - {fecha}", cuerpo breve). Si falla el envío, se registra warning pero no se falla la petición; el PDF se devuelve igual.
8. Respuesta: `ok=True`, `pdf_base64=base64.encode(pdf_bytes)`, `mensaje` indicando si se envió al correo o no.

### 3.3 Seguridad

- Sin auth: solo se exponen datos del cliente identificado por la cédula consultada.
- No se exponen datos de otros clientes.
- Rate limits evitan abuso por IP.
- Cédula: validación de formato y existencia en BD antes de devolver datos.

---

## 4. Frontend (EstadoCuentaPublicoPage)

- **Ruta:** `rapicredit-estadocuenta` (con basename `/pagos` → URL final `/pagos/rapicredit-estadocuenta`).
- **Pasos:** 0 = bienvenida, 1 = ingresar cédula, 2 = resultado (PDF + mensaje + botones).
- **Normalización cédula:** quita espacios, guiones, puntos; solo V/E/G/J + 6–11 dígitos; si solo dígitos se antepone V. Se envía al API ya normalizada.
- **Paso 2:** al montar (step === 2 y cedula válida), se llama una sola vez a `solicitarEstadoCuenta(cedula)`; el PDF se muestra vía `data:application/pdf;base64,{pdf_base64}` en un iframe. Descarga con enlace `<a href={pdfDataUrl} download="estado_cuenta_....pdf">`.
- **Sesión pública:** se guarda `PUBLIC_FLOW_SESSION_KEY` y path `rapicredit-estadocuenta` para que, si el usuario intenta ir a login/sistema, se pueda mostrar "Acceso prohibido" y volver a esta consulta.

---

## 5. Mejoras / notas

- **Variable shadowing en backend:** en `solicitar_estado_cuenta`, el cuerpo del email se asigna a `body` (local), lo que oculta el parámetro `body: SolicitarEstadoCuentaRequest`. Funcionalmente correcto porque `body.cedula` ya se usó antes; por claridad se puede renombrar a `email_body` o `cuerpo_email`.
- **CSP e iframe PDF:** en producción, si el servidor devuelve Content-Security-Policy que restringe `data:` o frame-src, el iframe del PDF podría no cargar; el enlace de descarga sigue funcionando. Ver `docs/VERIFICACION_ESTADO_CUENTA_CSP_CSS.md` si aplica.
- **Tablas de amortización:** solo se incluyen para préstamos en estado APROBADO o DESEMBOLSADO; préstamos en otro estado no muestran tabla en el PDF (coherente con la lógica de "préstamo activo").

Este documento sirve como referencia única de inicio a fin para el flujo de estado de cuenta público y la URL [rapicredit-estadocuenta](https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta).
