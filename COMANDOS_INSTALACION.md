# 🚀 COMANDOS PARA INSTALAR DEPENDENCIAS

## 📍 Instrucciones Específicas

Ya que npm no está disponible directamente en PowerShell, aquí tienes las instrucciones exactas:

---

## Opción 1: Desde Visual Studio Code (RECOMENDADO)

1. Abre la terminal integrada de VS Code (Ctrl + ñ o `` Ctrl + ` ``)
2. Asegúrate de que estás en el directorio del proyecto
3. Ejecuta estos comandos:

```bash
cd frontend
npm install
```

---

## Opción 2: Desde CMD (no PowerShell)

1. Abre **Command Prompt** (CMD) en lugar de PowerShell
2. Navega al directorio del proyecto:

```cmd
cd C:\Users\PORTATIL\Documents\GitHub\pagos\frontend
```

3. Ejecuta:

```cmd
npm install
```

---

## Opción 3: Desde Git Bash

Si tienes Git Bash instalado:

1. Abre Git Bash
2. Navega al proyecto:

```bash
cd /c/Users/PORTATIL/Documents/GitHub/pagos/frontend
```

3. Ejecuta:

```bash
npm install
```

---

## ✅ Verificación

Después de instalar, verifica que las librerías se instalaron correctamente:

```bash
npm list jspdf jspdf-autotable
```

Deberías ver:
```
jspdf@2.5.1
jspdf-autotable@3.8.3
```

---

## 📝 ¿Qué hace `npm install`?

- Descarga la librería `jspdf` (v2.5.1)
- Descarga la librería `jspdf-autotable` (v3.8.3)
- Las agrega a `node_modules/`
- Actualiza el archivo `package-lock.json`

---

## 🎯 Después de Instalar

1. Reinicia el servidor de desarrollo:
   ```bash
   npm run dev
   ```

2. Prueba las funciones de exportación:
   - Abre un préstamo
   - Ve a "Tabla de Amortización"
   - Haz clic en "Exportar Excel" o "Exportar PDF"

---

## ⚠️ Si npm no funciona

Si aún así `npm` no se reconoce:

1. **Reinstala Node.js**: Descarga de [nodejs.org](https://nodejs.org/)
2. **Restaura la terminal**: Cierra y abre nuevamente la terminal
3. **Reinicia VS Code**: Cierra y abre VS Code

---

## 📦 Dependencias que se Instalarán

- **jspdf**: Genera archivos PDF
- **jspdf-autotable**: Crea tablas automáticas en PDF
- **xlsx**: Ya estaba instalada (para Excel)

**Total**: ~1-2 MB de descarga

---

## ✅ Estado Actual

- ✅ Código implementado
- ✅ `package.json` actualizado
- ⏳ Pendiente: Ejecutar `npm install` en la terminal

¡Una vez que ejecutes `npm install`, todo estará listo!

