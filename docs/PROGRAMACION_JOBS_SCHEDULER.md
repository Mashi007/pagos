# Programación de jobs (APScheduler) — carga, eficiencia y colisiones

Este documento aplica al backend (`backend/app/core/scheduler.py`), líder único (`scheduler_leader.py`) y jobs que lean/escriban BD u APIs externas.

## Objetivo

Cada vez que se añada o modifique un job programado:

1. **Eficiencia:** disparos mínimos necesarios, sin solapar tareas pesadas innecesariamente.
2. **Sin colisión de calendario:** evitar el **mismo minuto** (`hora:minuto`) para **dos callables distintos** en el mismo día (salvo que una sea trivial y no use las mismas tablas).
3. **Según carga:** espaciar jobs **muy pesados** y respetar **dependencias de datos** (p. ej. sync antes de lecturas del snapshot).

## Clasificación de carga (orientativa)

| Nivel | Ejemplos típicos | Regla de espaciado |
|--------|------------------|---------------------|
| **Muy pesado** | Sync masivo desde Google Sheets, auditoría de toda la cartera, recorridos de todos los `prestamos` con escritura | No encadenar dos del mismo nivel en el **mismo minuto**; dejar **≥ 15–40 min** respecto a otra tarea muy pesada que comparta BD intensiva. |
| **Medio** | Snapshots desde tabla `drive`, cachés JSON por dominio, refrescos por lotes acotados | Tras un job **muy pesado**, preferir **≥ 15 min** antes del siguiente medio/pesado. |
| **Ligero** | Limpieza de códigos expirados, housekeeping puntual | Puede ir cerca de otros si no bloquea las mismas filas durante minutos; aun así evitar **mismo minuto** con un job masivo. |

## Dependencias de datos

- Si el job **lee** `drive`, `conciliacion_sheet_*` o datos recién volcados desde Sheets, debe ejecutarse **después** del sync CONCILIACIÓN (o con margen realista si el sync puede durar mucho en miércoles/domingo).
- Documentar en el docstring del `_job_*` y en el bloque de módulo de `scheduler.py` la **relación** “tras X / antes de Y”.

## Colisiones a revisar siempre

1. **Mismo `hora` + `minuto` + día** para dos funciones distintas → desfasar uno (p. ej. `:15`, `:30`, `:40`, `:45`).
2. **Miércoles/domingo 02:00:** sync CONCILIACIÓN; no programar otro job pesado que lea `drive` a las **02:00** exactas.
3. **03:00 diario:** auditoría cartera; no poner otro job pesado a **03:00** en lun–sáb.
4. **04:00 diario:** limpieza de códigos; separar cachés masivos de domingo si hacían cluster (p. ej. `:35` y hora siguiente).
5. **Gmail `:30` entre 06:30 y 19:30:** no coincidir en el mismo minuto con finiquito u otro job crítico si ambos saturan CPU/BD (hoy finiquito es `:00`).

## Eficiencia operativa

- **Un job por responsabilidad** con `id` estable y nombre legible en logs.
- Si la misma lógica debe correr **dos veces al día** (p. ej. finiquito), son **dos `add_job`** con el mismo callable e **ids distintos**; no duplicar triggers idénticos.
- Revisar `ENABLE_*` y documentar en `config.py` la **hora real** cuando el flag afecte al cron.
- Tras cambiar horarios: actualizar **docstring del módulo** `scheduler.py`, **`start_scheduler`**, **log de arranque**, y comentarios en **servicios** invocados si mencionan la hora.

## Orden recomendado en `start_scheduler()`

Registrar jobs en **orden cronológico del flujo nocturno** (facilita revisiones):

1. Finiquito / tareas tempranas lun–sáb si aplica  
2. Sync CONCILIACIÓN (dom/mié)  
3. Cachés o snapshots que dependen de `drive`  
4. Auditoría cartera  
5. Snapshots posteriores a auditoría si deben evitar contención  
6. Limpieza ligera  
7. Cachés masivos dominicales (separados entre sí)  
8. Segunda ventana finiquito / Gmail  

(El orden de registro no cambia la hora de ejecución de APScheduler, pero evita errores al leer el código.)

## Checklist antes de dar por cerrado un cambio de cron

- [ ] ¿Hay otro job el **mismo día a la misma hora y minuto**?
- [ ] ¿Este job **depende** de datos producidos por otro job el mismo día?
- [ ] ¿La **duración típica** del predecesor puede pisar el inicio del siguiente? (Si sí, aumentar hueco.)
- [ ] ¿Actualicé **scheduler.py** (cabecera + triggers), **config.py** (descripciones), y **servicio** si documentaba la hora antigua?
- [ ] ¿Los **ids** de job cambiaron? (Buscar referencias en tests o tooling.)

## Referencia de implementación

- Código: `backend/app/core/scheduler.py`  
- Liderazgo multi-worker: `backend/app/core/scheduler_leader.py`  
- Activación global: `ENABLE_AUTOMATIC_SCHEDULED_JOBS` (`backend/app/core/config.py`, `.env`)
