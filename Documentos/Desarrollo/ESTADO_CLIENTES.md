# ESTADO ACTUAL - MÓDULO CLIENTES

## ✅ COMPLETADO

### Backend:
1. **Script SQL** `ajustar_tabla_clientes.sql` creado
2. **Modelo Cliente** actualizado (nombres unificados, notas NOT NULL)
3. **Schemas** actualizados (validación 2-4 palabras para nombres, max 2 palabras para ocupacion)
4. **Endpoints** actualizados (sincronización estado/activo, fecha_actualizacion manual)

### Frontend:
1. **Interface FormData** actualizada (eliminado `apellidos`)
2. **Campo visual apellidos** eliminado del formulario
3. **Campo nombres** actualizado con label "Nombres y Apellidos (2-4 palabras)"
4. **Placeholder** actualizado: "Ejemplo: Juan Carlos Pérez González"

---

## ⚠️ PENDIENTE

### CRÍTICO - EJECUTAR EN DBEAVER:
```sql
-- Ejecutar script en la base de datos:
-- backend/scripts/ajustar_tabla_clientes.sql
```

### Frontend - FUNCIONALIDAD:
- [ ] Agregar validación 2-4 palabras para nombres (función validateNombres)
- [ ] Agregar validación max 2 palabras para ocupacion (función validateOcupacion)
- [ ] Agregar autoformato (capitalizar primera letra de cada palabra)
- [ ] **NO permitir guardar si no pasa validación**
- [ ] Actualizar campo `notas` para que muestre "NA" por defecto
- [ ] Crear componente `ClientesKPIs.tsx` (4 tarjetas)
- [ ] Agregar columna "Fecha Registro" al dashboard
- [ ] Eliminar CardHeader y CardTitle de tarjeta de búsqueda

---

## 🎯 PRÓXIMOS PASOS

1. **Ejecutar script SQL** en DBeaver
2. **Implementar validaciones** de nombres y ocupacion en frontend
3. **Crear componente KPIs** con diseño de 4 tarjetas
4. **Ajustar dashboard** para mostrar fecha de registro
5. **Probar flujo completo**: crear, editar, eliminar cliente

---

## 📝 NOTAS

- Los cambios ya están commiteados y pusheados a GitHub
- Render debe hacer deploy automático
- Una vez ejecutado el script SQL, el sistema estará funcional

