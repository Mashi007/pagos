# 📁 Organizador Automático de Archivos SQL

Este script organiza automáticamente todos los archivos `.sql` del proyecto en una carpeta centralizada para mejorar el orden y la gestión.

## 🚀 Scripts Disponibles

### 1. **organizar_sql.ps1** (PowerShell - Windows)
```powershell
# Modo normal (mueve archivos)
.\scripts\organizar_sql.ps1

# Modo dry-run (solo muestra qué haría)
.\scripts\organizar_sql.ps1 -DryRun

# Especificar carpeta destino personalizada
.\scripts\organizar_sql.ps1 -TargetFolder "sql_scripts"
```

### 2. **organizar_sql.py** (Python - Multiplataforma)
```bash
# Modo normal (mueve archivos)
python scripts/organizar_sql.py

# Modo dry-run (solo muestra qué haría)
python scripts/organizar_sql.py --dry-run

# Especificar carpeta destino personalizada
python scripts/organizar_sql.py --target-folder sql_scripts
```

## 📋 Características

- ✅ **Centraliza todos los archivos SQL** en una sola carpeta (`scripts/sql` por defecto)
- ✅ **Resuelve conflictos de nombres** automáticamente (renombra si es necesario)
- ✅ **Respeta archivos del sistema** (no mueve migraciones automáticas)
- ✅ **Modo dry-run** para verificar antes de mover
- ✅ **Manejo de errores** con reporte detallado

## 🚫 Archivos Excluidos

El script **NO mueve** archivos SQL que estén en:
- `migrations/` - Migraciones del sistema de base de datos
- `node_modules/` - Dependencias de Node.js
- `.git/` - Configuración de Git

También excluye archivos con patrones:
- `*migration*.sql`
- `*migrations*.sql`

## 📂 Carpeta Destino

Por defecto, todos los archivos SQL se organizan en:
```
scripts/sql/
```

Puedes cambiar la carpeta destino usando el parámetro `-TargetFolder` (PowerShell) o `--target-folder` (Python).

## 🔧 Uso Recomendado

### Paso 1: Verificar (Siempre primero)
```powershell
.\scripts\organizar_sql.ps1 -DryRun
```

### Paso 2: Organizar archivos
```powershell
.\scripts\organizar_sql.ps1
```

### Paso 3: Verificar cambios
```powershell
git status
git add scripts/sql/
git commit -m "chore: organizar archivos SQL en carpeta centralizada"
```

## 📊 Ejemplo de Salida

```
ORGANIZADOR DE ARCHIVOS SQL

Buscando archivos .sql...
   Encontrados: 22 archivos

[INFO] Carpeta creada: scripts\sql
[OK] agregar_num_referencias_verificadas.sql
   Movido: raiz -> scripts\sql\
[OK] consultas_verificacion_dbeaver.sql
   Movido: raiz -> scripts\sql\
...

=======================================
RESUMEN
=======================================
   Archivos movidos: 22
   Archivos omitidos: 0

Carpeta destino: scripts\sql

[OK] Proceso completado
```

## 🔍 Resolución de Conflictos

Si hay archivos con el mismo nombre en diferentes ubicaciones, el script:
1. Detecta el conflicto
2. Renombra automáticamente el segundo archivo con un sufijo `_1`, `_2`, etc.
3. Muestra una advertencia en el output

Ejemplo:
```
[WARN] verificar_tabla.sql tiene conflicto, se renombrara a: verificar_tabla_1.sql
```

## 💡 Tips

1. **Siempre usa `-DryRun` primero** para ver qué hará el script
2. **Haz commit antes de organizar** para poder revertir si es necesario
3. **Revisa los cambios** después de organizar antes de commitear
4. **Verifica que los paths en tu código sigan funcionando** después de mover los archivos
5. **Las migraciones automáticas se mantienen** en su lugar por seguridad

## 🔄 Integración Continua

Si quieres mantener los archivos SQL organizados automáticamente, puedes ejecutar este script como parte de tu proceso de desarrollo:

### Pre-commit Hook (Opcional)
Crear archivo `.git/hooks/pre-commit`:
```bash
#!/bin/sh
python scripts/organizar_sql.py
git add scripts/sql/
```

### En CI/CD
```yaml
- name: Organizar archivos SQL
  run: python scripts/organizar_sql.py --dry-run
```

## ⚠️ Notas Importantes

- El script **preserva las migraciones** en su lugar original
- Los archivos se **mueven físicamente**, no se copian
- Si hay **conflictos de nombres**, se renombran automáticamente
- El script es **idempotente**: ejecutarlo múltiples veces es seguro

---

**Creado para mantener la organización centralizada de scripts SQL** 📊

