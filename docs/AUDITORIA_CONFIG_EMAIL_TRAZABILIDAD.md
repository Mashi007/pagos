# Auditoría: Configuración de email – Trazabilidad paso a paso

## 1. Resumen ejecutivo

Hay **dos fuentes de verdad** en memoria para la config de email:

| Variable | Módulo | Uso |
|----------|--------|-----|
| `_email_config_stub` | `configuracion_email.py` | GET/PUT API, persistencia a BD, validación en POST /probar |
| `_current` | `email_config_holder.py` | `get_smtp_config()` → **envío real** en `send_email()` |

El envío (SMTP) **siempre** usa `_current` vía `get_smtp_config()`. La validación en POST /probar usaba `_email_config_stub`. Si no están sincronizados (p. ej. otro worker, o distinto orden de carga), se puede validar “OK” y fallar 535 al enviar.

---

## 2. Flujo PUT (guardar configuración)

```
Frontend (EmailConfig.tsx)
  → construye payload sin smtp_password/imap_password si *** o vacío
  → PUT /api/v1/configuracion/email/configuracion

configuracion_email.put_email_configuracion():
  1. _load_email_config_from_db(db)     → lee BD, rellena _email_config_stub (desencripta si hay _encriptado)
  2. data = payload.model_dump(exclude_none=True)
  3. Por cada k,v: si k in (smtp_password, imap_password) y _is_password_masked(v) → password_skipped=True, NO actualizar stub
  4. Resto de campos → _email_config_stub[k] = v
  5. validar_config_email_para_guardar(_email_config_stub)
  6. update_from_api(_email_config_stub) → copia a _current (holder)
  7. _persist_email_config(db)           → prepare_for_db_storage(_email_config_stub) → JSON → BD
```

**Trazabilidad contraseña en PUT:**

- Si el frontend envía `smtp_password` = `***` o vacío: backend **no** actualiza `_email_config_stub["smtp_password"]` (se mantiene lo que había en stub tras `_load_email_config_from_db`).
- Si el frontend envía contraseña real: se escribe en stub, luego en `_current` vía `update_from_api`, y en BD vía `prepare_for_db_storage`.
- `prepare_for_db_storage`: si `ENCRYPTION_KEY` está definida, encripta y guarda `smtp_password_encriptado` y pone `smtp_password = None` en el JSON. Si **no** hay clave, no encripta y deja la contraseña en claro en el JSON (riesgo de seguridad pero funciona).

---

## 3. Flujo GET (obtener configuración)

```
GET /api/v1/configuracion/email/configuracion

configuracion_email.get_email_configuracion():
  1. _load_email_config_from_db(db)  → BD → _email_config_stub (desencriptando si hay _encriptado)
  2. _sync_stub_from_settings()      → rellena desde .env si stub.smtp_user vacío
  3. out = _email_config_stub.copy()
  4. out["smtp_password"] = "***" si hay valor; out["imap_password"] = "***" si hay valor
  5. return out
```

La contraseña **nunca** se devuelve en claro; solo se usa en backend.

---

## 4. Flujo POST /probar (enviar email de prueba) – PUNTO CRÍTICO

```
POST /api/v1/configuracion/email/probar

configuracion_email.post_email_probar():
  1. _load_email_config_from_db(db)  → rellena _email_config_stub
  2. _sync_stub_from_settings()
  3. sync_from_db()                   → lee BD en holder y actualiza _current (email_config_holder)
  4. cfg = _email_config_stub        ← BUG: validación usa STUB
  5. Validación: cfg.get("smtp_host"), cfg.get("smtp_user"), cfg.get("smtp_password")
  6. send_email(...)                  → dentro usa get_smtp_config() → _current ← ENVÍO usa HOLDER
```

Problema: se valida con `_email_config_stub` pero se envía con `get_smtp_config()` = `_current`. Si por timing, worker distinto o fallo de desencriptación uno tiene contraseña y el otro no, se pasa la validación y falla 535.

Corrección: validar y comprobar destino con la **misma** config que se usa para enviar: `get_smtp_config()` (o al menos la misma fuente que usa `send_email`).

---

## 5. Flujo send_email (core/email.py)

```
send_email():
  1. sync_from_db()           → BD → _current (desencripta en holder)
  2. get_modo_pruebas_email()
  3. cfg = get_smtp_config()  → sync_from_db() de nuevo + return dict desde _current (o settings)
  4. server.login(cfg["smtp_user"], cfg["smtp_password"])
```

La contraseña usada en SMTP es **solo** la que está en `_current` después de `sync_from_db()`. Si en BD está encriptado y la desencriptación falla (sin o distinta `ENCRYPTION_KEY`), `_current["smtp_password"]` queda `None` o vacío → 535.

---

## 6. Carga desde BD: dos caminos

| Paso | _load_email_config_from_db (stub) | sync_from_db (holder) |
|------|-----------------------------------|------------------------|
| Lee | misma fila `configuracion` clave `email_config` | misma fila |
| Desencripta | por cada `*_encriptado`, desencripta y asigna a base_field | igual |
| Fallback | si no es _encriptado, asigna v a stub[k] | decrypted_data[field] = decrypted or data.get(field) |
| Escribe en | _email_config_stub | _current (vía update_from_api) |

Si la desencriptación falla en uno y no en el otro (no debería, mismo código), o uno se ejecuta antes que el otro en otro proceso, stub y holder pueden diferir.

---

## 7. Encriptación (app/core/crypto.py y holder)

- **Guardar:** `prepare_for_db_storage` → `_encrypt_value_safe(value, field)`. Si `ENCRYPTION_KEY` no está o es inválida, devuelve `None` → no se guarda `*_encriptado` y el valor en claro queda en el dict (y se persiste en claro).
- **Cargar:** se lee `*_encriptado` en hex, se desencripta. Si falla (clave distinta, token inválido), se usa `data.get(field)` (valor en claro legacy). Si solo hay `_encriptado` y falla la desencriptación, el campo queda `None` → 535.

Requisito: en producción, `ENCRYPTION_KEY` debe estar definida y ser la misma siempre. Tras cambiarla, volver a guardar la configuración de email (reingresar contraseña y guardar).

---

## 8. Hallazgos y correcciones aplicadas

1. **POST /probar valida con stub pero envía con holder**  
   Corrección: usar la config que devuelve `get_smtp_config()` para validar host, user y contraseña (y destino) en POST /probar, para que validación y envío usen la misma fuente.

2. **email_config_holder usa `logger` sin `import logging`**  
   Corrección: añadir `import logging` para evitar `NameError` si en el futuro se usa `logger` en ese módulo.

3. **Frontend**  
   Ya se construye el payload sin incluir `smtp_password`/`imap_password` cuando están vacíos o son `***`, para no sobrescribir en backend.

4. **Logs de diagnóstico**  
   En PUT: log con `password_skipped` y longitud de contraseña en stub (sin escribir la contraseña). En `send_email`: log de host, puerto, user y longitud de contraseña antes de `login`. Útil para ver en Render si la contraseña llega vacía en algún paso.

---

## 9. Checklist para 535 (Usuario o contraseña no aceptados)

- [ ] Gmail personal: usar **Contraseña de aplicación** (no la contraseña normal).
- [ ] Google Workspace: probar con contraseña normal.
- [ ] En Render: `ENCRYPTION_KEY` definida y estable; tras cambiarla, guardar de nuevo la config de email.
- [ ] Tras guardar con contraseña nueva, en logs: `smtp_password_len` > 0 en PUT y en `send_email`.
- [ ] POST /probar: validación y envío usan la misma config (get_smtp_config).
