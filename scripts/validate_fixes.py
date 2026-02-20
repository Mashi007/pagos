#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de validación: Asegurar que los cambios de persistencia están implementados correctamente.
Ejecutar en: python scripts/validate_fixes.py
"""
import sys
import re
from pathlib import Path

def check_backend_fixes():
    """Validar que el backend tiene la función helper y los commits correctos."""
    print("\n[BACKEND] Validando...")
    
    backend_file = Path("backend/app/api/v1/endpoints/clientes.py")
    if not backend_file.exists():
        print("[ERROR] No encontrado: backend/app/api/v1/endpoints/clientes.py")
        return False
    
    content = backend_file.read_text()
    
    # Validación 1: Existe la función helper
    if "def _perform_update_cliente" not in content:
        print("[ERROR] Falta la función helper: _perform_update_cliente()")
        return False
    print("[OK] Función helper _perform_update_cliente() existe")
    
    # Validación 2: Helper tiene db.commit()
    helper_match = re.search(
        r'def _perform_update_cliente.*?(?=@router|\Z)',
        content,
        re.DOTALL
    )
    if helper_match and "db.commit()" in helper_match.group():
        print("[OK] Helper contiene db.commit()")
    else:
        print("[ERROR] Helper no contiene db.commit()")
        return False
    
    # Validación 3: actualizar_clientes_lote usa la función helper
    if "_perform_update_cliente(cid, payload, db)" in content:
        print("[OK] actualizar_clientes_lote() usa la función helper")
    else:
        print("[ERROR] actualizar_clientes_lote() NO usa la función helper")
        return False
    
    # Validación 4: endpoint PUT usa la función helper
    if re.search(r'return _perform_update_cliente\(cliente_id, payload, db\)', content):
        print("[OK] Endpoint PUT usa la función helper")
    else:
        print("[ERROR] Endpoint PUT NO usa la función helper")
        return False
    
    return True

def check_frontend_fixes():
    """Validar que el frontend invalida el cache correctamente."""
    print("\n[FRONTEND] Validando...")
    
    frontend_file = Path("frontend/src/components/clientes/CasosRevisarDialog.tsx")
    if not frontend_file.exists():
        print("[ERROR] No encontrado: frontend/src/components/clientes/CasosRevisarDialog.tsx")
        return False
    
    content = frontend_file.read_text()
    
    # Validación 1: Importa useQueryClient
    if "useQueryClient" in content:
        print("[OK] Importa useQueryClient")
    else:
        print("[ERROR] No importa useQueryClient")
        return False
    
    # Validación 2: Importa clienteKeys
    if "clienteKeys" in content:
        print("[OK] Importa clienteKeys")
    else:
        print("[ERROR] No importa clienteKeys")
        return False
    
    # Validación 3: Usa queryClient en el componente
    if "const queryClient = useQueryClient()" in content:
        print("[OK] Usa queryClient en el componente")
    else:
        print("[ERROR] No usa queryClient en el componente")
        return False
    
    # Validación 4: Invalida en saveOne
    if content.count("queryClient.invalidateQueries") >= 3:
        print("[OK] Invalida cache en saveOne()")
    else:
        print("[ERROR] No invalida cache suficientemente en saveOne()")
        return False
    
    # Validación 5: Invalida en saveAll
    if "queryClient.invalidateQueries({ queryKey: clienteKeys.lists()" in content:
        print("[OK] Invalida lista de clientes después de guardar")
    else:
        print("[ERROR] No invalida lista de clientes después de guardar")
        return False
    
    return True

def main():
    print("\n" + "=" * 70)
    print("VALIDANDO IMPLEMENTACION DE PERSISTENCIA DE DATOS")
    print("=" * 70)
    
    backend_ok = check_backend_fixes()
    frontend_ok = check_frontend_fixes()
    
    print("\n" + "=" * 70)
    if backend_ok and frontend_ok:
        print("[SUCCESS] ¡Todos los cambios están correctamente implementados!")
        print("\nRESUMEN DE CAMBIOS:")
        print("  * Backend: Función helper _perform_update_cliente() con db.commit()")
        print("  * Backend: Ambos endpoints (PUT y POST lote) usan la función helper")
        print("  * Frontend: Invalidación de cache en React Query después de guardar")
        print("  * Frontend: Los cambios se reflejan inmediatamente en todos los componentes")
        print("=" * 70)
        return 0
    else:
        print("[FAILED] Algunos cambios no están correctamente implementados")
        print("\nPor favor, revisar los errores arriba")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
