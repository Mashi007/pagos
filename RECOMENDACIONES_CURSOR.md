# Recomendaciones para Cursor (proyecto pagos)

Resumen de lo revisado y qué hacer para que Cursor vaya más fluido.

---

## 1. Modelo: usar uno rápido y económico

- **Principal:** Deja activo **solo Gemini 3 Flash** (o 2.5 Flash) para Chat y Agente.
- **Desactiva** el resto (Opus 4.5, Sonnet 4.5, GPT-5.2, GPT-5.2 Codex) para uso diario.
- **Motivo:** Tu ping al backend es ~310 ms; el resto del tiempo (~900 ms por respuesta) es el modelo. Un Flash suele bajar a ~400–600 ms por turno.

---

## 2. Indexado: archivos grandes en .cursorignore

- Añade al final de **`.cursorignore`** los 8 archivos de más de 1500 líneas (rutas en `ARCHIVOS_LENTOS_CURSOR.md`).
- Así Cursor indexa menos y va más ligero; el contexto sigue siendo suficiente para pagos.

---

## 3. Indexado: sincronizar codebase

- En **Settings → Indexing & Docs**, si solo ves **1 file** indexado, pulsa **Sync** para reindexar el proyecto.
- Tras el Sync deberías ver muchos más archivos (salvo los que estén en `.cursorignore`).

---

## 4. Reglas: no abusar de “always”

- En **Rules, Skills, Subagents**, evita reglas que se ejecuten **siempre** en cada cambio (p. ej. kluster_code_review_auto).
- Mejor: **by file path** o **manual** para no ralentizar cada guardado.

---

## 5. Red: configuración actual

- **HTTP/1.1** está bien; si vas por VPN/proxy y va estable, déjalo así.
- **Ping ~310 ms**, **SSL** y **DNS** correctos → la red no es el cuello de botella; el tiempo lo marca el modelo.

---

## 6. Caché (si sigue lento)

- Cierra Cursor y borra en `%APPDATA%\Cursor\`: Cache, Code Cache, CachedData, GPUCache, ShaderCache.
- Vuelve a abrir Cursor.

---

## 7. Third-party y MCP

- **Include third-party skills** en **Off** → bien, menos carga.
- **No MCP Tools** → bien; no hace falta añadir nada para velocidad.

---

## Orden sugerido

| # | Acción | Impacto |
|---|--------|--------|
| 1 | Dejar solo **Gemini 3 Flash** activo | Alto – menos latencia por respuesta |
| 2 | Añadir los 8 archivos grandes a **`.cursorignore`** | Medio – índice más ligero |
| 3 | **Sync** en Indexing si solo hay 1 file | Medio – mejor contexto |
| 4 | Reducir reglas “always” | Medio – menos trabajo por guardado |
| 5 | Limpiar caché si sigue lento | Bajo–medio |

Empieza por **1** y **2**; si quieres más fluidez, sigue con **3** y **4**.
