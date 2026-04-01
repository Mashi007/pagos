"""
Ejemplos de uso para carga masiva de usuarios.
"""

# ============================================================================
# EJEMPLO 1: Carga masiva simple
# ============================================================================
POST /api/v1/usuarios/bulk
Authorization: Bearer <token_admin>
Content-Type: application/json

{
  "usuarios": [
    {
      "email": "juan.perez@empresa.com",
      "cedula": "12345678-9",
      "nombre": "Juan Pérez García",
      "cargo": "Operario",
      "rol": "operator",
      "password": "SeguraPassword123"
    },
    {
      "email": "maria.lopez@empresa.com",
      "cedula": "87654321-0",
      "nombre": "María López Rodríguez",
      "cargo": "Supervisora",
      "rol": "manager",
      "password": "OtraPassword456"
    },
    {
      "email": "carlos.torres@empresa.com",
      "cedula": "11111111-1",
      "nombre": "Carlos Torres Martínez",
      "cargo": "Contador",
      "rol": "viewer",
      "password": "MasPassword789"
    }
  ]
}


# ============================================================================
# RESPUESTA EXITOSA (201 Created)
# ============================================================================
{
  "total_solicitados": 3,
  "total_exitosos": 3,
  "total_errores": 0,
  "resultados": [
    {
      "email": "juan.perez@empresa.com",
      "status": "success",
      "mensaje": "Usuario creado exitosamente",
      "usuario_id": 100
    },
    {
      "email": "maria.lopez@empresa.com",
      "status": "success",
      "mensaje": "Usuario creado exitosamente",
      "usuario_id": 101
    },
    {
      "email": "carlos.torres@empresa.com",
      "status": "success",
      "mensaje": "Usuario creado exitosamente",
      "usuario_id": 102
    }
  ]
}


# ============================================================================
# RESPUESTA CON ALGUNOS ERRORES
# ============================================================================
{
  "total_solicitados": 3,
  "total_exitosos": 2,
  "total_errores": 1,
  "resultados": [
    {
      "email": "juan.perez@empresa.com",
      "status": "success",
      "mensaje": "Usuario creado exitosamente",
      "usuario_id": 100
    },
    {
      "email": "maria.lopez@empresa.com",
      "status": "error",
      "mensaje": "Email ya existe en el sistema: maria.lopez@empresa.com",
      "usuario_id": null
    },
    {
      "email": "carlos.torres@empresa.com",
      "status": "success",
      "mensaje": "Usuario creado exitosamente",
      "usuario_id": 101
    }
  ]
}


# ============================================================================
# ERROR: No es administrador (403 Forbidden)
# ============================================================================
{
  "detail": "Solo administradores pueden acceder a este recurso."
}


# ============================================================================
# ERROR: Datos inválidos (422 Unprocessable Entity)
# ============================================================================
{
  "detail": [
    {
      "loc": ["body", "usuarios", 0, "rol"],
      "msg": "Rol debe ser uno de: admin, manager, operator, viewer",
      "type": "value_error"
    }
  ]
}


# ============================================================================
# ERROR: Más de 1000 usuarios (422 Unprocessable Entity)
# ============================================================================
{
  "detail": [
    {
      "loc": ["body", "usuarios"],
      "msg": "ensure this value has at most 1000 items",
      "type": "value_error.list.max_items"
    }
  ]
}


# ============================================================================
# EJEMPLO 2: CSV a JSON (para convertir archivo CSV)
# ============================================================================

# Si tienes un archivo CSV:
# email,cedula,nombre,cargo,rol,password
# juan@empresa.com,12345678-9,Juan Pérez,Operario,operator,Pass123
# maria@empresa.com,87654321-0,María López,Supervisora,manager,Pass456

# Conviértelo a JSON con Python:

import csv
import json

def csv_a_json(archivo_csv):
    usuarios = []
    with open(archivo_csv, 'r', encoding='utf-8') as f:
        lector = csv.DictReader(f)
        for fila in lector:
            usuarios.append({
                "email": fila['email'].strip(),
                "cedula": fila['cedula'].strip(),
                "nombre": fila['nombre'].strip(),
                "cargo": fila['cargo'].strip() if fila['cargo'] else None,
                "rol": fila['rol'].strip(),
                "password": fila['password'].strip()
            })
    return {"usuarios": usuarios}

# Uso:
datos = csv_a_json('usuarios.csv')
print(json.dumps(datos, indent=2))


# ============================================================================
# EJEMPLO 3: Usar con cURL
# ============================================================================

curl -X POST http://localhost:8000/api/v1/usuarios/bulk \
  -H "Authorization: Bearer tu_token_admin" \
  -H "Content-Type: application/json" \
  -d '{
    "usuarios": [
      {
        "email": "usuario1@empresa.com",
        "cedula": "12345678-9",
        "nombre": "Usuario Uno",
        "cargo": "Operario",
        "rol": "operator",
        "password": "Password123"
      }
    ]
  }'


# ============================================================================
# VALIDACIONES Y LÍMITES
# ============================================================================

MÁXIMO_USUARIOS: 1000 por solicitud
EMAIL: Formato válido + único en el sistema
CEDULA: 1-50 caracteres + único en el sistema
NOMBRE: 1-255 caracteres (nombre completo)
CARGO: Opcional, máximo 100 caracteres
ROL: Obligatorio - admin|manager|operator|viewer
PASSWORD: Mínimo 6 caracteres
IS_ACTIVE: Siempre true para nuevos usuarios

VALIDACIONES INTERNAS:
- Detecta duplicados dentro de la misma carga
- Valida duplicados contra BD
- Procesa todos los usuarios válidos aunque haya algunos con error
- Registra cada operación en logs
- Transacción atómica: todos se crean o ninguno

# ============================================================================
# LOGS GENERADOS
# ============================================================================

Los logs registran:
- Usuario creado en importación masiva: email, cedula, rol, admin que lo creó
- Importación masiva completada: total exitosos, errores, admin
- Errores: detalles de cada fallo

Log ejemplo:
Usuario creado en importación masiva: email=juan@empresa.com, cedula=12345678-9, rol=operator, por admin=admin@sistema.com
Importación masiva completada: 5 exitosos, 2 errores, por admin=admin@sistema.com
