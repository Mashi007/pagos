# 🔧 Solución: Botón "Continuar" Deshabilitado

## ❌ Problema

El botón "Continuar" está deshabilitado en la pantalla "Confirm" y no se puede avanzar.

---

## ✅ Soluciones

### Solución 1: Revisar Mapeo de Columnas

1. **Haz clic en "← Anterior"** para volver a "Tables mapping"
2. **Verifica que todas las columnas estén mapeadas correctamente**
3. **Asegúrate de que la tabla destino sea `bd_clientes_csv`**
4. **Vuelve a "Confirm"**

---

### Solución 2: Ajustar Configuración de Performance

El problema puede ser que "Disable batches" esté en conflicto con otras configuraciones.

1. **Haz clic en "← Anterior"** para volver a "Data load settings"
2. **Desmarca "Disable batches"** (deja que use batches)
3. **Mantén "Ignore duplicate rows errors" marcado**
4. **Vuelve a "Confirm"**

---

### Solución 3: Verificar Tabla Destino

1. **Haz clic en "← Anterior"** hasta llegar a "Tables mapping"
2. **Verifica que "Target container" muestre `bd_clientes_csv`**
3. **Si no aparece, haz clic en "Choose..." y selecciona la tabla manualmente**
4. **Vuelve a "Confirm"**

---

### Solución 4: Revisar Mensajes de Error

1. **Busca mensajes de error o advertencias** en la pantalla "Confirm"
2. **Revisa si hay algún campo en rojo o con advertencia**
3. **Lee cualquier mensaje de validación que aparezca**

---

## 🎯 Recomendación

**Empieza con la Solución 2:** Desmarca "Disable batches" y vuelve a intentar.

Si eso no funciona, prueba la Solución 1 para verificar el mapeo de columnas.

---

## 📝 Nota

A veces DBeaver requiere que ciertas configuraciones sean compatibles entre sí. "Disable batches" puede estar en conflicto con "Use multi-row value insert".

