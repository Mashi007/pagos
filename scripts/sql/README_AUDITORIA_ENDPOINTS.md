# 📋 Guía de Auditoría: Endpoints que Dependen de Base de Datos

> **Auditoría completa de endpoints y uso de columnas sincronizadas en FASE 3**  
> Última actualización: 2026-01-11

---

## 🎯 Objetivo

Realizar una auditoría completa de todos los endpoints que dependen de base de datos para:
1. Identificar qué endpoints usan qué modelos
2. Verificar qué columnas sincronizadas en FASE 3 están siendo utilizadas en el código
3. Identificar oportunidades de mejora usando columnas disponibles pero no utilizadas
4. Verificar el uso real de columnas en la base de datos (valores no nulos)

---

## 📋 Scripts Disponibles

### **1. Script Python: `auditoria_endpoints_bd.py`**

**Ubicación:** `scripts/python/auditoria_endpoints_bd.py`

**Qué hace:**
- Analiza todos los archivos Python en `backend/app/api/v1/endpoints/`
- Identifica endpoints que usan `db: Session = Depends(get_db)`
- Detecta qué modelos ORM se utilizan en cada endpoint
- Busca uso de columnas sincronizadas en FASE 3:
  - 21 columnas de `Pago`
  - 2 columnas de `Cuota`
  - 6 columnas ML de `Prestamo`
- Genera un reporte completo en Markdown

**Cómo ejecutar:**
```bash
python scripts/python/auditoria_endpoints_bd.py
```

**Salida:**
- Reporte guardado en: `Documentos/Auditorias/2025-01/AUDITORIA_ENDPOINTS_BD.md`

---

### **2. Script SQL: `FASE3_AUDITORIA_COLUMNAS_EN_USO.sql`**

**Ubicación:** `scripts/sql/FASE3_AUDITORIA_COLUMNAS_EN_USO.sql`

**Qué hace:**
- Verifica el uso real de columnas sincronizadas en la base de datos
- Cuenta registros con valores no nulos para cada columna
- Calcula porcentaje de uso de cada columna
- Identifica índices en columnas sincronizadas
- Categoriza columnas por nivel de uso (ALTO, MEDIO, BAJO, SIN USO)

**Cómo ejecutar:**
1. Abrir DBeaver o tu cliente SQL preferido
2. Conectarse a la base de datos
3. Ejecutar el script completo

**Pasos del script:**
- **PASO 1:** Verificar columnas de PAGOS con datos
- **PASO 2:** Verificar uso real de columnas PAGOS (valores no nulos)
- **PASO 3:** Verificar uso real de columnas CUOTAS
- **PASO 4:** Verificar índices en columnas sincronizadas
- **PASO 5:** Resumen de columnas más usadas vs menos usadas

---

## 📊 Resultados de la Auditoría

### **Estadísticas Generales (Última ejecución)**

- **Total de archivos analizados:** 34
- **Archivos con endpoints:** 22
- **Total de endpoints con DB:** 213

### **Modelos Más Usados**

1. **Prestamo:** 8 archivos
2. **Cliente:** 5 archivos
3. **Cuota:** 3 archivos
4. **Pago:** 3 archivos

### **Columnas Sincronizadas en Uso (Código)**

**Columnas Pago usadas:** 1 de 21
- `monto` ✅

**Columnas Cuota usadas:** 0 de 2
- ⚠️ Ninguna columna sincronizada está siendo usada

**Columnas Prestamo ML usadas:** 6 de 6
- ✅ Todas las columnas ML están en uso

### **Columnas No Usadas en Código**

**Columnas Pago no usadas (20):**
- banco, codigo_pago, comprobante, creado_en, descuento
- dias_mora, documento, fecha_vencimiento, hora_pago, metodo_pago
- monto_capital, monto_cuota_programado, monto_interes, monto_mora
- monto_total, numero_operacion, observaciones, referencia_pago
- tasa_mora, tipo_pago

**Columnas Cuota no usadas (2):**
- actualizado_en, creado_en

---

## 🔍 Interpretación de Resultados

### **¿Qué significa "columna no usada"?**

Una columna está marcada como "no usada" si:
- No aparece en el código de los endpoints analizados
- No se accede directamente como `Pago.columna` o `pago.columna`
- No se usa en queries SQLAlchemy

**Importante:** Esto NO significa que:
- La columna no exista en la base de datos
- La columna no tenga datos
- La columna no sea importante

### **¿Por qué hay columnas no usadas?**

1. **Columnas nuevas:** Acabamos de sincronizarlas en FASE 3
2. **Funcionalidades pendientes:** Pueden estar planificadas para el futuro
3. **Uso indirecto:** Pueden usarse en servicios o utilidades no analizadas
4. **Datos históricos:** Pueden contener datos importantes pero no accedidos por endpoints

---

## 💡 Recomendaciones

### **1. Priorizar Uso de Columnas con Datos**

Ejecutar `FASE3_AUDITORIA_COLUMNAS_EN_USO.sql` para identificar:
- Columnas con alto porcentaje de uso en BD (>50%)
- Columnas con datos pero no usadas en código
- Oportunidades de mejora en endpoints

### **2. Endpoints que Podrían Beneficiarse**

**Endpoints de Pagos (`pagos.py`):**
- `listar_pagos`: Podría filtrar/ordenar por `metodo_pago`, `tipo_pago`, `banco`
- `crear_pago`: Podría usar `codigo_pago`, `numero_operacion`, `referencia_pago`
- `obtener_estadisticas_pagos`: Podría usar `monto_capital`, `monto_interes`, `monto_mora`

**Endpoints de Dashboard (`dashboard.py`):**
- `obtener_cobros_diarios`: Podría usar `hora_pago` para análisis temporal
- `obtener_pagos_conciliados`: Podría usar `comprobante`, `documento`

**Endpoints de Reportes (`reportes.py`):**
- `reporte_pagos`: Podría incluir todas las columnas sincronizadas
- `reporte_financiero`: Podría usar `monto_capital`, `monto_interes`, `descuento`

### **3. Columnas de Cuota**

Las columnas `creado_en` y `actualizado_en` en `Cuota` podrían usarse para:
- Auditoría de cambios en cuotas
- Tracking de creación de cuotas
- Análisis de tiempos de procesamiento

---

## 📝 Checklist de Auditoría

- [ ] Ejecutar script Python de auditoría
- [ ] Revisar reporte generado (`AUDITORIA_ENDPOINTS_BD.md`)
- [ ] Ejecutar script SQL de uso real de columnas
- [ ] Comparar uso en código vs uso en BD
- [ ] Identificar columnas con datos pero no usadas
- [ ] Planificar mejoras en endpoints prioritarios
- [ ] Documentar decisiones sobre columnas no usadas

---

## 🔄 Actualización Periódica

**Recomendación:** Ejecutar la auditoría:
- Después de cada FASE de sincronización
- Antes de implementar nuevas funcionalidades
- Mensualmente para tracking de uso

**Comando rápido:**
```bash
python scripts/python/auditoria_endpoints_bd.py
```

---

## 📚 Archivos Relacionados

- `scripts/python/auditoria_endpoints_bd.py` - Script de auditoría Python
- `scripts/sql/FASE3_AUDITORIA_COLUMNAS_EN_USO.sql` - Script SQL de uso real
- `Documentos/Auditorias/2025-01/AUDITORIA_ENDPOINTS_BD.md` - Reporte generado
- `scripts/sql/FASE3_DIAGNOSTICO_COLUMNAS.sql` - Diagnóstico de columnas
- `scripts/sql/README_FASE3.md` - Documentación de FASE 3

---

**Última revisión:** 2026-01-11
