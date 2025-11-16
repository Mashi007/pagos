# 🔧 Solución: npm no se reconoce en PowerShell

## Problema
npm no está en el PATH de PowerShell, aunque Node.js puede estar instalado.

## ✅ Solución 1: Encontrar Node.js

Ejecuta:

```powershell
where.exe node
```

Esto te dirá dónde está instalado Node.js.

---

## ✅ Solución 2: Usar npm con ruta completa

Si encontraste que Node.js está en `C:\Program Files\nodejs\`, ejecuta:

```powershell
& "C:\Program Files\nodejs\npm.cmd" install
```

O si está en otra ubicación, ejecuta:

```powershell
& "C:\Users\PORTATIL\AppData\Roaming\npm\npm.cmd" install
```

---

## ✅ Solución 3: Verificar si Node.js está instalado

Ejecuta:

```powershell
node --version
```

Si muestra un error, Node.js NO está instalado. Descárgalo de [nodejs.org](https://nodejs.org/)

---

## ✅ Solución 4: Agregar Node.js al PATH de PowerShell

Si Node.js está instalado pero npm no se reconoce, agrega al PATH:

```powershell
$env:Path += ";C:\Program Files\nodejs"
```

Luego intenta:

```powershell
npm install
```

---

## 🚀 Solución Rápida (Recomendada)

**Descarga e instala Node.js:**

1. Ve a: https://nodejs.org/
2. Descarga la versión LTS (Long Term Support)
3. Instálalo (marca todas las opciones por defecto)
4. **Reinicia PowerShell como Administrador**
5. Ejecuta los comandos nuevamente

---

## ✅ Después de instalar Node.js:

```powershell
cd C:\Users\PORTATIL\Documents\GitHub\pagos\frontend
npm install
```

