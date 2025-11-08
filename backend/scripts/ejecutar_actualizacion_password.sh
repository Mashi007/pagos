#!/bin/bash
# Script para actualizar contraseña de usuario en la base de datos
# Uso: ./ejecutar_actualizacion_password.sh <email> <password>

if [ $# -lt 2 ]; then
    echo "Uso: $0 <email> <password>"
    echo ""
    echo "Ejemplo:"
    echo "  $0 itmaster@rapicreditca.com Casa1803+"
    exit 1
fi

EMAIL=$1
PASSWORD=$2

echo "🔄 Actualizando contraseña para: $EMAIL"
echo ""

# Ejecutar script Python que actualiza directamente en BD
python scripts/cambiar_password_usuario.py "$EMAIL" "$PASSWORD"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Contraseña actualizada exitosamente"
    echo ""
    echo "Ahora puedes iniciar sesión con:"
    echo "  Email: $EMAIL"
    echo "  Contraseña: $PASSWORD"
else
    echo ""
    echo "❌ Error al actualizar contraseña"
    exit 1
fi

