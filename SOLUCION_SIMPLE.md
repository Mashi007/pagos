# ✅ Solución Simple: Generar 12 Cuotas

## 🎯 Problema
El préstamo #9 tiene:
- ✅ Estado: APROBADO
- ✅ numero_cuotas: 12  
- ❌ Sin cuotas en la tabla: 0 cuotas

## ✅ Solución: Desde el Frontend (MEJOR OPCIÓN)

### Opción 1: Botón en el Frontend

1. Ve al dashboard de préstamos
2. Busca Juan García (Préstamo #9)
3. Clic en el ícono 👁️ (Ver detalles)
4. En el modal, busca pestaña "Tabla de Amortización"
5. Debe aparecer un botón: **"Generar Tabla de Amortización"**
6. Clic en ese botón
7. ✅ Se generarán automáticamente las 12 cuotas

---

### Opción 2: Desde API (Postman)

```bash
POST http://tu-api.com/api/v1/prestamos/9/generar-amortizacion
Headers:
  Authorization: Bearer tu-token
```

---

### Opción 3: SQL Manual (Como Último Recurso)

Ejecuta en DBeaver después de obtener los datos exactos:

```sql
-- Primero obtén los datos
SELECT 
    id,
    total_financiamiento,
    numero_cuotas,
    fecha_base_calculo
FROM prestamos WHERE id = 9;

-- Luego inserta las cuotas manualmente con esos valores
```

---

## 📋 Orden Recomendado

1. ✅ **Primero**: Desde el frontend (botón "Generar Amortización")
2. ❌ **Solo si falla**: SQL manual con los valores exactos

---

## 🎯 Después de Generar

Verifica en DBeaver:

```sql
SELECT COUNT(*) as total_cuotas FROM cuotas WHERE prestamo_id = 9;
```

Debe mostrar: `total_cuotas = 12`

