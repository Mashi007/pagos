# CHECKLIST DE DEPLOY - PAGOS CONCILIADOS

## Pre-Deploy ✅

- [x] Código modificado sin errores de linting
- [x] Sin cambios en migraciones necesarios
- [x] Cambios compatibles con estructura actual de BD
- [x] Tests unitarios pasados (manual verification)
- [x] Documentación completa creada

---

## Deploy en Render (rapicredit.onrender.com)

### Paso 1: Push del Código
```bash
# En tu máquina local
git push origin main

# Verificar en GitHub
# https://github.com/tu-repo/pagos
```

### Paso 2: Esperar Build Automático
- Render detectará el push automáticamente
- Build toma ~2-3 minutos
- Monitorear en: https://dashboard.render.com/

### Paso 3: Verificar Deployment
```bash
# 1. Verificar que la API está activa
curl -X GET "https://rapicredit.onrender.com/health" \
  -H "Content-Type: application/json"

# Esperado: {"status": "ok"}

# 2. Verificar el nuevo endpoint
curl -X GET "https://rapicredit.onrender.com/api/v1/prestamos/4601/cuotas" \
  -H "Authorization: Bearer <token>"

# Esperado: Array de cuotas con "pago_conciliado" y "pago_monto_conciliado"
```

### Paso 4: Testing Manual en Frontend
1. Ir a https://rapicredit.onrender.com/pagos/prestamos
2. Buscar préstamo #4601
3. Hacer click en "Detalles del Préstamo"
4. Ir a pestaña "Tabla de Amortización"
5. Verificar que columna "Pago conciliado" muestra montos en lugar de "—"

---

## Validaciones Post-Deploy

### ✅ Checklist Funcional

- [ ] Tabla de amortización carga sin errores
- [ ] Columna "Pago conciliado" muestra valores
- [ ] Montos coinciden con pagos registrados
- [ ] No aparecen errores en consola del navegador
- [ ] Exportar Excel y PDF funcionan
- [ ] Otros préstamos se pueden visualizar sin problemas

### ✅ Checklist de Performance

- [ ] Página carga en < 3 segundos
- [ ] Sin lags al cargar tabla
- [ ] Exportaciones funcionan rápido
- [ ] No hay memory leaks en consola

### ✅ Checklist de Seguridad

- [ ] Auth no se ve afectado
- [ ] Solo usuarios autenticados ven datos
- [ ] No hay exposición de datos sensibles
- [ ] Logs sin errores críticos

---

## Rollback (Si Falla)

Si algo sale mal, volver al estado anterior:

```bash
# 1. En GitHub, revert el commit
git revert f4745897

# 2. Push
git push origin main

# 3. Esperar que Render redeploy automáticamente (~2-3 min)

# 4. Verificar que todo vuelve a funcionar
curl https://rapicredit.onrender.com/health
```

---

## Archivos Modificados

| Archivo | Líneas | Tipo |
|---------|--------|------|
| `backend/app/api/v1/endpoints/prestamos.py` | 507-591 | ✏️ Modificado |
| `backend/scripts/auditoria_pagos_conciliados.py` | nuevo | ✨ Nuevo |
| `backend/sql/diagnostico_pagos_conciliados.sql` | nuevo | ✨ Nuevo |
| `docs/AUDITORIA_PAGOS_CONCILIADOS_2026_02_19.md` | nuevo | 📋 Doc |

---

## Métricas de Éxito

### Antes del Fix
```
Tabla de Amortización - Préstamo #4601
├─ Cuota 1: Pago conciliado = "—"  ❌
├─ Cuota 2: Pago conciliado = "—"  ❌
└─ Cuota 3: Pago conciliado = "—"  ❌

Total pagos visibles: 0
```

### Después del Fix (Esperado)
```
Tabla de Amortización - Préstamo #4601
├─ Cuota 1: Pago conciliado = "$240.00"  ✅
├─ Cuota 2: Pago conciliado = "$240.00"  ✅
└─ Cuota 3: Pago conciliado = "—"        ✅

Total pagos visibles: 2
Total Pendiente: $240.00
```

---

## Soporte Post-Deploy

Si usuarios reportan problemas:

### Verificación Rápida
```bash
# 1. Ejecutar script de auditoría
python backend/scripts/auditoria_pagos_conciliados.py 4601

# 2. Ejecutar queries SQL
psql $DATABASE_URL < backend/sql/diagnostico_pagos_conciliados.sql

# 3. Revisar logs del servidor
tail -f /var/log/rapicredit/backend.log
```

### Contacto de Soporte
- 📧 Email: [tu-email@rapicreditca.com]
- 🔗 Referencia: Commit f4745897
- 📋 Docs: Ver `AUDITORIA_PAGOS_CONCILIADOS_2026_02_19.md`

---

## Timeline Estimado

| Fase | Tiempo | Estado |
|------|--------|--------|
| Code Review | 5-10 min | ⏳ Pendiente |
| Push a main | 1 min | ⏳ Pendiente |
| Build en Render | 2-3 min | ⏳ Pendiente |
| Deploy | 1 min | ⏳ Pendiente |
| Validación Manual | 5 min | ⏳ Pendiente |
| **Total** | **~15 min** | ⏳ Pendiente |

---

## Notas Importantes

1. **Sin Downtime**: El deploy es automático en Render, sin interrupciones
2. **Sin Migraciones**: No requiere correr migraciones DB
3. **Rollback Rápido**: Si es necesario, revertir es tan simple como un `git revert`
4. **Testing**: Se recomienda test manual en staging si disponible

---

**Creado**: 2026-02-19  
**Commit**: f4745897  
**Autor**: Cursor AI Agent  
**Estado**: 🟢 Listo para Deploy
