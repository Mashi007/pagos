# ⚡ Guía Rápida: Registro de Cambios en Auditoría

## ✅ Lo que se ha implementado

He creado un **módulo completo de Registro de Cambios** integrado al módulo de Auditoría que te permite:

1. **Registrar todos los cambios** del sistema con trazabilidad completa
2. **Capturar automáticamente**: Usuario que realiza el cambio, Fecha y Hora (con timezone), Descripción detallada
3. **Consultar cambios** mediante API REST con filtros flexibles
4. **Exportar a Excel** para reportes y análisis
5. **Ver estadísticas** de cambios por módulo, usuario y tipo

## 📁 Archivos Creados

```
backend/
├── app/
│   ├── models/
│   │   └── registro_cambios.py          ✨ NUEVO - Modelo ORM
│   ├── services/
│   │   └── registro_cambios_service.py  ✨ NUEVO - Lógica de negocio
│   └── api/v1/endpoints/
│       └── registro_cambios.py          ✨ NUEVO - Endpoints API
└── sql/
    └── 038_CREAR_TABLA_REGISTRO_CAMBIOS.sql  ✨ NUEVO - Migración BD
```

## 🚀 Pasos para activar

### Paso 1: Ejecutar la migración SQL
```bash
psql -d nombre_base_datos -f backend/sql/038_CREAR_TABLA_REGISTRO_CAMBIOS.sql
```

O si usas un cliente GUI (DBeaver, pgAdmin, etc.), ejecuta el contenido del archivo SQL.

### Paso 2: Reiniciar el servidor backend
```bash
# Detener servidor actual
# Iniciar nuevamente
python -m uvicorn app.main:app --reload
```

### Paso 3: Verificar la API
Accede a `http://localhost:8000/docs` y busca `/auditoria/registro-cambios` en la sección de Auditoria.

## 📊 API Endpoints Disponibles

### 1. **Listar cambios**
```
GET /api/v1/auditoria/registro-cambios?limit=50&modulo=Préstamos
```

### 2. **Obtener estadísticas**
```
GET /api/v1/auditoria/registro-cambios/stats
```

### 3. **Exportar a Excel**
```
GET /api/v1/auditoria/registro-cambios/exportar?modulo=Préstamos
```

### 4. **Ver detalles de un cambio**
```
GET /api/v1/auditoria/registro-cambios/{cambio_id}
```

## 💻 Cómo registrar cambios en tu código

### Ejemplo 1: En un endpoint que actualiza préstamos

```python
from app.services.registro_cambios_service import registrar_cambio

@router.put("/prestamos/{prestamo_id}")
def actualizar_prestamo(
    prestamo_id: int,
    datos: PrestamoUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    # Obtener estado anterior
    prestamo = db.get(Prestamo, prestamo_id)
    estado_anterior = prestamo.estado
    
    # Realizar cambios
    prestamo.estado = datos.estado
    db.commit()
    
    # ✨ Registrar cambio automáticamente
    registrar_cambio(
        db=db,
        usuario_id=current_user.id,
        modulo="Préstamos",
        tipo_cambio="ACTUALIZAR",
        descripcion=f"Estado cambiado de {estado_anterior} a {datos.estado}",
        registro_id=prestamo_id,
        tabla_afectada="prestamos",
        campos_anteriores={"estado": estado_anterior},
        campos_nuevos={"estado": datos.estado}
    )
    
    return {"success": True}
```

### Ejemplo 2: En un servicio que crea registros

```python
from app.services.registro_cambios_service import registrar_cambio

def crear_pago(db: Session, usuario_id: int, monto: float):
    # Crear pago
    pago = Pago(monto=monto, estado="PENDIENTE")
    db.add(pago)
    db.commit()
    db.refresh(pago)
    
    # ✨ Registrar el cambio
    registrar_cambio(
        db=db,
        usuario_id=usuario_id,
        modulo="Pagos",
        tipo_cambio="CREAR",
        descripcion=f"Nuevo pago creado por ${monto:.2f}",
        registro_id=pago.id,
        tabla_afectada="pagos",
        campos_nuevos={"id": pago.id, "monto": monto, "estado": "PENDIENTE"}
    )
    
    return pago
```

## 📋 Estructura de datos

### Tabla: `registro_cambios`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | Identificador único |
| usuario_id | INTEGER FK | Usuario que realiza el cambio |
| usuario_email | VARCHAR(255) | Email del usuario (para reportes) |
| modulo | VARCHAR(100) | Módulo afectado (Préstamos, Pagos, etc.) |
| tipo_cambio | VARCHAR(50) | CREAR, ACTUALIZAR, ELIMINAR, EXPORTAR |
| descripcion | TEXT | Descripción legible del cambio |
| registro_id | INTEGER | ID del registro afectado |
| tabla_afectada | VARCHAR(100) | Tabla de BD afectada |
| campos_anteriores | JSONB | Valores anteriores {key: value} |
| campos_nuevos | JSONB | Valores nuevos {key: value} |
| fecha_hora | TIMESTAMP | Fecha y hora exacta |
| vigente | BOOLEAN | True = activo, False = histórico |

## 🎯 Casos de uso

### ✅ Auditoría Completa
Cada cambio queda registrado con:
- **Quién**: Email del usuario
- **Cuándo**: Fecha y hora exacta
- **Qué**: Descripción clara del cambio
- **Antes/Después**: Valores anteriores y nuevos

### ✅ Reportes
Exporta a Excel y analiza:
- Cambios por usuario (quién es el más activo)
- Cambios por módulo (dónde hay más movimiento)
- Cambios por tipo (crear vs actualizar vs eliminar)
- Cambios en un período específico

### ✅ Trazabilidad
Rastrea cualquier problema:
- "¿Quién cambió el estado de liquidado a aprobado?"
- "¿Cuándo se eliminó este pago?"
- "¿Qué cambios hizo Juan en préstamos hoy?"

## 🔐 Seguridad

✅ Autenticación requerida en todos los endpoints  
✅ Se registra automáticamente el usuario autenticado  
✅ Cambios append-only (no se pueden borrar, solo marcar como históricos)  
✅ IP y User Agent registrados (opcional, para análisis posterior)

## 📈 Siguiente paso: Integración con componente React

Para visualizar en el dashboard:

```typescript
// frontend/src/hooks/useRegistroCambios.ts
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

export function useRegistroCambios(modulo?: string) {
  return useQuery({
    queryKey: ['registro-cambios', modulo],
    queryFn: () =>
      apiClient.get('/auditoria/registro-cambios', {
        params: { modulo, limit: 50 }
      }),
  });
}

export function useRegistroCambiosStats() {
  return useQuery({
    queryKey: ['registro-cambios-stats'],
    queryFn: () =>
      apiClient.get('/auditoria/registro-cambios/stats'),
  });
}
```

```typescript
// frontend/src/components/auditoria/RegistroCambiosTable.tsx
export function RegistroCambiosTable() {
  const { data, isLoading } = useRegistroCambios('Préstamos');

  if (isLoading) return <div>Cargando...</div>;

  return (
    <table>
      <thead>
        <tr>
          <th>Usuario</th>
          <th>Fecha y Hora</th>
          <th>Tipo Cambio</th>
          <th>Descripción</th>
        </tr>
      </thead>
      <tbody>
        {data?.items.map(cambio => (
          <tr key={cambio.id}>
            <td>{cambio.usuario_email}</td>
            <td>{new Date(cambio.fecha_hora).toLocaleString()}</td>
            <td>{cambio.tipo_cambio}</td>
            <td>{cambio.descripcion}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

## ❓ Preguntas Frecuentes

**P: ¿Se registran automáticamente los cambios?**  
R: No, debes llamar manualmente a `registrar_cambio()` en tus endpoints. Esto te da control total sobre qué registrar.

**P: ¿Puedo ver quién realizó un cambio?**  
R: Sí, todos los cambios incluyen `usuario_email`, así que siempre sabes quién lo hizo.

**P: ¿Se pueden eliminar registros de cambios?**  
R: No, son append-only. Puedes marcar como no vigentes, pero no se pueden borrar.

**P: ¿Cuánto espacio usa la tabla?**  
R: Los JSONB son eficientes, ~1KB por registro. Guarda años de datos sin problema.

## 📞 Soporte

Para más detalles, revisa: `IMPLEMENTACION_REGISTRO_CAMBIOS.md`
