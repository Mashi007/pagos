# 🚨 INSTRUCCIONES URGENTES - ERROR EN PRODUCCIÓN

## 🔴 Problema Actual

El sistema en producción está fallando con el error:

```
LookupError: 'ADMINISTRADOR_GENERAL' is not among the defined enum values.
Enum name: userrole. Possible values: USER
```

**Causa**: La base de datos tiene usuarios con roles antiguos, pero el código solo acepta el rol `USER`.

## ✅ Solución Lista

He creado un endpoint de emergencia que arreglará el problema automáticamente.

## 📋 PASOS A SEGUIR (5 minutos)

### 1️⃣ Esperar el Deploy
Primero, espera que Render complete el deploy del commit recién pusheado:
- Commit: `2e5b88d`
- Mensaje: "feat: Agregar migración de emergencia..."

Revisa en: https://dashboard.render.com/

### 2️⃣ Verificar el Estado Actual
Cuando el deploy termine, verifica el estado:

```bash
curl https://pagos-f2qf.onrender.com/api/v1/emergency/check-roles
```

**Respuesta esperada**:
```json
{
  "necesita_migracion": true,
  "distribucion_roles": {
    "ADMINISTRADOR_GENERAL": 1
  },
  "enum_valores": ["ADMINISTRADOR_GENERAL", "GERENTE", "COBRANZAS", "USER"],
  "mensaje": "⚠️ Ejecutar /emergency/migrate-roles"
}
```

### 3️⃣ Ejecutar la Migración
Si `necesita_migracion: true`, ejecuta:

```bash
curl -X POST https://pagos-f2qf.onrender.com/api/v1/emergency/migrate-roles
```

**Respuesta esperada**:
```json
{
  "status": "success",
  "message": "Migración de roles completada exitosamente",
  "estado_inicial": {"ADMINISTRADOR_GENERAL": 1},
  "estado_final": {"USER": 1},
  "acciones": [
    "✅ Todos los usuarios migrados a rol USER",
    "✅ Enum actualizado a solo USER",
    "✅ Usuario itmaster@rapicreditca.com verificado"
  ]
}
```

### 4️⃣ Verificar que Funcionó
Verifica nuevamente:

```bash
curl https://pagos-f2qf.onrender.com/api/v1/emergency/check-roles
```

Debe mostrar:
```json
{
  "necesita_migracion": false,
  "distribucion_roles": {"USER": 1},
  "enum_valores": ["USER"],
  "mensaje": "✅ Sistema correcto"
}
```

### 5️⃣ Probar el Login
Intenta iniciar sesión:
- Email: `itmaster@rapicreditca.com`
- Password: `admin123` (o la contraseña que configuraste)

### 6️⃣ Probar el Endpoint de Clientes
```bash
curl https://pagos-f2qf.onrender.com/api/v1/clientes/
```

Debe responder sin errores de enum.

## 🧹 Limpieza (Después de Verificar)

Una vez que TODO funcione correctamente:

1. **Eliminar archivos de emergencia**:
   ```bash
   rm backend/app/api/v1/endpoints/emergency_migrate_roles.py
   rm backend/scripts/run_migration_production.py
   ```

2. **Actualizar main.py**:
   - Remover: `emergency_migrate_roles,` del import
   - Remover: `app.include_router(emergency_migrate_roles.router, ...)` del registro

3. **Commit y push**:
   ```bash
   git add .
   git commit -m "chore: Limpieza post-migración de roles"
   git push origin main
   ```

## 🔍 Troubleshooting

### Si el endpoint no responde:
- Verifica que el deploy haya terminado
- Revisa los logs en Render Dashboard
- Espera 1-2 minutos para que la app inicie completamente

### Si la migración falla:
- Revisa la respuesta de error
- Verifica la conexión a base de datos
- Revisa los logs del servidor

### Si necesitas ejecutar manualmente:
Si tienes acceso SSH al servidor de producción:
```bash
cd backend
python scripts/run_migration_production.py
```

## 📊 Qué Hace la Migración

1. ✅ Actualiza TODOS los usuarios al rol `USER`
2. ✅ Modifica el enum de PostgreSQL para solo tener `USER`
3. ✅ Elimina el usuario `admin@financiamiento.com` (si existe)
4. ✅ Verifica/crea el usuario `itmaster@rapicreditca.com`
5. ✅ Es seguro: Usa transacciones y hace rollback si algo falla

## ⏱️ Tiempo Estimado

- Deploy nuevo código: 3-5 minutos
- Ejecutar migración: 10-30 segundos
- Verificación: 1-2 minutos
- **TOTAL: 5-10 minutos**

## 🎯 Resultado Final

Después de estos pasos:
- ✅ Sistema completamente funcional
- ✅ Login funcionando
- ✅ Todos los endpoints funcionando
- ✅ Sin errores de enum en logs
- ✅ Base de datos limpia con solo rol `USER`
- ✅ Todos los usuarios con acceso completo

## 📞 Ayuda

Si tienes problemas, revisa:
1. `SOLUCION_ERROR_ENUM_ROLES.md` - Documentación detallada
2. Logs de Render Dashboard
3. Response del endpoint de verificación

---

**NOTA IMPORTANTE**: El endpoint de emergencia NO requiere autenticación por diseño, para poder usarlo incluso si el login está roto. Por eso es crítico eliminarlo después de usarlo.

