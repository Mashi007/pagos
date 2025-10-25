#!/usr/bin/env python3
"""
Script para corregir errores de indentación específicos usando MultiEdit
"""

import os
from MultiEdit import MultiEdit

def fix_indentation_errors():
    """Corregir errores específicos de indentación"""
    
    files_to_fix = [
        "backend/app/api/v1/endpoints/intermittent_failure_analyzer.py",
        "backend/app/api/v1/endpoints/network_diagnostic.py", 
        "backend/app/api/v1/endpoints/temporal_analysis.py"
    ]
    
    total_fixed = 0
    
    for file_path in files_to_fix:
        print(f"Corrigiendo {file_path}...")
        
        if not os.path.exists(file_path):
            print(f"  ERROR: Archivo no encontrado: {file_path}")
            continue
        
        # Leer archivo
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Aplicar correcciones específicas
        edits = []
        
        if "intermittent_failure_analyzer.py" in file_path:
            # Corregir línea 110 - método _analyze_endpoint_patterns
            old_line = "    def _analyze_endpoint_patterns(self) -> Dict[str, Any]:"
            new_line = "    def _analyze_endpoint_patterns(self) -> Dict[str, Any]:"
            if old_line in content:
                edits.append({"old_string": old_line, "new_string": new_line})
        
        elif "network_diagnostic.py" in file_path:
            # Corregir línea 54 - método _test_connectivity  
            old_line = "    def _test_connectivity(self):"
            new_line = "    def _test_connectivity(self):"
            if old_line in content:
                edits.append({"old_string": old_line, "new_string": new_line})
        
        elif "temporal_analysis.py" in file_path:
            # Corregir línea 57 - bloque with
            old_line = "        current_time = datetime.now()"
            new_line = "        current_time = datetime.now()"
            if old_line in content:
                edits.append({"old_string": old_line, "new_string": new_line})
        
        # Aplicar ediciones
        if edits:
            try:
                MultiEdit(file_path, edits)
                print(f"  OK: {len(edits)} correcciones aplicadas")
                total_fixed += len(edits)
            except Exception as e:
                print(f"  ERROR: {e}")
        else:
            print(f"  OK: No se encontraron problemas")
    
    print(f"\nRESUMEN: Total de correcciones aplicadas: {total_fixed}")
    return total_fixed

if __name__ == "__main__":
    print("Corrigiendo errores de indentacion con MultiEdit...")
    fixed = fix_indentation_errors()
    print(f"Correccion completada. {fixed} correcciones aplicadas.")
