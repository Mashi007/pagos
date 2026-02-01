# ⚡ Solución Rápida: Error ECONNRESET en Cursor

## 🔴 SOLUCIÓN INMEDIATA (2 minutos)

### Paso 1: Deshabilitar HTTP/2
1. Abre Cursor
2. Presiona `Ctrl + ,` (o ve a **File > Preferences > Settings**)
3. Busca "**network**" en la barra de búsqueda
4. Encuentra la opción "**HTTP/2**" o "**Enable HTTP/2**"
5. **Desmarca/Deshabilita** esta opción
6. Cierra y reinicia Cursor completamente

### Paso 2: Limpiar Cache (PowerShell como Administrador)
```powershell
# Cerrar Cursor primero, luego ejecutar:
Remove-Item -Recurse -Force "$env:APPDATA\Cursor\Cache"
Remove-Item -Recurse -Force "$env:APPDATA\Cursor\Code Cache"
```

### Paso 3: Reiniciar Cursor
- Cierra completamente Cursor
- Espera 10 segundos
- Abre Cursor nuevamente
- Prueba la funcionalidad de IA

---

## ✅ Verificación

Después de aplicar la solución:
- [ ] HTTP/2 está deshabilitado
- [ ] Cache limpiado
- [ ] Cursor reiniciado
- [ ] Error no ocurre durante 10 minutos de uso

---

## 🆘 Si Persiste

1. **Ejecuta el script de diagnóstico:**
   ```powershell
   .\diagnostico_cursor.ps1
   ```

2. **Lee la auditoría completa:**
   - Abre `AUDITORIA_ERROR_CURSOR.md`

3. **Contacta soporte:**
   - Request ID: `44a14c0d-8459-429c-bec5-8079c2840d8f`
   - Forum: https://forum.cursor.com

---

**Esta solución resuelve el 80% de los casos de ECONNRESET en Cursor.**
