#!/usr/bin/env python3
"""
Script de validación para verificar que los modelos se pueden importar correctamente.
"""

import sys
import os

# Agregar el directorio backend al path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

def validate_models():
    """Valida que los modelos se puedan importar correctamente."""
    print("🔍 Validando importación de modelos...")
    
    try:
        # Importar Base primero
        from app.db.session import Base
        print("✅ Base importada correctamente")
        
        # Importar modelos uno por uno para identificar problemas específicos
        from app.models.user import User
        print("✅ User importado correctamente")
        
        from app.models.cliente import Cliente
        print("✅ Cliente importado correctamente")
        
        from app.models.prestamo import Prestamo
        print("✅ Prestamo importado correctamente")
        
        from app.models.pago import Pago
        print("✅ Pago importado correctamente")
        
        from app.models.amortizacion import Cuota
        print("✅ Cuota importada correctamente")
        
        from app.models.aprobacion import Aprobacion
        print("✅ Aprobacion importada correctamente")
        
        from app.models.auditoria import Auditoria
        print("✅ Auditoria importada correctamente")
        
        from app.models.notificacion import Notificacion
        print("✅ Notificacion importada correctamente")
        
        # Importar todos juntos como en __init__.py
        from app.models import (
            Base, User, Cliente, Prestamo, Pago, Cuota, 
            Aprobacion, Auditoria, Notificacion
        )
        print("✅ Todos los modelos importados correctamente desde __init__.py")
        
        print("🎉 Validación de modelos completada con éxito!")
        return True
        
    except Exception as e:
        print(f"❌ Error al importar modelos: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_endpoints():
    """Valida que los endpoints se puedan importar correctamente."""
    print("\n🔍 Validando importación de endpoints...")
    
    try:
        # Importar endpoint de aprobaciones que causaba problemas
        from app.api.v1.endpoints import aprobaciones
        print("✅ Endpoint de aprobaciones importado correctamente")
        
        # Importar todos los endpoints
        from app.api.v1.endpoints import (
            health, auth, users, clientes, prestamos, pagos,
            amortizacion, conciliacion, reportes, kpis,
            notificaciones, aprobaciones, auditoria, configuracion
        )
        print("✅ Todos los endpoints importados correctamente")
        
        print("🎉 Validación de endpoints completada con éxito!")
        return True
        
    except Exception as e:
        print(f"❌ Error al importar endpoints: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal de validación."""
    print("🚀 Iniciando validación de la aplicación...")
    print("=" * 50)
    
    success = True
    
    # Validar modelos
    if not validate_models():
        success = False
    
    # Validar endpoints
    if not validate_endpoints():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ¡Todas las validaciones pasaron correctamente!")
        print("✅ La aplicación debería iniciar sin problemas")
    else:
        print("❌ Hay errores que necesitan ser corregidos")
        sys.exit(1)

if __name__ == "__main__":
    main()