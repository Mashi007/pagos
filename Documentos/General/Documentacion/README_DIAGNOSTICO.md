# Scripts de Diagnóstico y Ajuste para Dashboard

Este directorio contiene scripts para diagnosticar y ajustar problemas con el dashboard de "Distribución de Financiamiento por Rangos".

## Scripts Disponibles

### 1. `diagnostico_dashboard_rangos.py`
Script de diagnóstico completo que verifica:
- Total de préstamos aprobados
- Préstamos con total_financiamiento válido
- Análisis de fechas (fecha_registro, fecha_aprobacion, fecha_base_calculo)
- Préstamos en rango del año actual
- Distribución de montos por rangos
- Recomendaciones para resolver problemas

**Uso:**
```bash
cd backend
python scripts/diagnostico_dashboard_rangos.py
```

### 2. `ajustar_fechas_prestamos.py`
Script para ajustar fechas de préstamos que pueden estar causando problemas:
- Asigna fechas a préstamos que no tienen ninguna fecha
- Normaliza fechas inconsistentes

**Uso (modo dry-run - solo muestra qué haría):**
```bash
cd backend
python scripts/ajustar_fechas_prestamos.py
```

**Uso (ejecutar cambios reales):**
```bash
cd backend
python scripts/ajustar_fechas_prestamos.py --execute
```

**Opciones:**
- `--execute`: Ejecutar cambios (por defecto es modo dry-run)
- `--solo-fechas-faltantes`: Solo ajustar préstamos sin fecha
- `--solo-inconsistentes`: Solo normalizar fechas inconsistentes

### 3. `test_endpoint_rangos.py`
Script para probar el endpoint `/api/v1/dashboard/financiamiento-por-rangos`:
- Prueba diferentes combinaciones de filtros
- Verifica que el endpoint responda correctamente
- Muestra estadísticas de la respuesta

**Uso:**
```bash
cd backend
python scripts/test_endpoint_rangos.py
```

**Opciones:**
- `--url`: URL base del backend (default: http://localhost:8000)
- `--token`: Token de autenticación (si es necesario)

## Flujo de Trabajo Recomendado

1. **Diagnosticar el problema:**
   ```bash
   python scripts/diagnostico_dashboard_rangos.py
   ```

2. **Revisar los resultados** y entender qué está causando el problema

3. **Si hay préstamos sin fecha o con fechas inconsistentes:**
   ```bash
   # Primero ver qué haría (dry-run)
   python scripts/ajustar_fechas_prestamos.py

   # Si está bien, ejecutar los cambios
   python scripts/ajustar_fechas_prestamos.py --execute
   ```

4. **Probar el endpoint:**
   ```bash
   python scripts/test_endpoint_rangos.py
   ```

5. **Verificar en el dashboard** que los datos se muestren correctamente

## Problemas Comunes y Soluciones

### Problema: "No hay datos disponibles" en el dashboard

**Posibles causas:**
1. No hay préstamos aprobados en la base de datos
2. Los préstamos no tienen total_financiamiento > 0
3. Los préstamos no tienen fechas en el rango del período seleccionado
4. Los filtros de fecha están excluyendo todos los préstamos

**Solución:**
- Ejecutar `diagnostico_dashboard_rangos.py` para identificar la causa
- Si hay préstamos sin fecha, usar `ajustar_fechas_prestamos.py`
- Verificar que el período seleccionado en el dashboard sea correcto

### Problema: El endpoint retorna 0 préstamos

**Posibles causas:**
1. Los filtros de fecha son demasiado restrictivos
2. Hay un error en la lógica de filtros del backend
3. Los préstamos tienen todas las fechas NULL

**Solución:**
- Revisar los logs del backend
- Ejecutar `test_endpoint_rangos.py` para probar diferentes filtros
- Verificar que los filtros de fecha manejen correctamente los NULLs

## Notas Importantes

- **Siempre hacer backup** antes de ejecutar scripts que modifican datos
- **Usar modo dry-run primero** para ver qué cambios se harían
- **Revisar los logs del backend** para más información sobre errores
- Los scripts requieren que el backend esté configurado correctamente con acceso a la base de datos

