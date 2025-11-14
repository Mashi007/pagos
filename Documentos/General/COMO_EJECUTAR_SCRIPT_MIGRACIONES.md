# 📋 Cómo Ejecutar el Script de Migraciones de Alembic

## 🎯 Ubicación del Script

El script está en: `scripts/powershell/ejecutar_migraciones_alembic.ps1`

## ✅ Opción 1: Desde la Raíz del Proyecto (Recomendado)

1. **Abre PowerShell** en la raíz del proyecto:
   ```
   C:\Users\PORTATIL\Documents\GitHub\pagos
   ```

2. **Ejecuta el script:**
   ```powershell
   .\scripts\powershell\ejecutar_migraciones_alembic.ps1
   ```

   O con la ruta completa:
   ```powershell
   .\scripts\powershell\ejecutar_migraciones_alembic.ps1
   ```

## ✅ Opción 2: Desde el Terminal Integrado de Cursor

1. **Abre el terminal en Cursor** (`` Ctrl+` `` o `Terminal > New Terminal`)

2. **Asegúrate de estar en la raíz del proyecto:**
   ```powershell
   cd C:\Users\PORTATIL\Documents\GitHub\pagos
   ```

3. **Ejecuta el script:**
   ```powershell
   .\scripts\powershell\ejecutar_migraciones_alembic.ps1
   ```

## ✅ Opción 3: Desde Cualquier Ubicación

Puedes ejecutarlo desde cualquier lugar usando la ruta completa:

```powershell
& "C:\Users\PORTATIL\Documents\GitHub\pagos\scripts\powershell\ejecutar_migraciones_alembic.ps1"
```

## 📝 Comandos Disponibles

### Ejecutar todas las migraciones pendientes:
```powershell
.\scripts\powershell\ejecutar_migraciones_alembic.ps1
```

### Verificar migraciones (sintaxis, dependencias, etc.):
```powershell
.\scripts\powershell\ejecutar_migraciones_alembic.ps1 -Check
```

### Ver historial de migraciones:
```powershell
.\scripts\powershell\ejecutar_migraciones_alembic.ps1 -History
```

### Ver migración actual aplicada:
```powershell
.\scripts\powershell\ejecutar_migraciones_alembic.ps1 -Current
```

### Ver el SQL que se ejecutará (sin ejecutarlo):
```powershell
.\scripts\powershell\ejecutar_migraciones_alembic.ps1 -SQL
```

### Revertir la última migración:
```powershell
.\scripts\powershell\ejecutar_migraciones_alembic.ps1 -Action downgrade -Target -1
```

## ⚠️ Si Obtienes un Error de Política de Ejecución

Si PowerShell te dice que no puede ejecutar scripts, ejecuta esto primero:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Luego intenta ejecutar el script nuevamente.

## 🔍 Verificación Rápida

Para verificar que estás en el lugar correcto, ejecuta:

```powershell
# Deberías ver la estructura del proyecto
ls

# Deberías ver el directorio backend
Test-Path backend

# Deberías ver el script
Test-Path scripts\powershell\ejecutar_migraciones_alembic.ps1
```

## 📍 Estructura Esperada

```
pagos/                          ← Debes estar aquí
├── backend/
│   ├── alembic.ini
│   └── alembic/
│       └── versions/
├── scripts/
│   └── powershell/
│       └── ejecutar_migraciones_alembic.ps1  ← El script
└── frontend/
```

## 💡 Consejo

El script automáticamente:
- ✅ Cambia al directorio `backend`
- ✅ Verifica que `alembic.ini` existe
- ✅ Verifica que el directorio de migraciones existe
- ✅ Ejecuta los comandos de Alembic
- ✅ Vuelve al directorio original al finalizar

¡No necesitas cambiar manualmente al directorio backend!

