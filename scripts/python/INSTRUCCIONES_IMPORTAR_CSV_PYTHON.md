# 🐍 Solución Definitiva: Importar CSV con Python

## ❌ Problema

Solo se importaron **466 registros** de aproximadamente **4,305** usando DBeaver.

---

## ✅ Solución: Script Python

He creado un script Python que importa el CSV directamente usando `psycopg2` y `pandas`, que es más robusto que el importador de DBeaver.

---

## 📋 Pasos para Ejecutar

### 1. Instalar Dependencias (si no están instaladas)

```bash
pip install pandas psycopg2-binary
```

### 2. Configurar DATABASE_URL

Asegúrate de que la variable de entorno `DATABASE_URL` esté configurada:

```bash
# Windows PowerShell
$env:DATABASE_URL = "postgresql://usuario:password@host:puerto/database"
```

### 3. Ejecutar el Script

```bash
python scripts/python/importar_csv_directo.py
```

---

## 🔧 Qué Hace el Script

1. **Lee el CSV** usando pandas (más robusto que DBeaver)
2. **Limpia los datos** automáticamente:
   - Remueve caracteres problemáticos
   - Convierte tipos de datos correctamente
   - Maneja valores nulos
3. **Trunca la tabla** `bd_clientes_csv`
4. **Inserta todos los registros** usando `execute_values` (más rápido)
5. **Verifica** cuántos registros se importaron

---

## ✅ Ventajas de Esta Solución

- ✅ **Más robusto**: Maneja errores de datos automáticamente
- ✅ **Más rápido**: Usa inserción en lote optimizada
- ✅ **Limpia datos**: Convierte y limpia valores problemáticos
- ✅ **Completo**: Importa todos los registros válidos

---

## 📊 Después de Ejecutar

Ejecuta el script de verificación:

```sql
-- Ver scripts/sql/verificar_importacion_completa.sql
```

---

## 🎯 Resultado Esperado

Deberías ver aproximadamente **4,305 registros** (o al menos 4,000+) importados correctamente.

---

## ⚠️ Si Hay Errores

El script mostrará mensajes de error detallados. Revisa:
- Que `DATABASE_URL` esté configurado correctamente
- Que el archivo CSV esté en la ruta correcta
- Que las columnas del CSV coincidan con las esperadas

