# 📁 Organizador Automático de Documentos Markdown

Este directorio contiene scripts para organizar automáticamente archivos `.md` en sus carpetas correspondientes según patrones en sus nombres.

## 🚀 Scripts Disponibles

### 1. **organizar_documentos.ps1** (PowerShell - Windows)
```powershell
# Modo normal (mueve archivos)
.\scripts\organizar_documentos.ps1

# Modo dry-run (solo muestra qué haría)
.\scripts\organizar_documentos.ps1 -DryRun
```

### 2. **organizar_documentos.py** (Python - Multiplataforma)
```bash
# Modo normal (mueve archivos)
python scripts/organizar_documentos.py

# Modo dry-run (solo muestra qué haría)
python scripts/organizar_documentos.py --dry-run

# Especificar ruta raíz
python scripts/organizar_documentos.py --root /ruta/al/proyecto
```

## 📋 Reglas de Clasificación

Los archivos se organizan automáticamente según estos patrones:

### 📂 **Documentos/Auditorias/**
- `AUDITORIA_*` - Documentos de auditoría

### 📂 **Documentos/Analisis/**
- `ANALISIS_*` - Documentos de análisis

### 📂 **Documentos/Testing/**
- `TEST_*` - Documentos de pruebas
- `CI-CD*` - Documentos de CI/CD
- `ACCESIBILIDAD*` - Documentos de accesibilidad

### 📂 **Documentos/Configuracion/**
- `INSTALAR_*` - Guías de instalación
- `COMANDOS_INSTALACION*` - Comandos de instalación
- `PASOS_INSTALACION*` - Pasos de instalación
- `DEPLOYMENT_*` - Documentos de despliegue
- `VERIFICAR_INSTALACION*` - Verificaciones de instalación

### 📂 **Documentos/Desarrollo/**
- `PROCEDIMIENTO_*` - Procedimientos de desarrollo
- `AVANCE_*` - Avances de desarrollo
- `ESTADO_FINAL_*` - Estados finales
- `ESTADO_CLIENTES*` - Estados de clientes
- `RESUMEN_CAMBIOS_*` - Resúmenes de cambios
- `RESUMEN_ERRORES_*` - Resúmenes de errores
- `PROPUESTA_*` - Propuestas

### 📂 **Documentos/General/**
- `VERIFICACION_*` - Verificaciones
- `CONFIRMACION_*` - Confirmaciones
- `CHECKLIST_*` - Checklists
- `SOLUCION_*` - Soluciones
- `CORRECCION_*` - Correcciones
- `CONEXIONES_*` - Documentos de conexiones
- `EXPORTACION_*` - Documentos de exportación
- `SISTEMA_NOTIFICACIONES*` - Sistema de notificaciones
- `RESUMEN_NOTIFICACIONES*` - Resúmenes de notificaciones
- `GUIA_*` - Guías
- `ESCALA_*` - Escalas
- `DETALLE_*` - Detalles
- `EXPLICACION_*` - Explicaciones
- `ACLARACION_*` - Aclaraciones
- `CAMBIO_IMPORTANTE_*` - Cambios importantes
- Cualquier otro archivo .md que no coincida con los patrones anteriores

## 🚫 Archivos Excluidos

Los siguientes archivos **NO** se mueven:
- `README.md` (en cualquier ubicación)
- Archivos dentro de `Documentos/` ya organizados
- Archivos dentro de `backend/`, `frontend/`, `scripts/`, `node_modules/`, `.git/`

## 🔧 Uso Recomendado

### Antes de cada commit:
```bash
# Verificar organización (dry-run)
python scripts/organizar_documentos.py --dry-run

# Si todo está bien, organizar
python scripts/organizar_documentos.py

# Agregar cambios y commitear
git add .
git commit -m "docs: organizar documentos"
```

### Configurar como alias de Git (opcional):
```bash
git config alias.org-docs '!python scripts/organizar_documentos.py'
git org-docs
```

## 🔄 Integración con Git Hooks

Para automatizar la organización antes de cada commit, puedes crear un pre-commit hook:

### Opción 1: Manual (Windows)
Crear archivo `.git/hooks/pre-commit`:
```powershell
# .git/hooks/pre-commit
python scripts/organizar_documentos.py
git add Documentos/
```

### Opción 2: Usando husky (si usas Node.js)
```bash
npm install --save-dev husky
npx husky install
npx husky add .husky/pre-commit "python scripts/organizar_documentos.py && git add Documentos/"
```

## 📊 Ejemplo de Salida

```
📁 ORGANIZADOR DE DOCUMENTOS MARKDOWN

🔍 Buscando archivos .md...
   Encontrados: 5 archivos

✓ VERIFICACION_MODULO.md
   Ya está en: Documentos\General

✓ NUEVO_DOCUMENTO.md
   Movido: raiz → Documentos\General\

═══════════════════════════════════════
📊 RESUMEN
═══════════════════════════════════════
   Archivos movidos: 1
   Archivos omitidos: 4
   Errores: 0

✅ Proceso completado
```

## 🔍 Troubleshooting

### "No se encontraron archivos"
- Verifica que estás ejecutando el script desde la raíz del proyecto
- Verifica que hay archivos .md fuera de las carpetas excluidas

### "Permission denied" (Linux/Mac)
```bash
chmod +x scripts/organizar_documentos.py
```

### "Python no encontrado"
- Asegúrate de tener Python 3 instalado
- Usa `python3` en lugar de `python` si es necesario

## 💡 Tips

1. **Siempre usa `--dry-run` primero** para ver qué hará el script
2. **Haz commit antes de organizar** para poder revertir si es necesario
3. **Revisa los cambios** después de organizar antes de commitear
4. **Usa nombres descriptivos** en tus archivos .md para que se clasifiquen correctamente

---

**Creado para mantener la organización automática de la documentación del proyecto** 📚

