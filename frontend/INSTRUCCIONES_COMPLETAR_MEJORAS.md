# 📋 Instrucciones para Completar las Mejoras

**Fecha:** 1 de Febrero, 2026

---

## ✅ Mejoras Completadas Automáticamente

1. ✅ **Scripts agregados a package.json**
   - `start`: Para ejecutar el servidor en producción
   - `lint`: Para verificar código con ESLint
   - `lint:fix`: Para corregir problemas de ESLint automáticamente
   - `format`: Para formatear código con Prettier
   - `format:check`: Para verificar formato sin cambiar archivos

2. ✅ **Configuración de ESLint creada**
   - Archivo: `.eslintrc.cjs`
   - Configurado para React 18.2
   - Reglas recomendadas activadas

3. ✅ **Configuración de Prettier creada**
   - Archivo: `.prettierrc`
   - Archivo: `.prettierignore`
   - Configuración estándar para proyectos React

4. ✅ **Mejoras en vite.config.js**
   - Sourcemaps habilitados en desarrollo
   - Configuración de variables de entorno mejorada

5. ✅ **Verificación de seguridad**
   - Archivos `.env` NO están en git (verificado)

---

## 🔄 Tareas que Requieren npm (Pendientes)

### Paso 1: Instalar Dependencias de Desarrollo

Abre una terminal en la carpeta `frontend` y ejecuta:

```bash
cd frontend
npm install
```

Esto instalará:
- ESLint y sus plugins
- Prettier
- Generará `package-lock.json`

### Paso 2: Verificar Seguridad de Dependencias

Después de instalar, ejecuta:

```bash
npm audit
```

Si hay vulnerabilidades, ejecuta:

```bash
npm audit fix
```

Para vulnerabilidades que requieren cambios manuales:

```bash
npm audit fix --force
```

⚠️ **Nota:** `--force` puede actualizar versiones mayores, revisa los cambios antes de commitear.

### Paso 3: Verificar Versiones Desactualizadas (Opcional)

Para ver qué paquetes tienen actualizaciones disponibles:

```bash
npm outdated
```

Para actualizar dependencias menores y parches:

```bash
npm update
```

---

## 🧪 Probar las Nuevas Configuraciones

### Probar ESLint

```bash
npm run lint
```

Para corregir automáticamente problemas:

```bash
npm run lint:fix
```

### Probar Prettier

Para formatear todos los archivos:

```bash
npm run format
```

Para solo verificar formato sin cambiar archivos:

```bash
npm run format:check
```

### Probar Script de Inicio

```bash
npm run start
```

Esto ejecutará `node server.js` para servir los archivos estáticos.

---

## 📝 Configuración de Editor (Recomendado)

### Visual Studio Code / Cursor

Instala las extensiones recomendadas:

1. **ESLint** (dbaeumer.vscode-eslint)
2. **Prettier** (esbenp.prettier-vscode)

Agrega a `.vscode/settings.json` (o configuración de usuario):

```json
{
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": "explicit"
  },
  "eslint.validate": [
    "javascript",
    "javascriptreact"
  ]
}
```

---

## 📋 Checklist Final

- [ ] Ejecutar `npm install` en `frontend/`
- [ ] Verificar que `package-lock.json` se haya generado
- [ ] Ejecutar `npm audit` y corregir vulnerabilidades si las hay
- [ ] Probar `npm run lint` y verificar que funciona
- [ ] Probar `npm run format` y verificar que funciona
- [ ] Configurar extensiones de editor (opcional pero recomendado)
- [ ] Commitear los cambios:
  ```bash
  git add .
  git commit -m "feat: agregar ESLint, Prettier y mejorar configuración"
  ```

---

## 🎯 Resumen de Archivos Creados/Modificados

### Archivos Creados:
- ✅ `.eslintrc.cjs` - Configuración de ESLint
- ✅ `.prettierrc` - Configuración de Prettier
- ✅ `.prettierignore` - Archivos a ignorar por Prettier

### Archivos Modificados:
- ✅ `package.json` - Scripts y devDependencies agregados
- ✅ `vite.config.js` - Sourcemaps y variables de entorno mejoradas

### Archivos que se Generarán:
- ⏳ `package-lock.json` - Se generará al ejecutar `npm install`

---

## 🆘 Solución de Problemas

### Si npm no está instalado:

**Windows:**
1. Descarga Node.js desde https://nodejs.org/
2. Instala la versión LTS
3. Reinicia la terminal
4. Verifica con: `node --version` y `npm --version`

### Si hay errores de ESLint:

1. Verifica que todas las dependencias estén instaladas:
   ```bash
   npm install
   ```

2. Si hay conflictos, limpia e instala de nuevo:
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

### Si Prettier no funciona:

1. Verifica que esté instalado:
   ```bash
   npm list prettier
   ```

2. Si no está, instálalo manualmente:
   ```bash
   npm install --save-dev prettier
   ```

---

**Última Actualización:** 1 de Febrero, 2026  
**Estado:** ✅ Configuraciones creadas, pendiente ejecutar `npm install`
