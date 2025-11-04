# ✅ INSTRUCCIONES: IMPLEMENTACIÓN DE TABLAS OFICIALES DEL DASHBOARD

**Fecha:** 2025-01-04

---

## 📋 RESUMEN DE LO CREADO

He creado todo el código necesario para migrar el dashboard a usar **tablas oficiales de reporting**:

1. ✅ **Scripts SQL** para crear las tablas en DBeaver
2. ✅ **Scripts SQL** para actualizar las tablas
3. ✅ **Modelos SQLAlchemy** para las tablas oficiales
4. ✅ **Ejemplo de migración** del endpoint `evolucion-morosidad`

---

## 🚀 PASOS PARA IMPLEMENTAR

### **PASO 1: Crear las Tablas en DBeaver**

1. Abrir DBeaver
2. Conectarse a tu base de datos
3. Abrir el archivo: `scripts/sql/CREAR_TABLAS_OFICIALES_DASHBOARD.sql`
4. Seleccionar todo el contenido (Ctrl+A)
5. Ejecutar (F5 o botón "Execute SQL script")

**Verificar que se crearon:**
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_name LIKE 'dashboard_%';
```

Deberías ver 9 tablas:
- `dashboard_morosidad_mensual`
- `dashboard_cobranzas_mensuales`
- `dashboard_kpis_diarios`
- `dashboard_financiamiento_mensual`
- `dashboard_morosidad_por_analista`
- `dashboard_prestamos_por_concesionario`
- `dashboard_pagos_mensuales`
- `dashboard_cobros_por_analista`
- `dashboard_metricas_acumuladas`

---

### **PASO 2: Poblar las Tablas con Datos**

1. Abrir el archivo: `scripts/sql/ACTUALIZAR_TABLAS_OFICIALES_DASHBOARD.sql`
2. Seleccionar todo el contenido
3. Ejecutar (F5)

**Verificar que se poblaron:**
```sql
SELECT 
    'dashboard_morosidad_mensual' as tabla,
    COUNT(*) as registros,
    MAX(fecha_actualizacion) as ultima_actualizacion
FROM dashboard_morosidad_mensual;
```

---

### **PASO 3: Modificar los Endpoints Restantes**

Ya modifiqué el endpoint `/api/v1/dashboard/evolucion-morosidad` como ejemplo.

**Necesitas modificar estos endpoints similares:**

1. `/api/v1/dashboard/morosidad-por-analista`
   - Usar: `DashboardMorosidadPorAnalista`

2. `/api/v1/dashboard/prestamos-por-concesionario`
   - Usar: `DashboardPrestamosPorConcesionario`

3. `/api/v1/dashboard/cobranzas-mensuales`
   - Usar: `DashboardCobranzasMensuales`

4. `/api/v1/dashboard/financiamiento-tendencia-mensual`
   - Usar: `DashboardFinanciamientoMensual`

5. `/api/v1/dashboard/evolucion-pagos`
   - Usar: `DashboardPagosMensuales`

6. `/api/v1/dashboard/kpis-principales`
   - Usar: `DashboardKPIsDiarios`

**Patrón a seguir (igual que `evolucion-morosidad`):**
```python
# ✅ ANTES (consulta directa):
query = db.query(Cuota).join(Prestamo).filter(...)

# ✅ DESPUÉS (tabla oficial):
query = db.query(DashboardMorosidadMensual).filter(...)
```

---

### **PASO 4: Configurar Actualización Automática**

Las tablas oficiales deben actualizarse periódicamente. Opciones:

#### **Opción A: Manual (para empezar)**
```sql
-- Ejecutar cuando necesites actualizar
SELECT actualizar_tablas_oficiales_dashboard();
```

#### **Opción B: Cron Job (recomendado)**
```bash
# Agregar a crontab (ejecutar diariamente a las 2 AM)
0 2 * * * psql -U usuario -d database -f /ruta/ACTUALIZAR_TABLAS_OFICIALES_DASHBOARD.sql
```

#### **Opción C: Endpoint Administrativo**
Crear endpoint en el backend:
```python
@router.post("/admin/actualizar-tablas-oficiales")
def actualizar_tablas_oficiales(db: Session = Depends(get_db)):
    db.execute(text("SELECT actualizar_tablas_oficiales_dashboard()"))
    db.commit()
    return {"status": "Tablas actualizadas"}
```

---

## 📊 ARCHIVOS CREADOS

### **1. Scripts SQL:**
- ✅ `scripts/sql/CREAR_TABLAS_OFICIALES_DASHBOARD.sql` - Crear tablas
- ✅ `scripts/sql/ACTUALIZAR_TABLAS_OFICIALES_DASHBOARD.sql` - Actualizar datos

### **2. Modelos Python:**
- ✅ `backend/app/models/dashboard_oficial.py` - Modelos SQLAlchemy

### **3. Código Backend:**
- ✅ `backend/app/api/v1/endpoints/dashboard.py` - Endpoint `evolucion-morosidad` migrado

### **4. Documentación:**
- ✅ `MIGRACION_TABLAS_OFICIALES_DASHBOARD.md` - Guía completa
- ✅ `INSTRUCCIONES_TABLAS_OFICIALES.md` - Este archivo

---

## ⚠️ IMPORTANTE

### **Antes de Usar en Producción:**

1. **Probar localmente primero**
2. **Verificar que las tablas se crearon correctamente**
3. **Verificar que los datos se poblaron**
4. **Probar que el endpoint migrado funciona**
5. **Migrar endpoints uno por uno**
6. **Mantener fallback a consulta original** (ya incluido en el código)

### **Filtros Opcionales:**

⚠️ **NOTA:** Los filtros opcionales (`analista`, `concesionario`, `modelo`) pueden requerir:
- Tablas oficiales adicionales con estos filtros pre-aplicados
- O mantener consulta original cuando hay filtros

Por ahora, el endpoint `evolucion-morosidad` migrado funciona sin filtros. Si necesitas filtros, puedes:
1. Crear tablas adicionales con filtros
2. O usar el fallback cuando hay filtros

---

## ✅ VERIFICACIÓN

### **Verificar Tablas Creadas:**
```sql
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = t.table_name) as columnas
FROM information_schema.tables t
WHERE table_name LIKE 'dashboard_%'
ORDER BY table_name;
```

### **Verificar Datos:**
```sql
SELECT 
    'dashboard_morosidad_mensual' as tabla,
    COUNT(*) as registros,
    MAX(fecha_actualizacion) as ultima_actualizacion
FROM dashboard_morosidad_mensual
UNION ALL
SELECT 'dashboard_kpis_diarios', COUNT(*), MAX(fecha_actualizacion)
FROM dashboard_kpis_diarios;
```

### **Probar Endpoint:**
```bash
curl http://localhost:8000/api/v1/dashboard/evolucion-morosidad?meses=6
```

---

## 🎯 PRÓXIMOS PASOS

1. ✅ Ejecutar scripts SQL en DBeaver
2. ⏳ Migrar endpoints restantes (usar el ejemplo de `evolucion-morosidad`)
3. ⏳ Configurar actualización automática
4. ⏳ Probar en ambiente de desarrollo
5. ⏳ Desplegar a producción

---

## 📞 SOPORTE

Si encuentras problemas:
1. Verificar que las tablas se crearon
2. Verificar que se poblaron con datos
3. Revisar logs del backend
4. El código tiene fallback automático si las tablas no existen

---

**¡Todo listo para implementar!** 🚀

