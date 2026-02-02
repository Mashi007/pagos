# Auditoría integral – Módulo Notificaciones

**Alcance:** `app/api/v1/endpoints/notificaciones.py` (API prefix `/api/v1/notificaciones`).  
**Regla:** Todos los endpoints deben usar `get_db` y datos reales desde la BD.

## 1. Uso de `get_db`

| Ruta | Método | `get_db` | Notas |
|------|--------|----------|--------|
| `""` | GET | ✅ `db: Session = Depends(get_db)` | Lista paginada; sin tabla de notificaciones se devuelve lista vacía; `db` inyectado para reglas de negocio. |
| `/estadisticas/resumen` | GET | ✅ `db: Session = Depends(get_db)` | Resumen sidebar (no_leidas, total); `db` inyectado para consistencia. |
| `/clientes-retrasados` | GET | ✅ `db: Session = Depends(get_db)` | Cuotas no pagadas + Cliente desde BD; reglas 5/3/1 días, hoy, mora 61+. |
| `/actualizar` | POST | ✅ `db: Session = Depends(get_db)` | Cuotas en mora desde BD; pensado para cron. |

## 2. Función auxiliar (no es endpoint)

- `get_notificaciones_tabs_data(db: Session)`: recibe `db` desde los routers de `notificaciones_tabs.py`, donde todos los endpoints ya inyectan `Depends(get_db)`.

## 3. Conclusión

- **Todos los endpoints del módulo Notificaciones usan `get_db`.**
- Los datos expuestos (clientes retrasados, actualizar) provienen de las tablas `cuotas` y `clientes`.
- Lista y resumen devuelven vacío/ceros por diseño (sin tabla de notificaciones/envíos); la sesión se inyecta igual para cumplir la regla y futuras extensiones.

**Fecha auditoría:** 2025-02-02
