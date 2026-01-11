====================================================================================================
REPORTE DE DISCREPANCIAS: BASE DE DATOS vs MODELOS ORM
====================================================================================================

Fecha: 2026-01-11 11:32:22

RESUMEN EJECUTIVO
----------------------------------------------------------------------------------------------------
Total discrepancias: 9
  - ALTA (Críticas): 4
  - MEDIA (Importantes): 5

DISCREPANCIAS POR TIPO
====================================================================================================

[ORM_SIN_BD] 4 casos
----------------------------------------------------------------------------------------------------
  Tabla: prestamos
  Columna: ml_impago_nivel_riesgo_calculado
  Severidad: ALTA
  Descripción: Columna ml_impago_nivel_riesgo_calculado existe en modelo ORM pero no en BD prestamos

  Tabla: prestamos
  Columna: ml_impago_probabilidad_calculada
  Severidad: ALTA
  Descripción: Columna ml_impago_probabilidad_calculada existe en modelo ORM pero no en BD prestamos

  Tabla: prestamos
  Columna: ml_impago_calculado_en
  Severidad: ALTA
  Descripción: Columna ml_impago_calculado_en existe en modelo ORM pero no en BD prestamos

  Tabla: prestamos
  Columna: ml_impago_modelo_id
  Severidad: ALTA
  Descripción: Columna ml_impago_modelo_id existe en modelo ORM pero no en BD prestamos


[NULLABLE_DIFERENTE] 5 casos
----------------------------------------------------------------------------------------------------
  Tabla: notificaciones
  Columna: id
  Severidad: MEDIA
  Descripción: Columna id: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: notificaciones
  Columna: tipo
  Severidad: MEDIA
  Descripción: Columna tipo: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: notificaciones
  Columna: categoria
  Severidad: MEDIA
  Descripción: Columna categoria: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: notificaciones
  Columna: estado
  Severidad: MEDIA
  Descripción: Columna estado: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

  Tabla: notificaciones
  Columna: prioridad
  Severidad: MEDIA
  Descripción: Columna prioridad: nullable en BD=False, en ORM=True
  Nullable BD: False, ORM: True

====================================================================================================
RECOMENDACIONES PARA CORRECCIÓN
====================================================================================================

2. COLUMNAS EN MODELO ORM SIN BD (ALTA PRIORIDAD)
----------------------------------------------------------------------------------------------------
  Estas columnas están en modelos ORM pero no existen en BD.
  ACCIÓN: Verificar si deben agregarse a BD o removerse del modelo.

  - prestamos.ml_impago_nivel_riesgo_calculado
  - prestamos.ml_impago_probabilidad_calculada
  - prestamos.ml_impago_calculado_en
  - prestamos.ml_impago_modelo_id

3. DIFERENCIAS EN NULLABLE (MEDIA PRIORIDAD)
----------------------------------------------------------------------------------------------------
  Estas columnas tienen diferente configuración de nullable.
  ACCIÓN: Sincronizar nullable entre BD y ORM.

  - notificaciones.id: BD=False, ORM=True
  - notificaciones.tipo: BD=False, ORM=True
  - notificaciones.categoria: BD=False, ORM=True
  - notificaciones.estado: BD=False, ORM=True
  - notificaciones.prioridad: BD=False, ORM=True

====================================================================================================
PLAN DE ACCIÓN
====================================================================================================

1. PRIORIDAD ALTA - Corregir discrepancias críticas:
   - Agregar columnas faltantes en modelos ORM
   - Verificar columnas en ORM que no existen en BD

2. PRIORIDAD MEDIA - Sincronizar configuración:
   - Corregir diferencias en nullable
   - Corregir diferencias en longitudes

3. VERIFICACIÓN:
   - Ejecutar este script nuevamente después de correcciones
   - Verificar que no haya errores en aplicación

====================================================================================================
FIN DEL REPORTE
====================================================================================================