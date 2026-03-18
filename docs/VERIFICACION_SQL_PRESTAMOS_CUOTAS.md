# Verificación: SQL préstamos y cuotas (comprobado en código)

## Fuentes verificadas

- **Tabla préstamos**: `backend/app/models/prestamo.py` → `__tablename__ = "prestamos"`.
- **Tabla cuotas**: `backend/app/models/cuota.py` → `__tablename__ = "cuotas"`, con `prestamo_id = Column(Integer, ForeignKey("prestamos.id"), ...)`.
- **Modelos exportados**: `backend/app/models/__init__.py` incluye `Prestamo` y `Cuota`; no existe modelo ni tabla `tabla_amortizacion` en la app.

## Conclusión

- Las cuotas están en la tabla **`cuotas`**, enlazada a **`prestamos`** por **`prestamo_id`**.
- No se usa en el código ninguna tabla llamada `tabla_amortizacion` ni `prestamo` (singular). La tabla correcta es **`prestamos`** (plural).

---

## SQL para verificar si todos los préstamos tienen cuotas generadas

### 1. Préstamos sin ninguna cuota

```sql
SELECT p.id AS prestamo_id, p.cliente_id, p.total_financiamiento, p.numero_cuotas
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
WHERE c.id IS NULL
ORDER BY p.id;
```

### 2. Cantidad de préstamos sin cuotas (0 = todos tienen cuotas)

```sql
SELECT COUNT(*) AS prestamos_sin_cuotas
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
WHERE c.id IS NULL;
```

### 3. Préstamos con número de cuotas distinto al esperado (prestamos.numero_cuotas)

```sql
SELECT p.id, p.numero_cuotas AS esperadas,
       COUNT(c.id) AS generadas,
       CASE WHEN COUNT(c.id) = p.numero_cuotas THEN 'OK' ELSE 'FALTA' END AS estado
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
GROUP BY p.id, p.numero_cuotas
HAVING COUNT(c.id) != p.numero_cuotas
ORDER BY p.id;
```

### 4. Resumen global

```sql
SELECT
  (SELECT COUNT(*) FROM prestamos) AS total_prestamos,
  (SELECT COUNT(DISTINCT prestamo_id) FROM cuotas) AS prestamos_con_cuotas,
  (SELECT COUNT(*) FROM prestamos p
   LEFT JOIN cuotas c ON c.prestamo_id = p.id
   WHERE c.id IS NULL) AS prestamos_sin_cuotas;
```

---

## SQL para verificar si todos los préstamos están aprobados

En `prestamo.py`, el campo es **`estado`** (String), con `server_default=text("'DRAFT'")`. Valores típicos: `'DRAFT'`, `'APROBADO'` (confirmar en BD si hay otros).

### Préstamos no aprobados

```sql
SELECT id, cliente_id, total_financiamiento, estado, fecha_registro
FROM prestamos
WHERE estado IS NULL OR estado != 'APROBADO'
ORDER BY id;
```

### ¿Todos aprobados? (0 = sí)

```sql
SELECT COUNT(*) AS prestamos_no_aprobados
FROM prestamos
WHERE estado IS NULL OR estado != 'APROBADO';
```
