# 📋 Cómo Verificar Datos del Excel

## ✅ NO necesitas subir nada a la base de datos

El script Python lee tu Excel directamente y compara con la BD.

---

## 🚀 Pasos para Verificar

### 1. Coloca tu archivo Excel

Coloca tu archivo Excel en esta carpeta:
```
scripts/data/datos_excel.xlsx
```

**Importante:** El Excel debe tener estas columnas (pueden tener nombres similares):
- **CLIENTE** (o Cliente, NOMBRE)
- **CEDULA IDENTIDAD** (o CEDULA, Cédula, CI)
- **TOTAL FINANCIAMIENTO** (o Total Financiamiento, TOTAL)
- **ABONOS** (o Abonos, PAGOS, TOTAL PAGADO)
- **SALDO DEUDOR** (o Saldo Deudor, SALDO, PENDIENTE)
- **CUOTAS** (o Cuotas, NUMERO CUOTAS)
- **MODALIDAD FINANCIAMIENTO** (o Modalidad)

### 2. Instala dependencias (si no las tienes)

```bash
pip install pandas openpyxl sqlalchemy psycopg2-binary
```

### 3. Configura la variable de entorno

Asegúrate de tener `DATABASE_URL` configurada:

```bash
# Windows PowerShell
$env:DATABASE_URL="postgresql://user:password@host:5432/database"

# Linux/Mac
export DATABASE_URL="postgresql://user:password@host:5432/database"
```

O crea un archivo `.env` en la raíz del proyecto con:
```
DATABASE_URL=postgresql://user:password@host:5432/database
```

### 4. Ejecuta el script

```bash
python scripts/python/verificar_excel_bd.py
```

### 5. Revisa el reporte

El script generará un reporte en:
```
scripts/data/reporte_verificacion_excel.md
```

---

## 📊 ¿Qué verifica el script?

✅ **Cliente existe** (por cédula)  
✅ **Préstamo existe** (por cédula + total_financiamiento)  
✅ **Total financiamiento coincide**  
✅ **Abonos coinciden** (suma de pagos en BD)  
✅ **Saldo deudor coincide** (suma de cuotas pendientes)  
✅ **Número de cuotas coincide**  
✅ **Modalidad coincide**

---

## ❓ Preguntas Frecuentes

### ¿Puedo usar otro nombre para el archivo Excel?

Sí, edita la variable `EXCEL_PATH` en el script:
```python
EXCEL_PATH = project_root / "scripts" / "data" / "tu_archivo.xlsx"
```

### ¿Qué pasa si el Excel tiene columnas con nombres diferentes?

El script busca automáticamente columnas similares. Por ejemplo:
- "CLIENTE" → encuentra "Cliente", "NOMBRE", "Nombre"
- "CEDULA IDENTIDAD" → encuentra "CEDULA", "Cédula", "CI"

### ¿El script modifica la base de datos?

**NO.** El script solo **lee** datos, nunca modifica nada.

### ¿Puedo ejecutar el script varias veces?

Sí, puedes ejecutarlo cuantas veces quieras. Cada ejecución genera un nuevo reporte.

---

## 🔧 Solución de Problemas

### Error: "El archivo no existe"
- Verifica que el Excel esté en: `scripts/data/datos_excel.xlsx`
- Verifica que el nombre del archivo sea exacto

### Error: "Columnas faltantes"
- Verifica que el Excel tenga las columnas necesarias
- El script mostrará qué columnas encontró y cuáles faltan

### Error: "Error al conectar a la base de datos"
- Verifica tu `DATABASE_URL`
- Verifica que PostgreSQL esté corriendo
- Verifica credenciales de acceso

### Error: "pandas no está instalado"
```bash
pip install pandas openpyxl
```

