# Registro de Cambios - Módulo de Auditoría

## Descripción General

Se ha implementado un nuevo módulo de **Registro de Cambios** integrado en el módulo de Auditoría. Este módulo proporciona un registro completo y trazable de todos los cambios realizados en el sistema, con información detallada del usuario, fecha/hora y descripción de cada cambio.

## Componentes Implementados

### 1. Modelo de Base de Datos (`registro_cambios.py`)

**Tabla**: `registro_cambios`

Campos principales:
- `id`: Identificador único (Primary Key)
- `usuario_id`: ID del usuario que realiza el cambio (FK a usuarios)
- `usuario_email`: Email del usuario (desnormalizado para reportes)
- `modulo`: Módulo del sistema afectado (Préstamos, Pagos, Auditoría, etc.)
- `tipo_cambio`: Tipo de operación (CREAR, ACTUALIZAR, ELIMINAR, EXPORTAR, etc.)
- `descripcion`: Descripción legible y detallada del cambio
- `registro_id`: ID del registro específico afectado (opcional)
- `tabla_afectada`: Nombre de la tabla afectada (opcional)
- `campos_anteriores`: Valores anteriores en formato JSON (para cambios)
- `campos_nuevos`: Valores nuevos en formato JSON (para cambios)
- `ip_address`: Dirección IP del cliente (opcional)
- `user_agent`: User Agent del cliente (opcional)
- `fecha_hora`: Timestamp con timezone del cambio
- `vigente`: Flag para marcar cambios como activos o históricos

**Índices**:
- usuario_id (búsqueda por usuario)
- modulo (búsqueda por módulo)
- tipo_cambio (búsqueda por tipo)
- registro_id (búsqueda de cambios de un registro específico)
- fecha_hora (búsqueda por fecha, descendente)
- modulo + fecha_hora (búsqueda combinada)
- usuario_id + fecha_hora (búsqueda combinada)
- vigente (para filtrar cambios activos)

### 2. Servicio (`registro_cambios_service.py`)

**Funciones principales**:

#### `registrar_cambio()`
```python
registrar_cambio(
    db: Session,
    usuario_id: int,
    modulo: str,
    tipo_cambio: str,
    descripcion: str,
    registro_id: Optional[int] = None,
    tabla_afectada: Optional[str] = None,
    campos_anteriores: Optional[Dict[str, Any]] = None,
    campos_nuevos: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> RegistroCambios
```

Registra un nuevo cambio en la base de datos. Automáticamente obtiene el email del usuario desde la BD.

**Ejemplo de uso**:
```python
from app.services.registro_cambios_service import registrar_cambio

cambio = registrar_cambio(
    db=db,
    usuario_id=current_user.id,
    modulo="Préstamos",
    tipo_cambio="ACTUALIZAR",
    descripcion="Actualización de moneda de pago - cambio de USD a BS",
    registro_id=prestamo_id,
    tabla_afectada="prestamos",
    campos_anteriores={"moneda": "USD", "tasa": "2.65"},
    campos_nuevos={"moneda": "BS", "tasa": "2.80"}
)
```

#### `obtener_cambios_recientes()`
```python
obtener_cambios_recientes(
    db: Session,
    modulo: Optional[str] = None,
    usuario_id: Optional[int] = None,
    registro_id: Optional[int] = None,
    limite: int = 100,
) -> list[RegistroCambios]
```

Obtiene los cambios más recientes con filtros opcionales.

### 3. Endpoints API (`registro_cambios.py`)

**Prefijo**: `/auditoria/registro-cambios`

#### **GET** `/` - Listar registros de cambios
```
Parámetros de query:
- skip: int (default: 0)
- limit: int (default: 50, máx: 500)
- modulo: str (optional)
- usuario_id: int (optional)
- tipo_cambio: str (optional)
- registro_id: int (optional)
- fecha_desde: str ISO format (optional)
- fecha_hasta: str ISO format (optional)
- ordenar_por: str (default: "fecha_hora")
- orden: str (default: "desc")

Respuesta:
{
  "items": [
    {
      "id": 1,
      "usuario_id": 5,
      "usuario_email": "usuario@example.com",
      "modulo": "Préstamos",
      "tipo_cambio": "ACTUALIZAR",
      "descripcion": "Cambio de estado de APROBADO a LIQUIDADO",
      "registro_id": 123,
      "tabla_afectada": "prestamos",
      "campos_anteriores": {"estado": "APROBADO"},
      "campos_nuevos": {"estado": "LIQUIDADO"},
      "fecha_hora": "2026-03-31T14:30:00Z",
      "vigente": true
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 50,
  "total_pages": 3
}
```

#### **GET** `/stats` - Estadísticas de cambios
```
Respuesta:
{
  "total_cambios": 1250,
  "cambios_hoy": 45,
  "cambios_esta_semana": 280,
  "cambios_por_modulo": {
    "Préstamos": 500,
    "Pagos": 600,
    "Auditoría": 150
  },
  "cambios_por_usuario": {
    "usuario1@example.com": 300,
    "usuario2@example.com": 250
  },
  "cambios_por_tipo": {
    "ACTUALIZAR": 800,
    "CREAR": 300,
    "ELIMINAR": 100,
    "EXPORTAR": 50
  }
}
```

#### **GET** `/exportar` - Exportar a Excel
```
Parámetros de query:
- modulo: str (optional)
- usuario_id: int (optional)
- tipo_cambio: str (optional)
- fecha_desde: str (optional)
- fecha_hasta: str (optional)

Retorna: Archivo Excel con registros de cambios
```

#### **GET** `/{cambio_id}` - Obtener detalles de un cambio
```
Retorna los detalles completos de un registro de cambio específico.
```

### 4. Migración de Base de Datos

**Archivo**: `backend/sql/038_CREAR_TABLA_REGISTRO_CAMBIOS.sql`

Crea la tabla `registro_cambios` con todos los índices necesarios para optimizar consultas.

## Cómo Usar

### Registrar un cambio en tu código

En cualquier endpoint o servicio que realice cambios, puedes registrar el cambio:

```python
from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.registro_cambios_service import registrar_cambio

@router.put("/prestamos/{prestamo_id}")
def actualizar_prestamo(
    prestamo_id: int,
    datos: PrestamoUpdateSchema,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    # Obtener estado anterior
    prestamo_anterior = db.get(Prestamo, prestamo_id)
    
    # Realizar cambios
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    prestamo.estado = datos.estado
    prestamo.monto = datos.monto
    db.commit()
    
    # Registrar cambio
    registrar_cambio(
        db=db,
        usuario_id=current_user.id,
        modulo="Préstamos",
        tipo_cambio="ACTUALIZAR",
        descripcion=f"Actualización de préstamo #{prestamo_id}: cambio de estado y monto",
        registro_id=prestamo_id,
        tabla_afectada="prestamos",
        campos_anteriores={
            "estado": prestamo_anterior.estado,
            "monto": str(prestamo_anterior.total_financiamiento)
        },
        campos_nuevos={
            "estado": datos.estado,
            "monto": str(datos.monto)
        }
    )
    
    return prestamo
```

### Consultar cambios desde el frontend

```typescript
// Obtener últimos cambios
const response = await fetch('/api/v1/auditoria/registro-cambios?limit=20&modulo=Préstamos', {
  headers: { Authorization: `Bearer ${token}` }
});

// Con filtros
const filtered = await fetch(
  '/api/v1/auditoria/registro-cambios?' +
  'usuario_id=5&' +
  'tipo_cambio=ACTUALIZAR&' +
  'fecha_desde=2026-03-01T00:00:00Z',
  { headers: { Authorization: `Bearer ${token}` } }
);

// Obtener estadísticas
const stats = await fetch('/api/v1/auditoria/registro-cambios/stats', {
  headers: { Authorization: `Bearer ${token}` }
});

// Exportar a Excel
const excel = await fetch(
  '/api/v1/auditoria/registro-cambios/exportar?modulo=Préstamos',
  { headers: { Authorization: `Bearer ${token}` } }
);
```

## Estructura en UI (Recomendado)

La información debe mostrarse en una tabla con las siguientes columnas:

| Usuario | Fecha y Hora | Módulo | Tipo de Cambio | Descripción | Registro ID | Detalles |
|---------|-------------|--------|-----------------|-------------|------------|----------|
| usuario@example.com | 31/03/2026 14:30:00 | Préstamos | ACTUALIZAR | Cambio de estado a LIQUIDADO | 123 | Ver JSON |
| admin@example.com | 31/03/2026 14:25:00 | Pagos | CREAR | Pago registrado manualmente | 456 | Ver JSON |

## Seguridad

- ✅ Todos los endpoints requieren autenticación (`Depends(get_current_user)`)
- ✅ Se registra automáticamente el usuario autenticado
- ✅ Los emails se desnormalizan para facilitar reportes
- ✅ Se puede registrar IP y User Agent para auditoría adicional
- ✅ Los cambios son append-only (no se pueden borrar, solo marcar como no vigentes)

## Próximos Pasos (Opcionales)

1. **Frontend Component**: Crear componente React para visualizar el registro de cambios
2. **Notificaciones**: Alertar a administradores sobre cambios críticos
3. **Webhooks**: Disparar webhooks cuando se registren ciertos tipos de cambios
4. **Integración**: Registrar cambios automáticamente en endpoints existentes
5. **Reports**: Crear reportes de cambios por módulo/usuario/fecha

## Archivos Creados/Modificados

✅ **Creados**:
- `backend/app/models/registro_cambios.py` - Modelo ORM
- `backend/app/services/registro_cambios_service.py` - Servicio de negocio
- `backend/app/api/v1/endpoints/registro_cambios.py` - Endpoints API
- `backend/sql/038_CREAR_TABLA_REGISTRO_CAMBIOS.sql` - Migración SQL

✅ **Modificados**:
- `backend/app/api/v1/__init__.py` - Registrar nuevo router
- `backend/app/models/__init__.py` - Importar nuevo modelo

## Notas Importantes

1. **Ejecutar la migración SQL** antes de usar este módulo:
   ```bash
   psql -d tu_base_datos -f backend/sql/038_CREAR_TABLA_REGISTRO_CAMBIOS.sql
   ```

2. El campo `usuario_email` se desnormaliza automáticamente desde la tabla `usuarios` para facilitar reportes sin joins

3. Los campos `campos_anteriores` y `campos_nuevos` están en JSONB para máxima flexibilidad

4. El sistema registra automáticamente la fecha/hora con timezone de PostgreSQL

5. Los índices están optimizados para las búsquedas más comunes (usuario + fecha, módulo + fecha)
