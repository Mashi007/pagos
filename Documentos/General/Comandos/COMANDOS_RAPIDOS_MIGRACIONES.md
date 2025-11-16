# ⚡ Comandos Rápidos para Ver y Migrar

## 🚀 Comando Todo-en-Uno (Recomendado)

**Ver el estado y luego migrar:**

```powershell
.\scripts\powershell\ejecutar_migraciones_alembic.ps1 -VerYMigrar
```

Este comando:
1. ✅ Muestra la migración actual aplicada
2. ✅ Muestra las migraciones disponibles
3. ✅ Muestra el historial reciente
4. ✅ Te pregunta si quieres ejecutar las migraciones
5. ✅ Ejecuta las migraciones si confirmas

## 📊 Solo Ver Estado

```powershell
.\scripts\powershell\ejecutar_migraciones_alembic.ps1 -Status
```

## ⬆️ Solo Migrar (sin ver estado)

```powershell
.\scripts\powershell\ejecutar_migraciones_alembic.ps1
```

## 📝 Comandos Directos (sin script)

Si prefieres ejecutar los comandos directamente:

### Ver estado actual:
```powershell
cd backend
py -m alembic current
```

### Ver migraciones disponibles:
```powershell
cd backend
py -m alembic heads
```

### Ver historial:
```powershell
cd backend
py -m alembic history
```

### Migrar todo:
```powershell
cd backend
py -m alembic upgrade head
```

### Todo en una línea (ver y migrar):
```powershell
cd backend; py -m alembic current; py -m alembic heads; py -m alembic upgrade head
```

## 🎯 Resumen de Opciones

| Comando | Descripción |
|---------|-------------|
| `-VerYMigrar` | Ver estado completo y luego migrar (interactivo) |
| `-Status` | Solo ver el estado |
| `-Current` | Ver migración actual |
| `-History` | Ver historial completo |
| `-Check` | Verificar sintaxis y dependencias |
| `-SQL` | Ver SQL sin ejecutar |
| (sin parámetros) | Ejecutar migraciones directamente |

## 💡 Ejemplo de Uso Completo

```powershell
# 1. Ver estado y migrar (recomendado)
.\scripts\powershell\ejecutar_migraciones_alembic.ps1 -VerYMigrar

# 2. O si prefieres hacerlo paso a paso:
.\scripts\powershell\ejecutar_migraciones_alembic.ps1 -Status
# Revisa la salida, luego:
.\scripts\powershell\ejecutar_migraciones_alembic.ps1
```

