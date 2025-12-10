# 📋 Guía Paso a Paso: Verificar Excel

## ✅ Paso 1: Preparar el Excel

1. **Abre tu archivo Excel** (el que tiene los 3690 registros)
2. **Guarda una copia** con el nombre: `datos_excel.xlsx`
3. **Verifica que tenga estas columnas:**
   - CLIENTE (o Cliente)
   - CEDULA IDENTIDAD (o CEDULA, Cédula)
   - TOTAL FINANCIAMIENTO (o Total Financiamiento)
   - ABONOS (o Abonos)
   - SALDO DEUDOR (o Saldo Deudor)
   - CUOTAS (o Cuotas)
   - MODALIDAD FINANCIAMIENTO (o Modalidad)

---

## ✅ Paso 2: Copiar el Excel a la carpeta del proyecto

### Opción A: Desde el Explorador de Windows

1. **Abre el Explorador de Windows** (presiona `Windows + E`)
2. **Navega a esta carpeta:**
   ```
   C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\scripts\data
   ```
3. **Copia tu Excel** (`datos_excel.xlsx`) y **pégalo** en esa carpeta

### Opción B: Desde la terminal

1. **Abre PowerShell** o **CMD**
2. **Ejecuta este comando** (reemplaza `RUTA_DONDE_ESTA_TU_EXCEL` con la ruta real):
   ```powershell
   Copy-Item "RUTA_DONDE_ESTA_TU_EXCEL\datos_excel.xlsx" -Destination "C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\scripts\data\datos_excel.xlsx"
   ```

**Ejemplo:**
```powershell
# Si tu Excel está en el Escritorio:
Copy-Item "C:\Users\PORTATIL\Desktop\datos_excel.xlsx" -Destination "C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\scripts\data\datos_excel.xlsx"
```

---

## ✅ Paso 3: Verificar que el Excel esté en el lugar correcto

1. **Abre la carpeta:**
   ```
   C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\scripts\data
   ```
2. **Debes ver el archivo:** `datos_excel.xlsx`

---

## ✅ Paso 4: Instalar dependencias (si no las tienes)

1. **Abre PowerShell** o **CMD**
2. **Navega a la carpeta del proyecto:**
   ```powershell
   cd C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos
   ```
3. **Instala las dependencias:**
   ```powershell
   pip install pandas openpyxl sqlalchemy psycopg2-binary
   ```

**Espera a que termine la instalación.**

---

## ✅ Paso 5: Verificar la conexión a la base de datos

1. **Verifica que tengas la variable `DATABASE_URL` configurada**

   **Opción A: Si tienes un archivo `.env`:**
   - Abre el archivo `.env` en la raíz del proyecto
   - Verifica que tenga una línea como:
     ```
     DATABASE_URL=postgresql://usuario:contraseña@host:5432/nombre_bd
     ```

   **Opción B: Si no tienes `.env`:**
   - Configura la variable de entorno en PowerShell:
     ```powershell
     $env:DATABASE_URL="postgresql://usuario:contraseña@host:5432/nombre_bd"
     ```

---

## ✅ Paso 6: Ejecutar el script

1. **Abre PowerShell** o **CMD**
2. **Navega a la carpeta del proyecto:**
   ```powershell
   cd C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos
   ```
3. **Ejecuta el script:**
   ```powershell
   python scripts/python/verificar_excel_bd.py
   ```

**El script mostrará:**
- ✅ Leyendo Excel...
- ✅ Conexión establecida
- 🔍 Verificando registros...
- ✅ Verificación completada
- 📝 Generando reporte...

---

## ✅ Paso 7: Revisar el reporte

1. **Abre la carpeta:**
   ```
   C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\scripts\data
   ```
2. **Abre el archivo:** `reporte_verificacion_excel.md`
3. **Revisa los resultados:**
   - Resumen general (cuántos existen, cuántos faltan)
   - Registros con problemas
   - Detalle completo

---

## 🆘 Solución de Problemas

### Error: "El archivo no existe"
- **Solución:** Verifica que el Excel esté en `scripts/data/datos_excel.xlsx`
- Verifica que el nombre sea exacto: `datos_excel.xlsx`

### Error: "pandas no está instalado"
- **Solución:** Ejecuta: `pip install pandas openpyxl`

### Error: "Error al conectar a la base de datos"
- **Solución:** Verifica tu `DATABASE_URL`
- Verifica que PostgreSQL esté corriendo
- Verifica credenciales

### Error: "Columnas faltantes"
- **Solución:** Verifica que el Excel tenga las columnas necesarias
- El script mostrará qué columnas encontró y cuáles faltan

---

## 📝 Resumen Rápido

```
1. Copiar Excel → scripts/data/datos_excel.xlsx
2. Instalar: pip install pandas openpyxl sqlalchemy psycopg2-binary
3. Ejecutar: python scripts/python/verificar_excel_bd.py
4. Revisar: scripts/data/reporte_verificacion_excel.md
```

---

## ✅ Checklist

- [ ] Excel guardado como `datos_excel.xlsx`
- [ ] Excel copiado a `scripts/data/datos_excel.xlsx`
- [ ] Dependencias instaladas (`pandas`, `openpyxl`, etc.)
- [ ] `DATABASE_URL` configurada
- [ ] Script ejecutado sin errores
- [ ] Reporte generado y revisado

