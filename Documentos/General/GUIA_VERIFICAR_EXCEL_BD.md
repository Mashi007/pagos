# 📋 Guía: Verificar Datos del Excel en la Base de Datos

## ✅ NO necesitas subir otra base de datos

Los scripts se ejecutan directamente en tu base de datos PostgreSQL actual.

---

## 🎯 OPCIÓN 1: Verificación Manual (Más Simple)

### Paso 1: Abrir DBeaver
1. Abre **DBeaver**
2. Conéctate a tu base de datos PostgreSQL

### Paso 2: Ejecutar verificación por cédula
Copia y ejecuta este script, reemplazando `'V23107415'` con la cédula del Excel:

```sql
-- Verificar un cliente del Excel
SELECT 
    'CLIENTE' AS tipo,
    'V23107415' AS cedula_excel,
    c.id AS cliente_id,
    c.cedula AS cedula_bd,
    c.nombres AS nombres_bd,
    CASE WHEN c.id IS NULL THEN '❌ NO EXISTE' ELSE '✅ EXISTE' END AS estado
FROM clientes c
WHERE c.cedula = 'V23107415';

-- Verificar préstamo del Excel
SELECT 
    'PRESTAMO' AS tipo,
    'V23107415' AS cedula_excel,
    864.00 AS total_financiamiento_excel,
    p.id AS prestamo_id,
    p.total_financiamiento AS total_financiamiento_bd,
    p.numero_cuotas AS cuotas_bd,
    COALESCE(SUM(cu.total_pagado), 0) AS abonos_bd,
    COALESCE(SUM(cu.monto_cuota - cu.total_pagado), 0) AS saldo_deudor_bd,
    CASE 
        WHEN p.id IS NULL THEN '❌ PRESTAMO NO EXISTE'
        WHEN ABS(p.total_financiamiento - 864.00) > 0.01 THEN '⚠️ TOTAL DIFERENTE'
        ELSE '✅ EXISTE Y COINCIDE'
    END AS estado
FROM prestamos p
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.cedula = 'V23107415'
  AND ABS(p.total_financiamiento - 864.00) < 100
GROUP BY p.id, p.total_financiamiento, p.numero_cuotas
ORDER BY ABS(p.total_financiamiento - 864.00)
LIMIT 5;
```

### Paso 3: Repetir para cada registro
Repite el Paso 2 cambiando la cédula y el total_financiamiento para cada registro del Excel.

---

## 🚀 OPCIÓN 2: Verificación Masiva con Script SQL

**⚠️ IMPORTANTE:** La tabla temporal (`CREATE TEMP TABLE`) NO es un archivo que subes. Se crea en memoria durante la sesión SQL y desaparece al cerrar DBeaver.

### Paso 1: Preparar datos del Excel
1. Abre tu Excel
2. Copia solo las columnas: **CLIENTE**, **CEDULA IDENTIDAD**, **TOTAL FINANCIAMIENTO**, **ABONOS**, **SALDO DEUDOR**, **CUOTAS**
3. Formatea los datos como valores SQL

### Paso 2: Usar script masivo
1. Abre `scripts/sql/verificar_datos_excel_bd_masivo.sql` en DBeaver
2. Reemplaza la sección `INSERT INTO datos_excel VALUES` con tus datos (formato SQL)
3. Ejecuta el script completo
4. La tabla temporal se crea automáticamente en memoria (no subes nada)

---

## 🐍 OPCIÓN 3: Script Python (Más Automático)

Si prefieres automatizar todo, usa el script Python que lee el Excel directamente:

1. Guarda tu Excel en: `scripts/data/datos_excel.xlsx`
2. Ejecuta: `python scripts/python/verificar_excel_bd.py`
3. El script generará un reporte con todas las diferencias

---

## 📊 ¿Qué verifica cada script?

✅ **Cliente existe** (por cédula)  
✅ **Préstamo existe** (por cédula + total_financiamiento)  
✅ **Total financiamiento coincide**  
✅ **Abonos coinciden** (suma de pagos)  
✅ **Saldo deudor coincide** (suma de cuotas pendientes)  
✅ **Número de cuotas coincide**  
✅ **Modalidad coincide**

---

## ❓ ¿Cuál opción elegir?

- **Opción 1**: Si tienes pocos registros (< 10)
- **Opción 2**: Si tienes muchos registros y sabes SQL
- **Opción 3**: Si prefieres automatizar todo (recomendado para 3690 registros)


