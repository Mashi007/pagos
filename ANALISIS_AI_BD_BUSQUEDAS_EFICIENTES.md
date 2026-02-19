# Análisis: Mecanismo de conexión AI ↔ BD para búsquedas eficientes

**Fecha:** 2025-02-19  
**Alcance:** Flujo de datos, optimizaciones, puntos fuertes y mejoras posibles.

---

## 1. Arquitectura general

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐     ┌──────────────┐
│   Frontend  │────▶│  POST /chat      │────▶│  PostgreSQL │     │  OpenRouter  │
│   ChatAI    │     │  configuracion_ai│     │  (BD)       │     │  (API)       │
└─────────────┘     └────────┬─────────┘     └──────▲──────┘     └──────▲───────┘
                             │                      │                   │
                             │  1. Sesión corta     │                   │
                             │  2. Cargar contexto  │                   │
                             │  3. Cerrar sesión   │                   │
                             │  4. Llamar API ──────────────────────────┘
                             │  5. Devolver respuesta
                             ▼
                      ┌──────────────┐
                      │ Caché (90s)  │
                      │ contexto BD  │
                      └──────────────┘
```

**Principio:** La conexión a BD se usa solo para leer datos; se cierra **antes** de llamar a OpenRouter. Así no se retiene un slot del pool durante la I/O externa (hasta 45 s).

---

## 2. Mecanismos de eficiencia implementados

### 2.1 Mínimos round-trips (1 consulta principal)

| Antes | Ahora |
|-------|-------|
| 9+ consultas separadas (`db.query().scalar()`) | **1 consulta** con subconsultas escalares |

**Implementación:** `_build_chat_context()` usa `select()` con múltiples `scalar_subquery().label()`:

```python
stmt = select(
    select(func.count(Cliente.id)).scalar_subquery().label("total_clientes"),
    select(func.count(Prestamo.id)).scalar_subquery().label("total_prestamos"),
    # ... 12 métricas en total
)
row = db.execute(stmt).first()
```

PostgreSQL ejecuta una sola sentencia que combina las subconsultas; un único round-trip a la BD.

### 2.2 Sesión de corta duración

| Fase | Conexión BD |
|------|-------------|
| Cargar config + contexto | ✅ Abierta |
| Llamada a OpenRouter (hasta 45 s) | ❌ Cerrada |
| Devolver respuesta | ❌ Cerrada |

**Código:** `_build_prompt_for_question()` abre `SessionLocal()`, hace las consultas y cierra en `finally` antes de llamar a OpenRouter.

### 2.3 Caché de contexto (TTL 90 s)

- **Qué se cachea:** Bloque de datos agregados (`datos_bd`).
- **Dónde:** Memoria (`chat_context_cache.py`).
- **Invalidación:** Al guardar config AI o prompt personalizado.

**Efecto:** En ventanas de 90 s, las preguntas repetidas evitan consultas a BD para el contexto base.

### 2.4 Timeout en consulta

```python
db.execute(text(f"SET LOCAL statement_timeout = {CONTEXTO_AI_STATEMENT_TIMEOUT_MS}"))
# 10 segundos
```

Si la consulta tarda más de 10 s, PostgreSQL la cancela y no se bloquea la conexión.

### 2.5 Pool de conexiones

```python
# database.py
engine = create_engine(
    _db_url,
    pool_pre_ping=True,   # Verifica conexión antes de usar
    pool_size=5,
    max_overflow=10,
)
```

- **pool_pre_ping:** Evita usar conexiones muertas (útil en Render con spin-down).
- **pool_size=5, max_overflow=10:** Hasta 15 conexiones bajo carga.

---

## 3. Flujo de búsquedas por tipo de pregunta

### 3.1 Preguntas agregadas (totales, mora, etc.)

| Paso | Acción |
|------|--------|
| 1 | ¿Contexto en caché? → Sí: usar base cacheado |
| 2 | No: ejecutar 1 consulta agregada (12 métricas + muestra clientes mora) |
| 3 | Guardar en caché |
| 4 | Construir prompt y llamar a OpenRouter |

**Consultas BD:** 0 (cache hit) o 1–2 (cache miss: agregados + opcional muestra clientes mora).

### 3.2 Preguntas con cédula específica

| Paso | Acción |
|------|--------|
| 1 | Extraer cédula de la pregunta (`_extract_cedula_from_pregunta`) |
| 2 | Si hay cédula: consulta adicional `SELECT ... FROM clientes WHERE cedula ILIKE ...` |
| 3 | Añadir `cliente_buscado` al contexto |
| 4 | Construir prompt y llamar a OpenRouter |

**Consultas BD:** 1 (lookup por cédula) + 0–1 (contexto base si no está en caché).

### 3.3 Consultas adicionales en `_build_chat_context`

Cuando hay mora (`prestamos_con_mora_count > 0`):

1. `SELECT prestamo_id FROM cuotas WHERE ... DISTINCT LIMIT 5`
2. `SELECT cedula, nombres, telefono FROM clientes JOIN prestamos WHERE prestamo_id IN (...)`

**Total en cache miss:** 1 consulta principal + 2 consultas para muestra de clientes en mora = **3 round-trips**.

---

## 4. Índices y rendimiento de consultas

### 4.1 Uso de índices implícito

| Tabla | Condición | Índice esperado |
|-------|-----------|----------------|
| `clientes` | `cedula` (ILIKE, =) | `clientes_cedula` (index) |
| `prestamos` | `estado`, `cliente_id` | `prestamos_estado`, FK |
| `cuotas` | `fecha_pago`, `fecha_vencimiento`, `prestamo_id` | FK, posible índice compuesto |

### 4.2 Consulta de lookup por cédula

```python
Cliente.cedula.ilike(cedula) | Cliente.cedula.ilike(f"%{cedula}%")
```

- **Riesgo:** `ILIKE '%X%'` puede impedir el uso de índice en algunos casos.
- **Mitigación:** `order_by(func.length(Cliente.cedula).asc())` para priorizar coincidencia exacta; `limit(1)` reduce filas leídas.

### 4.3 Condición de mora

```python
Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < func.current_date()
```

Índice compuesto `(fecha_pago, fecha_vencimiento)` o `(fecha_vencimiento)` mejoraría filtrado en tablas grandes.

---

## 5. Resumen de eficiencia

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Round-trips | ✅ Optimizado | 1 consulta principal; 2–3 en cache miss con mora |
| Retención de conexión | ✅ Correcto | Sesión cerrada antes de OpenRouter |
| Caché | ✅ Activo | TTL 90 s, invalidación al cambiar config |
| Timeout | ✅ Configurado | 10 s por consulta |
| Pool | ✅ Ajustado | pool_pre_ping, pool_size=5, max_overflow=10 |
| Lookup dinámico | ✅ Condicional | Solo cuando se detecta cédula en la pregunta |

---

## 6. Posibles mejoras

### 6.1 Índices

- Índice compuesto en `cuotas (fecha_pago, fecha_vencimiento)` para la condición de mora.
- Índice en `clientes.cedula` si no existe (para búsquedas por cédula).

### 6.2 Lookup por cédula

- Evitar `ILIKE '%cedula%'` cuando la cédula sea completa; usar `=` o `ILIKE 'cedula'` para aprovechar índice.
- Considerar búsqueda solo por coincidencia exacta cuando el patrón sea de cédula completa (p. ej. V + 8 dígitos).

### 6.3 Consultas de muestra en mora

- Unificar en una sola consulta con `DISTINCT ON (cliente_id)` o subconsulta correlacionada para reducir round-trips cuando hay mora.

### 6.4 Caché distribuido

- Si hay varios workers (p. ej. en Render), el caché en memoria no se comparte. Redis permitiría un caché compartido entre instancias.

---

## 7. Referencias

- `backend/app/api/v1/endpoints/configuracion_ai.py` — Lógica principal
- `backend/app/core/chat_context_cache.py` — Caché
- `backend/app/core/database.py` — Pool y sesiones
- `backend/docs/AUDITORIA_AI_BD.md` — Buenas prácticas AI-BD
