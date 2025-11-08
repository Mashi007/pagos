# Cambiar Contraseña de Usuario

## Script para cambiar contraseña

Se ha creado un script para cambiar la contraseña de cualquier usuario en el sistema.

### Uso del script

```bash
cd backend
python scripts/cambiar_password_usuario.py <email> <nueva_password>
```

### Ejemplo: Cambiar contraseña de itmaster@rapicreditca.com

```bash
cd backend
python scripts/cambiar_password_usuario.py itmaster@rapicreditca.com Casa1803+
```

### Requisitos de la contraseña

La nueva contraseña debe cumplir con:
- Mínimo 8 caracteres
- Al menos una letra mayúscula
- Al menos una letra minúscula
- Al menos un número
- Al menos un símbolo especial

### Script alternativo: actualizar_admin.py

También puedes usar el script `actualizar_admin.py` que actualiza específicamente el usuario admin:

```bash
cd backend
python scripts/actualizar_admin.py
```

Este script actualiza automáticamente la contraseña de `itmaster@rapicreditca.com` a `Casa1803+`.

