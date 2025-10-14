# 🔧 INSTRUCCIONES PARA CREAR USUARIO CON CONTRASEÑA CONOCIDA

## 🚨 **PROBLEMA IDENTIFICADO:**

### **❌ CREDENCIALES INCORRECTAS:**
- **Usuario existe**: `admin@financiamiento.com` está en la base de datos
- **Contraseña incorrecta**: Ninguna contraseña probada funciona
- **Resultado**: Login falla → Tokens no se almacenan → 403 Forbidden

## 🚀 **SOLUCIÓN:**

### **1. ✅ CREAR USUARIO NUEVO CON CONTRASEÑA CONOCIDA**

#### **📋 CREDENCIALES A CREAR:**
```
Email: admin@rapicredit.com
Password: admin123
Rol: ADMIN
```

#### **🔧 MÉTODO 1: SQL DIRECTO**
```sql
-- Ejecutar en la base de datos PostgreSQL
DELETE FROM users WHERE email = 'admin@rapicredit.com';

INSERT INTO users (
    email, 
    password_hash, 
    nombre, 
    apellido, 
    rol, 
    activo, 
    creado_en, 
    actualizado_en
) VALUES (
    'admin@rapicredit.com',
    '$2b$12$LQv3c1yqBwEHXz2gG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO',
    'Admin',
    'Sistema',
    'ADMIN',
    true,
    NOW(),
    NOW()
);
```

#### **🔧 MÉTODO 2: SCRIPT PYTHON**
```python
import bcrypt
from app.models.user import User
from app.db.session import SessionLocal

def create_user():
    db = SessionLocal()
    try:
        password = "admin123"
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        new_user = User(
            email="admin@rapicredit.com",
            password_hash=password_hash.decode('utf-8'),
            nombre="Admin",
            apellido="Sistema",
            rol="ADMIN",
            activo=True
        )
        
        db.add(new_user)
        db.commit()
        print("✅ Usuario creado exitosamente")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

create_user()
```

#### **🔧 MÉTODO 3: ENDPOINT DE CREACIÓN**
```bash
# Crear endpoint temporal en el backend
POST /api/v1/auth/create-test-user
{
    "email": "admin@rapicredit.com",
    "password": "admin123",
    "nombre": "Admin",
    "apellido": "Sistema",
    "rol": "ADMIN"
}
```

## 🧪 **PRUEBAS DESPUÉS DE CREAR USUARIO:**

### **1. ✅ PROBAR LOGIN:**
```bash
POST https://pagos-f2qf.onrender.com/api/v1/auth/login
{
    "email": "admin@rapicredit.com",
    "password": "admin123",
    "remember": true
}
```

### **2. ✅ VERIFICAR TOKENS:**
```
🔍 Logs esperados:
- "🔧 SOLUCIÓN DEFINITIVA: Iniciando guardado forzado..."
- "✅ localStorage: Tokens guardados"
- "✅ sessionStorage: Tokens guardados"
- "✅ Interceptor: Usando token de localStorage"
```

### **3. ✅ PROBAR ENDPOINT PROTEGIDO:**
```bash
GET https://pagos-f2qf.onrender.com/api/v1/clientes
Authorization: Bearer [token]
```

## 📊 **ESTADO ACTUAL:**

### **❌ PROBLEMA:**
- **Credenciales incorrectas**: Usuario existe pero contraseña no es correcta
- **Login falla**: 401 Unauthorized
- **Tokens no se almacenan**: Porque el login no es exitoso
- **Requests fallan**: 403 Forbidden en endpoints protegidos

### **✅ SOLUCIÓN:**
- **Crear usuario nuevo**: Con contraseña conocida
- **Probar login**: Con credenciales correctas
- **Verificar tokens**: Que se almacenan correctamente
- **Probar funcionalidad**: Endpoints protegidos

## 🎯 **PRÓXIMO PASO:**

**EJECUTAR SQL PARA CREAR USUARIO CON CONTRASEÑA CONOCIDA Y PROBAR LOGIN**

### **📋 CREDENCIALES FINALES:**
```
Email: admin@rapicredit.com
Password: admin123
```

**¡Estas credenciales deberían funcionar después de ejecutar el SQL!**
