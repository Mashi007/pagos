# Verificación: compatibilidad con estado de cuenta (CSP, CSS, XHR)

## Resumen

Los **endpoints y el flujo antiguos** son **compatibles** con la solución que añade la tabla de amortización al PDF. Los avisos que ves (CSS “mal selector” y bloqueo de PDF por CSP) ya existían o dependen de la configuración de despliegue, no del cambio en el backend.

---

## 1. XHR (compatibles)

- **GET** `https://rapicredit.onrender.com/api/v1/estado-cuenta/public/validar-cedula?cedula=V11112944` → **HTTP 200**  
  Sigue igual; no se modificó.

- **POST** `https://rapicredit.onrender.com/api/v1/estado-cuenta/public/solicitar-estado-cuenta` → **HTTP 200**  
  El contrato no cambia: el body sigue siendo JSON con `ok`, `pdf_base64`, `mensaje`, `error`.  
  Solo se **amplía el contenido del PDF** (se añaden las tablas de amortización); el frontend no tiene que cambiar nada.

---

## 2. CSS: “Juego de reglas ignoradas debido a un mal selector” (index-DZWKGIKT.css:1:66675)

- Es un **aviso del navegador** por un selector CSS inválido o no soportado (habitual con Tailwind/PostCSS y hashes de build).
- **No está causado** por la solución de amortización (solo toca backend).
- En `frontend/index.html` ya hay **scripts que ocultan** ese tipo de avisos en consola (por texto “reglas ignoradas”, “mal selector”, “index-*.css”, etc.).
- Si el aviso sigue saliendo, puede ser:
  - Que el script se ejecute después de que el navegador haya mostrado el aviso, o  
  - Que el mensaje llegue por `console.error` en lugar de `console.warn` y el filtro no lo cubra.

**Conclusión:** compatible; el comportamiento de la app y del PDF no dependen de ese CSS.

---

## 3. Content-Security-Policy: bloqueo de `data:application/pdf;base64,...` en iframe

Mensaje típico:

```text
Content-Security-Policy: La configuración de la página bloqueó la carga de un recurso (frame-src)
en data:application/pdf;base64,... porque viola la siguiente directiva: "default-src 'self'"
```

- En el **código fuente** del frontend, `frontend/index.html` ya incluye una meta CSP que permite el PDF en iframe:

  ```html
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; frame-src 'self' data: blob:;" />
  ```

- Si aun así el navegador aplica **solo** `default-src 'self'` para `frame-src`, suele ser porque:
  1. El **servidor** (p. ej. Render) envía una **cabecera** `Content-Security-Policy` al servir el HTML.  
     Esa cabecera **tiene prioridad** sobre la meta y puede no incluir `frame-src` (o no incluir `data:`), por lo que para iframes se usa `default-src 'self'` y se bloquea `data:`.
  2. El **index.html desplegado** (build) no incluye la meta (poco probable si Vite usa el mismo `index.html` como plantilla).

Qué hacer:

1. **Comprobar en producción** qué CSP se aplica:
   - En DevTools → pestaña **Red** → recargar → seleccionar el documento (primera petición, p. ej. `rapicredit-estadocuenta`).
   - En **Encabezados de respuesta**, ver si existe `Content-Security-Policy`.  
   - Si existe y no incluye `frame-src ... data: blob:`, esa es la causa.

2. **Si el servidor (Render) envía CSP:**  
   Configurar en Render (o en el proxy/CDN) una política que permita el iframe con PDF en data, por ejemplo:
   - Añadir o modificar la cabecera para que incluya:  
     `frame-src 'self' data: blob:;`  
   (y el resto que necesites, p. ej. `default-src 'self'; ...`).

3. **Si el servidor no envía CSP:**  
   Asegurarse de que el **build** que se despliega incluye la meta anterior (revisar el `index.html` generado en `dist/` o equivalente).

4. **Mientras tanto:**  
   El flujo sigue siendo válido: el usuario puede usar el botón **“Descargar PDF”** y el envío por correo. Solo falla la **vista previa** dentro del iframe cuando la CSP efectiva no permite `data:` en `frame-src`.

---

## 4. Compatibilidad con la solución de amortización

| Elemento              | ¿Compatible? | Nota                                                                 |
|-----------------------|-------------|----------------------------------------------------------------------|
| Validar cédula (GET)  | Sí          | Sin cambios.                                                         |
| Solicitar PDF (POST)  | Sí          | Misma respuesta; el PDF ahora incluye tablas de amortización.        |
| Visualización en iframe | Depende de CSP | Si la CSP efectiva permite `frame-src data:`, la vista previa funciona. |
| Descargar PDF         | Sí          | El enlace de descarga no depende del iframe.                         |
| Envío por email       | Sí          | Backend sigue adjuntando el mismo PDF (ahora con amortización).      |
| Aviso CSS “mal selector” | Sí       | Previo a la solución; no afecta al PDF ni a la lógica.               |

En conjunto, los “antiguos” (XHR, flujo de estado de cuenta, descarga y email) **son compatibles** con la solución que añade la tabla de amortización al PDF; el único punto a revisar en el entorno desplegado es la CSP para poder mostrar el PDF dentro del iframe sin bloqueos.
