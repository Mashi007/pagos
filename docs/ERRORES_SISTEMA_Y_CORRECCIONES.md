# Errores en el sistema y correcciones

Resumen de los problemas detectados y acciones tomadas/recomendadas.

---

## 1. Tests backend que fallaban (corregidos)

### Problema
- `test_post_probar_email_con_smtp_mock_ok`: el test hacía `@patch("app.api.v1.endpoints.configuracion_email.send_email")`, pero `send_email` se importa **dentro de la función** desde `app.core.email`, no está como atributo del módulo.
- `test_post_probar_imap_mock_ok` y `test_post_probar_imap_mock_fallo`: igual con `test_imap_connection`, importado desde `app.core.email` dentro del endpoint.

### Corrección aplicada
En `backend/tests/test_config_email_fases.py` se cambió el objetivo del patch:

- `app.api.v1.endpoints.configuracion_email.send_email` → **`app.core.email.send_email`**
- `app.api.v1.endpoints.configuracion_email.test_imap_connection` → **`app.core.email.test_imap_connection`**

Con esto los tres tests deberían pasar.

---

## 2. Codificación de caracteres (UTF-8 / mojibake)

### Síntomas
- En la UI: "**Ãšltimo Mes**" en lugar de "**Último Mes**" (y otros textos con tildes/ñ).
- En logs del backend: "Configuracin", "Conexin bsica", "Envo", "cdigos", "Campaas", "cach" (ó, í, á, ñ, é interpretados mal).

### Causa
Texto en UTF-8 interpretado como Latin-1 (ISO-8859-1), o viceversa, en algún punto de la cadena (navegador, servidor, consola, BD).

### Acciones recomendadas

1. **Frontend (HTML)**  
   En `frontend/index.html` (o el HTML principal) asegurar en el `<head>`:
   ```html
   <meta charset="utf-8">
   ```

2. **Backend (FastAPI)**  
   - Respuestas JSON con cabecera: `Content-Type: application/json; charset=utf-8`.
   - Si usas `JSONResponse`, configurar `media_type` con charset o que el servidor (p. ej. Uvicorn) sirva UTF-8 por defecto.

3. **Consola / logs (Windows)**  
   Los caracteres raros en la consola suelen ser solo de visualización. Para ver bien tildes y ñ en PowerShell:
   ```powershell
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   chcp 65001
   ```
   O ejecutar pytest con salida UTF-8 si tu IDE/terminal lo permite.

4. **Base de datos**  
   - Conexión con charset UTF-8 (p. ej. en MySQL: `?charset=utf8mb4` en la URL).
   - Tablas/columnas con collation UTF-8.

5. **Archivos fuente**  
   - Guardar todos los `.py`, `.tsx`, `.ts`, `.json` y plantillas en **UTF-8** (con BOM solo si el equipo lo requiere).

---

## 3. Frontend: avisos de build (Vite)

### Observado
- Módulos importados tanto estática como dinámicamente (p. ej. `errors.ts`, `analistaService.ts`, `concesionarioService.ts`, `modeloVehiculoService.ts`, `excelValidation.ts`, `exceljs.ts`): "dynamic import will not move module into another chunk".
- Chunk principal > 500 kB: recomendación de code-splitting o `manualChunks`.

### Impacto
No son errores; el build termina correctamente. Afectan sobre todo a tamaño de bundles y carga inicial.

### Recomendación
- Unificar criterio: o bien import estático o bien dinámico por módulo, para que Vite pueda hacer chunk splitting donde interese.
- En `vite.config.ts` valorar `build.rollupOptions.output.manualChunks` para partir el bundle grande (p. ej. por rutas o por librerías pesadas).

---

## 4. Pytest: opción desconocida

### Mensaje
`PytestConfigWarning: Unknown config option: timeout`

### Causa
En `pytest.ini` (o `pyproject.toml`) está definida la opción `timeout`, pero el plugin `pytest-timeout` no está instalado o no está activo.

### Solución
- Instalar el plugin: `pip install pytest-timeout`
- O quitar la opción `timeout` de la config de pytest si no quieres usar timeouts.

---

## 5. Resumen de estado

| Área              | Estado        | Acción                          |
|-------------------|---------------|----------------------------------|
| Build frontend    | OK (con avisos)| Opcional: chunks e imports      |
| Tests backend     | 3 tests corregidos (patch path) | Ejecutar suite completa para confirmar |
| Codificación UI  | Errores tipo "Ãš" | Revisar charset HTML, API y BD  |
| Codificación logs| Caracteres raros en consola | UTF-8 en terminal/consola       |

Si quieres, el siguiente paso puede ser revisar contigo un archivo concreto (por ejemplo donde sale "Último Mes") o el `index.html` del frontend para dejar UTF-8 bien cerrado.
