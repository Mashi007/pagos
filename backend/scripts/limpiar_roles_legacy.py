#!/usr/bin/env python3
"""
Script para limpiar roles legacy que no existen en el sistema
Elimina referencias a: USER, USER, USER, ADMIN, GERENTE
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Set

class LegacyRoleCleaner:
    def __init__(self, backend_path: str = "."):
        self.backend_path = Path(backend_path)
        self.legacy_roles = {
            'USER',
            'USER', 
            'USER',
            'ADMIN',
            'GERENTE',
            'USER_USER'
        }
        self.valid_roles = {'USER', 'ADMIN', 'GERENTE', 'COBRANZAS'}
        self.files_to_fix = []
        
    def scan_and_fix_files(self):
        """Escanear y corregir archivos con roles legacy"""
        print("ESCANEANDO ARCHIVOS CON ROLES LEGACY")
        print("=" * 50)
        
        # Buscar archivos Python
        python_files = list(self.backend_path.rglob("*.py"))
        
        for file_path in python_files:
            self.analyze_and_fix_file(file_path)
            
        # Buscar archivos SQL
        sql_files = list(self.backend_path.rglob("*.sql"))
        for file_path in sql_files:
            self.analyze_and_fix_file(file_path)
            
        self.generate_cleanup_report()
    
    def analyze_and_fix_file(self, file_path: Path):
        """Analizar y corregir un archivo"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            fixed_content = self.fix_legacy_roles(content)
            
            if content != fixed_content:
                # Guardar archivo corregido
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                    
                relative_path = file_path.relative_to(self.backend_path)
                self.files_to_fix.append({
                    'path': str(relative_path),
                    'changes': self.get_changes_summary(original_content, fixed_content)
                })
                
        except Exception as e:
            print(f"Error procesando {file_path}: {e}")
    
    def fix_legacy_roles(self, content: str) -> str:
        """Corregir roles legacy en el contenido"""
        fixed_content = content
        
        # Reemplazos específicos
        replacements = {
            # ADMIN -> ADMIN
            r'"ADMIN"': '"ADMIN"',
            r"'ADMIN'": "'ADMIN'",
            r'ADMIN': 'ADMIN',
            
            # GERENTE -> GERENTE
            r'"GERENTE"': '"GERENTE"',
            r"'GERENTE'": "'GERENTE'",
            r'GERENTE': 'GERENTE',
            
            # USER -> USER
            r'"USER"': '"USER"',
            r"'USER'": "'USER'",
            r'USER': 'USER',
            
            # USER -> USER
            r'"USER"': '"USER"',
            r"'USER'": "'USER'",
            r'USER': 'USER',
            
            # USER -> USER
            r'"USER"': '"USER"',
            r"'USER'": "'USER'",
            r'USER': 'USER',
            
            # USER_USER -> USER
            r'"USER_USER"': '"USER"',
            r"'USER_USER'": "'USER'",
            r'USER_USER': 'USER',
            
            # Listas de roles legacy
            r'\["ADMIN", "GERENTE", "GERENTE"\]': '["ADMIN", "GERENTE"]',
            r'\["ADMIN", "GERENTE", "GERENTE"\]': '["ADMIN", "GERENTE"]',
            r'\["ADMIN", "COBRANZAS"\]': '["ADMIN", "COBRANZAS"]',
            r'\["ADMIN", "COBRANZAS"\]': '["ADMIN", "COBRANZAS"]',
            r'\["ADMIN", "GERENTE", "GERENTE", "COBRANZAS", "USER", "USER", "USER", "USER"\]': '["ADMIN", "GERENTE", "COBRANZAS", "USER"]',
            r'\["ADMIN", "GERENTE", "GERENTE", "COBRANZAS", "USER", "USER", "USER", "USER"\]': '["ADMIN", "GERENTE", "COBRANZAS", "USER"]',
            
            # Roles en filtros
            r'User\.rol\.in\(\["ADMIN", "GERENTE", "GERENTE"\]\)': 'User.rol.in(["ADMIN", "GERENTE"])',
            r'User\.rol\.in\(\["ADMIN", "COBRANZAS"\]\)': 'User.rol.in(["ADMIN", "COBRANZAS"])',
            r'User\.rol == "ADMIN"': 'User.rol == "ADMIN"',
            r'User\.rol == "GERENTE"': 'User.rol == "GERENTE"',
            r'User\.rol == "USER"': 'User.rol == "USER"',
            r'User\.rol == "USER"': 'User.rol == "USER"',
            r'User\.rol == "USER"': 'User.rol == "USER"',
            
            # Comentarios y documentación
            r'# Solo ADMIN': '# Solo ADMIN',
            r'# ADMIN': '# ADMIN',
            r'# GERENTE': '# GERENTE',
            r'# USER': '# USER',
            r'# USER': '# USER',
            r'# USER': '# USER',
        }
        
        for pattern, replacement in replacements.items():
            fixed_content = re.sub(pattern, replacement, fixed_content)
        
        return fixed_content
    
    def get_changes_summary(self, original: str, fixed: str) -> List[str]:
        """Obtener resumen de cambios realizados"""
        changes = []
        
        for legacy_role in self.legacy_roles:
            if legacy_role in original and legacy_role not in fixed:
                changes.append(f"Eliminado rol legacy: {legacy_role}")
        
        return changes
    
    def generate_cleanup_report(self):
        """Generar reporte de limpieza"""
        print("\nREPORTE DE LIMPIEZA DE ROLES LEGACY")
        print("=" * 50)
        
        if self.files_to_fix:
            print(f"\nARCHIVOS CORREGIDOS: {len(self.files_to_fix)}")
            for file_info in self.files_to_fix:
                print(f"\nARCHIVO: {file_info['path']}")
                for change in file_info['changes']:
                    print(f"  - {change}")
        else:
            print("\nNO SE ENCONTRARON ARCHIVOS CON ROLES LEGACY")
        
        print(f"\nROLES VALIDOS EN EL SISTEMA:")
        for role in sorted(self.valid_roles):
            print(f"  - {role}")
        
        print(f"\nROLES LEGACY ELIMINADOS:")
        for role in sorted(self.legacy_roles):
            print(f"  - {role}")

def main():
    """Función principal"""
    cleaner = LegacyRoleCleaner()
    cleaner.scan_and_fix_files()
    
    print(f"\nLIMPIEZA COMPLETADA")
    print(f"Archivos procesados: {len(cleaner.files_to_fix)}")

if __name__ == "__main__":
    main()
