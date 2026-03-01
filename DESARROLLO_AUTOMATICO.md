# ?? Desarrollo Automático

## Build Automático Activado

El desarrollo automático está configurado en tu proyecto. Cuando abres Cursor:

### ? Lo que sucede automáticamente:
1. **Dev Server** inicia en `http://localhost:5173`
2. **Hot Reload** se activa automáticamente
3. **TypeScript** se verifica continuamente
4. **Cambios** se compilan sin pedir confirmación

### ??? Comandos Whitelistados (Sin "Run")
Los siguientes comandos se ejecutan automáticamente:
- `npm run build`
- `npm run dev`
- `npm run type-check`
- `npm run lint`
- `npm run lint:fix`
- `git add`, `git commit --trailer "Made-with: Cursor"`, `git push`

### ?? Cómo usar:
1. Guarda archivos ? Hot Reload automático
2. Los errores aparecen en el terminal integrado
3. No hay que hacer click en "Run" cada vez

### ?? Configuración
- `.cursor/settings.json` ? Allowlist de comandos
- `.vscode/tasks.json` ? Tasks de build
- `auto-build.js` ? Script de auto-inicio

### ?? Si necesitas detener:
- Cierra el terminal o presiona `Ctrl+C`
- Reinicia con `npm run dev`

---

**Nota**: La configuración está optimizada para evitar prompts innecesarios mientras mantienes el control.
