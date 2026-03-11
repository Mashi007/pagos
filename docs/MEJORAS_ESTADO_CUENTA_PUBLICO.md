# Mejoras propuestas: Estado de cuenta público (/pagos/rapicredit-estadocuenta)

Documento de mejoras para el flujo de consulta pública de estado de cuenta (código por email + PDF).

---

## 1. UX / Frontend

| # | Mejora | Prioridad | Estado |
|---|--------|-----------|--------|
| 1.1 | **Anuncio de paso 3 para lectores de pantalla**: Incluir en `stepAnnouncements` el paso 3 ("Estado de cuenta generado" o similar) para que el paso final sea anunciado. | Media | ✅ Implementado |
| 1.2 | **Descarga PDF con blob URL**: Usar `pdfBlobUrl` para el enlace de descarga cuando exista, en lugar de `pdfDataUrl`. Los data URLs muy largos pueden fallar en algunos navegadores o tener límites de longitud. | Media | ✅ Implementado |
| 1.3 | **Texto del botón**: Cambiar "Termina" por "Terminar" (infinitivo más natural en español para acciones). | Baja | ✅ Implementado |
| 1.4 | **"Reenviar código" en paso 2**: Añadir botón "¿No llegó el correo? Reenviar código" con cooldown (ej. 60 s) para no saturar rate limit y dar feedback claro. | Media | ✅ Implementado |
| 1.5 | **Mensajes de error más amigables**: Mapear 429/500 a textos concretos (ej. "Demasiados intentos. Espere X minutos." ya está; añadir mensaje genérico para fallos de red). | Baja | Propuesto |
| 1.6 | **Loading en paso 2**: Mostrar estado "Enviando código..." durante la llamada a `solicitarCodigo` (ya existe); en verificar, "Verificando..." (ya existe). Revisar que no parpadee el paso. | Baja | OK actual |

---

## 2. Backend / Seguridad

| # | Mejora | Prioridad | Estado |
|---|--------|-----------|--------|
| 2.1 | **Datetime con timezone**: Sustituir `datetime.utcnow()` por `datetime.now(timezone.utc)` (Python 3.12+ depreca `utcnow()`). | Media | ✅ Implementado |
| 2.2 | **Log de auditoría al enviar código**: Registrar con `logger.info` cuando el código se envía correctamente por email (sin datos sensibles: solo "código enviado para cédula terminada en ..." o similar). | Baja | ✅ Implementado |
| 2.3 | **Persistir código solo tras envío exitoso**: Hoy se hace `db.commit()` antes de `send_email`. Si el envío falla, el código queda en BD y el usuario no lo recibe. Opciones: (a) hacer commit después de enviar (si falla el commit tras enviar, el usuario podría recibir dos correos en un retry); (b) dejar como está y aceptar códigos "huérfanos". Ambas son válidas; (b) es más simple. | Baja | No implementado (decisión: mantener comportamiento actual) |
| 2.4 | **Rate limit distribuido**: Los límites están en memoria por proceso. Con varias instancias del backend (horizontal scaling), cada una lleva su propio contador. Para producción multi-instancia, valorar Redis o almacén compartido para rate limit. | Media | ✅ Implementado (Redis opcional; fallback memoria) |
| 2.5 | **Límite de códigos activos por cédula**: Evitar acumular muchos códigos no usados por la misma cédula (ej. máximo 3 códigos no expirados/no usados por cédula; al solicitar uno nuevo, invalidar los anteriores o no crear nuevo si ya hay uno reciente). | Baja | ✅ Implementado (max 3 activos; se eliminan los más viejos) |

---

## 3. Documentación

| # | Mejora | Prioridad | Estado |
|---|--------|-----------|--------|
| 3.1 | **Actualizar ESTADO_CUENTA_PUBLICO_FLUJO_COMPLETO.md**: El doc describe el flujo antiguo (validar-cedula + solicitar-estado-cuenta directo). Actualizar a flujo actual: solicitar-codigo → verificar-codigo → PDF. | Alta | ✅ Implementado |
| 3.2 | **Referencia cruzada**: En ese doc, enlazar a AUDITORIA_ESTADO_CUENTA_PUBLICO_INTEGRAL.md y a este de mejoras. | Baja | Propuesto |

---

## 4. Testing y calidad

| # | Mejora | Prioridad | Estado |
|---|--------|-----------|--------|
| 4.1 | **Tests E2E**: Flujo mínimo: abrir página → ingresar cédula → (mock o test env) solicitar código → ingresar código → ver PDF/descarga. | Media | ✅ Implementado (backend `tests/e2e_estado_cuenta_publico.py` con Playwright; frontend `tests/integration/test-estado-cuenta-publico.test.tsx`) |
| 4.2 | **Tests API**: Tests de integración para `POST solicitar-codigo` y `POST verificar-codigo` (con BD de test y mock de email). | Media | ✅ Implementado (`backend/tests/test_estado_cuenta_publico_api.py`) |

---

## 5. Resumen de implementaciones realizadas

- **Frontend:** Anuncio paso 3, descarga usando blob URL cuando existe, botón "Terminar".
- **Backend:** Uso de `datetime.now(timezone.utc)`, log info al enviar código correctamente.
- **Documentación:** ESTADO_CUENTA_PUBLICO_FLUJO_COMPLETO.md actualizado al flujo con código por email.

El resto de ítems quedan como propuestas para futuras iteraciones o cuando se disponga de infra (p. ej. Redis para rate limit).
