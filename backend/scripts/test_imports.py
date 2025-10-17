#!/usr/bin/env python3
"""
Script para verificar importaciones del sistema
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Probar todas las importaciones críticas"""
    
    print("🔍 VERIFICANDO IMPORTACIONES CRÍTICAS")
    print("=" * 50)
    
    try:
        from app.utils.validators import validate_password_strength
        print("✅ validate_password_strength importada correctamente")
        
        # Probar la función
        is_valid, message = validate_password_strength("Test123!")
        print(f"✅ Función funciona: {is_valid}, {message}")
        
    except ImportError as e:
        print(f"❌ Error importando validate_password_strength: {e}")
        return False
    
    try:
        from app.api.deps import get_admin_user, get_current_user
        print("✅ Dependencias de API importadas correctamente")
    except ImportError as e:
        print(f"❌ Error importando dependencias API: {e}")
        return False
    
    try:
        from app.models.user import User
        print("✅ Modelo User importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando modelo User: {e}")
        return False
    
    try:
        from app.schemas.user import UserCreate, UserUpdate, UserResponse
        print("✅ Schemas de usuario importados correctamente")
    except ImportError as e:
        print(f"❌ Error importando schemas: {e}")
        return False
    
    try:
        from app.utils.auditoria_helper import registrar_creacion
        print("✅ Helper de auditoría importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando auditoría helper: {e}")
        return False
    
    try:
        from app.core.security import get_password_hash
        print("✅ Seguridad importada correctamente")
    except ImportError as e:
        print(f"❌ Error importando seguridad: {e}")
        return False
    
    print("\n🎉 TODAS LAS IMPORTACIONES FUNCIONAN CORRECTAMENTE")
    return True

if __name__ == "__main__":
    test_imports()
