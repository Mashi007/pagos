# Estado de cuenta público: flujo de inicio a fin

Documento de referencia del flujo **consulta pública de estado de cuenta** (URL: [https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta](https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta)). Sin login; validación por cédula y **código enviado al email** del cliente; tras verificar el código se genera y muestra/descarga el PDF.

Para auditoría con trazabilidad paso a paso, ver [AUDITORIA_ESTADO_CUENTA_PUBLICO_INTEGRAL.md](./AUDITORIA_ESTADO_CUENTA_PUBLICO_INTEGRAL.md). Para mejoras propuestas, ver [MEJORAS_ESTADO_CUENTA_PUBLICO.md](./MEJORAS_ESTADO_CUENTA_PUBLICO.md).

---

## 1. Resumen del flujo (inicio → fin)

| Fase | Qué ocurre |
|------|------------|
| **Entrada** | Usuario abre la URL pública `/pagos/rapicredit-estadocuenta`. No requiere login. |
| **Paso 0** | Pantalla de bienvenida: texto explicativo y botón "Iniciar". |
| **Paso 1** | Usuario ingresa cédula (V/E/G/J + 6–11 dígitos). Frontend normaliza y llama `POST /api/v1/estado-cuenta/public/solicitar-codigo` con `{ cedula }`. Backend valida cédula, busca cliente y email; si hay email, genera código de 6 dígitos, lo guarda en `estado_cuenta_codigos` y lo envía por correo. Respuesta siempre genérica (no revela si la cédula existe). Frontend pasa al paso 2. |
| **Paso 2** | Usuario ingresa el código de 6 dígitos recibido por email. Frontend llama `POST /api/v1/estado-cuenta/public/verificar-codigo` con `{ cedula, codigo }`. Backend verifica código (válido, no expirado, no usado), genera el PDF, marca el código como usado y devuelve `pdf_base64`. Frontend muestra el PDF en iframe y opciones "Terminar", "Consultar otra cédula", "Descargar PDF". |
| **Paso 3** | Usuario ve el PDF en pantalla, puede descargarlo y/o consultar otra cédula. |

---

## 2. Endpoints (prefijo base: `/api/v1/estado-cuenta/public`)

**Públicos, sin autenticación.** Rate limiting por IP.

| Método | Ruta | Descripción | Rate limit |
|--------|------|-------------|------------|
| **GET** | `/validar-cedula?cedula=...` | Valida formato y existencia en `clientes`. Retorna `ok`, `nombre`, `email` (o `error`). No usado en el flujo actual de la UI (la UI usa solicitar-codigo + verificar-codigo). | 30 req/min por IP |
| **POST** | `/solicitar-codigo` | Body: `{ "cedula": "V12345678" }`. Valida cédula; si el cliente tiene email, genera código 6 dígitos, lo persiste en `estado_cuenta_codigos` (expira en 2 h) y lo envía por email. Respuesta genérica. | 5 req/hora por IP |
| **POST** | `/verificar-codigo` | Body: `{ "cedula", "codigo" }`. Verifica código (no expirado, no usado), genera PDF, marca código usado, devuelve `pdf_base64`. | 15 intentos / 15 min por IP |
| **POST** | `/solicitar-estado-cuenta` | Body: `{ "cedula" }`. Flujo alternativo: genera PDF, envía al email, devuelve base64 (sin paso de código). No usado en la UI actual. | 5 req/hora por IP |

---

## 3. Procesos clarificados

### 3.1 Solicitar código (solicitar-codigo)

1. Rate limit: 5/hora por IP.
2. Validación de cédula (formato V/E/G/J + 6–11 dígitos) y lookup en `clientes` (cédula normalizada sin guión).
3. Si no hay cliente o no hay email: se responde `ok=True` con mensaje genérico (no se revela si la cédula existe).
4. Si hay email: se genera código de 6 dígitos, se guarda en `estado_cuenta_codigos` (expira en 2 h, `usado=False`), se envía por email y se responde con el mismo mensaje genérico. Si el envío del email falla, se registra warning pero la respuesta sigue siendo OK.

### 3.2 Verificar código (verificar-codigo)

1. Rate limit: 15 intentos / 15 min por IP.
2. Se busca en `estado_cuenta_codigos` una fila con la cédula normalizada, el código, `expira_en > now` y `usado == False`.
3. Si no hay fila: `ok=False`, "Código inválido o expirado. Solicite uno nuevo."
4. Si hay fila: se obtienen datos para el PDF (`_obtener_datos_pdf`: cliente, préstamos, cuotas pendientes, amortizaciones para APROBADOS/DESEMBOLSADOS), se genera el PDF con `generar_pdf_estado_cuenta`, se marca el código como usado (`usado=True`), se devuelve `pdf_base64`.

### 3.3 Seguridad

- Sin auth: solo se exponen datos del cliente identificado por la cédula; el código demuestra acceso al email del cliente.
- Código de un solo uso y expiración 2 h.
- Rate limits evitan abuso por IP.
- Mensajes genéricos en solicitar-codigo para no revelar si la cédula está registrada.

---

## 4. Frontend (EstadoCuentaPublicoPage)

- **Ruta:** `rapicredit-estadocuenta` (con basename `/pagos` → URL final `/pagos/rapicredit-estadocuenta`).
- **Pasos:** 0 = bienvenida, 1 = ingresar cédula y solicitar código, 2 = ingresar código, 3 = PDF (visualización + descarga).
- **Normalización cédula:** quita espacios, guiones, puntos; solo V/E/G/J + 6–11 dígitos; si solo dígitos se antepone V.
- **Paso 2:** el usuario escribe el código recibido por correo; al enviar se llama `verificarCodigo(cedula, codigo)`.
- **Paso 3:** el PDF se muestra vía blob URL o data URL en un iframe; la descarga usa blob URL cuando está disponible para evitar límites de longitud de data URL.
- **Sesión pública:** se guarda `PUBLIC_FLOW_SESSION_KEY` y path `rapicredit-estadocuenta` para restringir acceso a login/sistema y poder volver.

---

## 5. Notas

- **CSP e iframe PDF:** en producción, si el servidor devuelve Content-Security-Policy que restringe `data:` o frame-src, el iframe del PDF podría no cargar; el enlace de descarga sigue funcionando. Ver `docs/VERIFICACION_ESTADO_CUENTA_CSP_CSS.md` si aplica.
- **Tablas de amortización:** solo se incluyen para préstamos en estado APROBADO o DESEMBOLSADO.

Este documento sirve como referencia del flujo actual (código por email) para la URL [rapicredit-estadocuenta](https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta).
