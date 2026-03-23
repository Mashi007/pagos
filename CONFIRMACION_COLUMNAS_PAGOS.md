# Confirmación de Columnas: Tablas de Pagos

## Tablas correctas confirmadas desde modelos SQLAlchemy

```
TABLA 1: pagos (no "pago")
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Columna              Tipo           Notas
────────────────────────────────────────────────────────
id                   Integer        PRIMARY KEY
prestamo_id          Integer        FOREIGN KEY (nullable)
cedula               String(20)     Código del cliente
fecha_pago           DateTime       Fecha del pago registrado
monto_pagado         Numeric(14,2)  ← USAR ESTA (no "monto")
numero_documento     String(100)    Referencia del documento
institucion_bancaria String(255)    Banco o institución
estado               String(30)     Estado del pago
fecha_registro       DateTime       Cuando se registró
fecha_conciliacion   DateTime       Cuando se concilió
conciliado           Boolean        Indicador de conciliación
referencia_pago      String(100)    Referencia interna
usuario_registro     String(255)
notas                Text
documento_nombre     String(255)
documento_tipo       String(50)
documento_ruta       String(255)


TABLA 2: cuota_pagos (no "cuota_pago")
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Columna              Tipo           Notas
────────────────────────────────────────────────────────
id                   Integer        PRIMARY KEY
cuota_id             Integer        FOREIGN KEY a cuotas
pago_id              Integer        FOREIGN KEY a pagos
monto_aplicado       Numeric(14,2)  ← USAR ESTA (no "monto_cuota")
fecha_aplicacion     DateTime       Cuando se aplicó el pago
orden_aplicacion     Integer        Secuencia Cascada
es_pago_completo     Boolean        ¿Completó la cuota?
creado_en            DateTime
actualizado_en       DateTime
```

## Cambios principales en el SQL corregido

| Anterior (INCORRECTO) | Ahora (CORRECTO) | Ubicación |
|---|---|---|
| `pago` | `pagos` | Todas las queries |
| `cuota_pago` | `cuota_pagos` | Todas las queries |
| `p.monto` | `pg.monto_pagado` | Tabla pagos |
| `cp.monto_cuota` | `cp.monto_aplicado` | Tabla cuota_pagos |

## Archivo corregido

```
sql/verificacion_pagos_CORREGIDO.sql
```

Todas las 8 queries ahora usan los nombres correctos de tablas y columnas.

## Query rápida (resumen en 5 segundos)

```sql
-- Resumen rápido de conciliación
SELECT 
  COUNT(*) AS total_pagos,
  COUNT(DISTINCT cp.cuota_id) AS cuotas_con_pagos,
  (SELECT COUNT(*) FROM cuotas WHERE estado = 'PAGADO') AS cuotas_pagadas_total,
  (SELECT COUNT(*) FROM prestamos WHERE estado = 'LIQUIDADO') AS prestamos_liquidados
FROM pagos pg
LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id;
```

## Cómo ejecutar

### Opción 1: DBeaver
1. Abre: `sql/verificacion_pagos_CORREGIDO.sql`
2. Ejecuta con Ctrl+Enter

### Opción 2: Terminal
```bash
psql -U usuario -d pagos_db < sql/verificacion_pagos_CORREGIDO.sql
```

---

**Ejecuta el SQL corregido y comparte los resultados principales.**
