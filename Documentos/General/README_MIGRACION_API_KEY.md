# 🔐 Migración: Encriptar API Key de OpenAI

## Descripción

Este script encripta la API Key de OpenAI existente en la base de datos si actualmente está almacenada en texto plano.

## ¿Por qué es necesario?

Según la auditoría de seguridad, la API Key está almacenada en texto plano, lo cual es un **riesgo crítico de seguridad**. Si la base de datos es comprometida, la API Key quedaría expuesta.

## Requisitos

- Python 3.8+
- Acceso a la base de datos
- Variables de entorno configuradas (SECRET_KEY o ENCRYPTION_KEY)

## Ejecución

### Opción 1: Desde el directorio raíz del proyecto

```bash
cd backend
python -m app.scripts.migrar_encriptar_api_key
```

### Opción 2: Ejecutar directamente

```bash
cd backend/scripts
python migrar_encriptar_api_key.py
```

## ¿Qué hace el script?

1. **Verifica** si la API Key existe en la base de datos
2. **Comprueba** si ya está encriptada
3. **Encripta** la API Key si está en texto plano
4. **Valida** que la encriptación funciona correctamente (puede desencriptar)
5. **Guarda** la API Key encriptada en la base de datos

## Resultado esperado

```
============================================================
MIGRACIÓN: Encriptar API Key de OpenAI
============================================================
🔐 Encriptando API Key...
✅ API Key encriptada y guardada exitosamente
   Formato original: sk-proj-xxx...
   Formato encriptado: gAAAAABxxx...
============================================================
✅ MIGRACIÓN COMPLETADA EXITOSAMENTE
============================================================
```

## Verificación

Después de ejecutar el script, puedes verificar que la API Key está encriptada ejecutando el script de auditoría:

```sql
-- En DBeaver o psql
SELECT 
    clave,
    CASE 
        WHEN valor LIKE 'gAAAAAB%' THEN '✅ Encriptada'
        ELSE '❌ NO encriptada'
    END AS estado,
    LENGTH(valor) AS longitud
FROM configuracion_sistema
WHERE categoria = 'AI' 
AND clave = 'openai_api_key';
```

## Notas importantes

- ⚠️ **Backup**: Se recomienda hacer un backup de la base de datos antes de ejecutar el script
- ✅ **Reversible**: El script verifica que la API Key se puede desencriptar antes de guardarla
- 🔒 **Seguridad**: Una vez encriptada, la API Key solo se puede leer usando `decrypt_api_key()`
- 🔄 **Idempotente**: Puedes ejecutar el script múltiples veces sin problemas (detecta si ya está encriptada)

## Solución de problemas

### Error: "SECRET_KEY no está configurada"

**Solución**: Configura la variable de entorno `SECRET_KEY` o `ENCRYPTION_KEY`

```bash
export SECRET_KEY="tu-secret-key-aqui"
# O
export ENCRYPTION_KEY="tu-encryption-key-fernet-aqui"
```

### Error: "No se encontró API Key para encriptar"

**Solución**: Asegúrate de que la API Key esté configurada en la base de datos:

```sql
SELECT * FROM configuracion_sistema 
WHERE categoria = 'AI' AND clave = 'openai_api_key';
```

### Error: "La API Key encriptada no coincide con la original"

**Solución**: Esto indica un problema con la clave de encriptación. Verifica que `SECRET_KEY` o `ENCRYPTION_KEY` sean correctos y consistentes.

## Después de la migración

Una vez completada la migración:

1. ✅ La API Key estará encriptada en la base de datos
2. ✅ El código automáticamente la desencriptará cuando sea necesario
3. ✅ Las nuevas API Keys se encriptarán automáticamente al guardarse
4. ✅ En producción, el sistema no permitirá guardar API Keys sin encriptar

## Soporte

Si encuentras problemas, revisa los logs del script o contacta al equipo de desarrollo.

