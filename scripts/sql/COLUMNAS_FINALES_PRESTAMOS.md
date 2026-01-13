# 📋 COLUMNAS FINALES DE LA TABLA `prestamos`

## Fecha de Actualización
Después de eliminar `producto_financiero` y hacer `analista` obligatorio

---

## 📊 ESTRUCTURA FINAL DE COLUMNAS (37 columnas)

### 1. IDENTIFICACIÓN
| # | Columna | Tipo | Nullable | Default | Descripción |
|---|---------|------|----------|---------|-------------|
| 1 | `id` | INTEGER | NO | `nextval('prestamos_id_seq'::regclass)` | ID único con autoincremento |

### 2. DATOS DEL CLIENTE
| # | Columna | Tipo | Nullable | Default | Descripción |
|---|---------|------|----------|---------|-------------|
| 2 | `cliente_id` | INTEGER | NO | - | Foreign Key a `clientes.id` |
| 3 | `cedula` | VARCHAR(20) | NO | - | Cédula del cliente |
| 4 | `nombres` | VARCHAR(100) | NO | - | Nombre del cliente |

### 3. DATOS DEL PRÉSTAMO
| # | Columna | Tipo | Nullable | Default | Descripción |
|---|---------|------|----------|---------|-------------|
| 5 | `valor_activo` | NUMERIC(15,2) | YES | - | Valor del activo (vehículo) |
| 6 | `total_financiamiento` | NUMERIC(15,2) | NO | - | Monto total del préstamo |
| 7 | `fecha_requerimiento` | DATE | NO | - | Fecha que necesita el préstamo |
| 8 | `modalidad_pago` | VARCHAR(20) | NO | - | MENSUAL, QUINCENAL, SEMANAL |
| 9 | `numero_cuotas` | INTEGER | NO | - | Número de cuotas |
| 10 | `cuota_periodo` | NUMERIC(15,2) | NO | - | Monto por cuota |
| 11 | `tasa_interes` | NUMERIC(5,2) | NO | `0.00` | Tasa de interés |
| 12 | `fecha_base_calculo` | DATE | YES | - | Fecha base para generar tabla de amortización |

### 4. PRODUCTO
| # | Columna | Tipo | Nullable | Default | Descripción |
|---|---------|------|----------|---------|-------------|
| 13 | `producto` | VARCHAR(100) | NO | - | Modelo de vehículo |

### 5. INFORMACIÓN ADICIONAL (LEGACY)
| # | Columna | Tipo | Nullable | Default | Descripción |
|---|---------|------|----------|---------|-------------|
| 14 | `concesionario` | VARCHAR(100) | YES | - | Concesionario (legacy - usar `concesionario_id`) |
| 15 | `analista` | VARCHAR(100) | **NO** | - | **Analista asignado (OBLIGATORIO)** |
| 16 | `modelo_vehiculo` | VARCHAR(100) | YES | - | Modelo del vehículo (legacy - usar `modelo_vehiculo_id`) |

### 6. RELACIONES NORMALIZADAS
| # | Columna | Tipo | Nullable | Default | Descripción |
|---|---------|------|----------|---------|-------------|
| 17 | `concesionario_id` | INTEGER | YES | - | FK a `concesionarios.id` |
| 18 | `analista_id` | INTEGER | YES | - | FK a `analistas.id` |
| 19 | `modelo_vehiculo_id` | INTEGER | YES | - | FK a `modelos_vehiculos.id` |

### 7. ESTADO Y APROBACIÓN
| # | Columna | Tipo | Nullable | Default | Descripción |
|---|---------|------|----------|---------|-------------|
| 20 | `estado` | VARCHAR(20) | NO | `'DRAFT'` | Estado del préstamo (DRAFT, EN_REVISION, APROBADO, RECHAZADO, FINALIZADO) |
| 21 | `usuario_proponente` | VARCHAR(100) | NO | - | Email del analista |
| 22 | `usuario_aprobador` | VARCHAR(100) | YES | - | Email del admin |
| 23 | `usuario_autoriza` | VARCHAR(100) | YES | `'operaciones@rapicreditca.com'` | Usuario que autoriza |
| 24 | `observaciones` | TEXT | YES | `'No observaciones'` | Observaciones |

### 8. FECHAS
| # | Columna | Tipo | Nullable | Default | Descripción |
|---|---------|------|----------|---------|-------------|
| 25 | `fecha_registro` | TIMESTAMP | NO | `CURRENT_TIMESTAMP` | Fecha de creación |
| 26 | `fecha_aprobacion` | TIMESTAMP | YES | - | Fecha cuando se aprueba el préstamo |
| 27 | `fecha_actualizacion` | TIMESTAMP | NO | `CURRENT_TIMESTAMP` | Fecha de última actualización |

### 9. INFORMACIÓN COMPLEMENTARIA
| # | Columna | Tipo | Nullable | Default | Descripción |
|---|---------|------|----------|---------|-------------|
| 28 | `informacion_desplegable` | BOOLEAN | NO | `false` | Si ha desplegado información adicional |

### 10. ML IMPAGO - VALORES MANUALES
| # | Columna | Tipo | Nullable | Default | Descripción |
|---|---------|------|----------|---------|-------------|
| 29 | `ml_impago_nivel_riesgo_manual` | VARCHAR(20) | YES | - | Nivel de riesgo manual (Alto, Medio, Bajo) |
| 30 | `ml_impago_probabilidad_manual` | NUMERIC(5,3) | YES | - | Probabilidad manual (0.0 a 1.0) |

### 11. ML IMPAGO - VALORES CALCULADOS
| # | Columna | Tipo | Nullable | Default | Descripción |
|---|---------|------|----------|---------|-------------|
| 31 | `ml_impago_nivel_riesgo_calculado` | VARCHAR(20) | YES | - | Nivel de riesgo calculado por ML |
| 32 | `ml_impago_probabilidad_calculada` | NUMERIC(5,3) | YES | - | Probabilidad calculada por ML (0.0 a 1.0) |
| 33 | `ml_impago_calculado_en` | TIMESTAMP | YES | - | Fecha de última predicción calculada |
| 34 | `ml_impago_modelo_id` | INTEGER | YES | - | FK a `modelos_impago_cuotas.id` |

### 12. REVISIÓN
| # | Columna | Tipo | Nullable | Default | Descripción |
|---|---------|------|----------|---------|-------------|
| 35 | `requiere_revision` | BOOLEAN | NO | `false` | Marca préstamos que requieren revisión manual |

---

## ✅ CAMBIOS REALIZADOS

### ❌ COLUMNA ELIMINADA:
- ~~`producto_financiero`~~ - **ELIMINADA** (datos migrados a `analista`)

### ✅ COLUMNA MODIFICADA:
- `analista` - **AHORA ES OBLIGATORIO (NOT NULL)**

---

## 📝 RESUMEN

- **Total de columnas:** 37
- **Columnas obligatorias (NOT NULL):** 19
- **Columnas opcionales (NULL):** 18
- **Foreign Keys:** 4 (`cliente_id`, `concesionario_id`, `analista_id`, `modelo_vehiculo_id`, `ml_impago_modelo_id`)

---

## 🔑 ÍNDICES

- `id` (Primary Key)
- `cliente_id` (Foreign Key)
- `cedula`
- `estado`
- `fecha_registro`
- `concesionario_id`
- `analista_id`
- `modelo_vehiculo_id`
- `requiere_revision`

---

## 📌 NOTAS IMPORTANTES

1. **`analista` es ahora obligatorio** - Todos los préstamos deben tener un analista asignado
2. **`producto_financiero` fue eliminada** - Sus datos fueron migrados a `analista`
3. **Campos legacy** - `concesionario`, `analista`, `modelo_vehiculo` se mantienen por compatibilidad, pero se recomienda usar los campos normalizados (`*_id`)
