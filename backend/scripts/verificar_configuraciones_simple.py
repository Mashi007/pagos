#!/usr/bin/env python3
"""
Script de verificación de configuraciones en el backend
Busca inconsistencias en roles, permisos y configuraciones
"""
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

class BackendConfigAnalyzer:
    def __init__(self, backend_path: str = "."):
        self.backend_path = Path(backend_path)
        self.roles_found = set()
        self.config_inconsistencies = []
        self.file_analysis = {}
        
    def analyze_all_files(self):
        """Analizar todos los archivos del backend"""
        print("INICIANDO ANALISIS DE CONFIGURACIONES DEL BACKEND")
        print("=" * 60)
        
        # Buscar archivos Python
        python_files = list(self.backend_path.rglob("*.py"))
        
        for file_path in python_files:
            self.analyze_file(file_path)
            
        # Buscar archivos SQL
        sql_files = list(self.backend_path.rglob("*.sql"))
        for file_path in sql_files:
            self.analyze_sql_file(file_path)
            
        self.generate_report()
    
    def analyze_file(self, file_path: Path):
        """Analizar un archivo Python"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            relative_path = file_path.relative_to(self.backend_path)
            
            analysis = {
                'path': str(relative_path),
                'roles': self.extract_roles(content),
                'permissions': self.extract_permissions(content),
                'configs': self.extract_configs(content),
                'imports': self.extract_imports(content),
                'issues': []
            }
            
            self.file_analysis[str(relative_path)] = analysis
            
        except Exception as e:
            print(f"Error analizando {file_path}: {e}")
    
    def analyze_sql_file(self, file_path: Path):
        """Analizar un archivo SQL"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            relative_path = file_path.relative_to(self.backend_path)
            
            analysis = {
                'path': str(relative_path),
                'roles': self.extract_roles_from_sql(content),
                'enums': self.extract_enums_from_sql(content),
                'issues': []
            }
            
            self.file_analysis[str(relative_path)] = analysis
            
        except Exception as e:
            print(f"Error analizando SQL {file_path}: {e}")
    
    def extract_roles(self, content: str) -> Set[str]:
        """Extraer roles del código Python"""
        roles = set()
        
        # Patrones para encontrar roles
        patterns = [
            r'UserRole\.(\w+)',
            r'"(\w+)"\s*:\s*["\'](\w+)["\']',  # Diccionarios
            r'rol\s*=\s*["\'](\w+)["\']',  # Asignaciones de rol
            r'rol\s*==\s*["\'](\w+)["\']',  # Comparaciones de rol
            r'rol\s*in\s*\[([^\]]+)\]',  # Listas de roles
            r'requiredRoles\s*=\s*\[([^\]]+)\]',  # Roles requeridos
            r'ADMIN',  # Rol legacy
            r'COBRANZAS',
            r'GERENTE',
            r'ADMIN',
            r'USER',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    roles.update(match)
                else:
                    roles.add(match)
        
        # Limpiar roles encontrados
        cleaned_roles = set()
        for role in roles:
            if isinstance(role, str) and role.isupper() and len(role) > 1:
                cleaned_roles.add(role)
        
        return cleaned_roles
    
    def extract_roles_from_sql(self, content: str) -> Set[str]:
        """Extraer roles de archivos SQL"""
        roles = set()
        
        # Patrones SQL
        patterns = [
            r"ENUM\s*\(\s*['\"]([^'\"]+)['\"]",  # ENUM definitions
            r"'(\w+)'",  # Valores entre comillas simples
            r'"(\w+)"',  # Valores entre comillas dobles
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if ',' in match:
                    # Separar valores múltiples
                    for role in match.split(','):
                        role = role.strip().strip("'\"")
                        if role.isupper() and len(role) > 1:
                            roles.add(role)
                else:
                    if match.isupper() and len(match) > 1:
                        roles.add(match)
        
        return roles
    
    def extract_permissions(self, content: str) -> Set[str]:
        """Extraer permisos del código"""
        permissions = set()
        
        patterns = [
            r'Permission\.(\w+)',
            r'permission\s*=\s*["\']([^"\']+)["\']',
            r'has_permission\([^,]+,\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            permissions.update(matches)
        
        return permissions
    
    def extract_configs(self, content: str) -> Dict[str, str]:
        """Extraer configuraciones"""
        configs = {}
        
        patterns = [
            r'(\w+)\s*=\s*["\']([^"\']+)["\']',  # Configuraciones simples
            r'(\w+)\s*:\s*str\s*=\s*["\']([^"\']+)["\']',  # Tipos con valores
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for key, value in matches:
                if key.isupper():  # Solo configuraciones en mayúsculas
                    configs[key] = value
        
        return configs
    
    def extract_imports(self, content: str) -> Set[str]:
        """Extraer imports relacionados con roles"""
        imports = set()
        
        patterns = [
            r'from\s+([^\s]+)\s+import\s+([^\n]+)',
            r'import\s+([^\s]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    imports.add(f"{match[0]}.{match[1]}")
                else:
                    imports.add(match)
        
        return imports
    
    def extract_enums_from_sql(self, content: str) -> Set[str]:
        """Extraer enums de archivos SQL"""
        enums = set()
        
        pattern = r'CREATE\s+TYPE\s+(\w+)\s+AS\s+ENUM'
        matches = re.findall(pattern, content, re.IGNORECASE)
        enums.update(matches)
        
        return enums
    
    def generate_report(self):
        """Generar reporte de análisis"""
        print("\nREPORTE DE ANALISIS DE CONFIGURACIONES")
        print("=" * 60)
        
        # Recopilar todos los roles encontrados
        all_roles = set()
        for analysis in self.file_analysis.values():
            all_roles.update(analysis.get('roles', set()))
        
        print(f"\nROLES ENCONTRADOS EN EL SISTEMA:")
        for role in sorted(all_roles):
            print(f"  - {role}")
        
        # Buscar inconsistencias
        self.find_inconsistencies()
        
        # Mostrar archivos con roles
        print(f"\nARCHIVOS QUE CONTIENEN ROLES:")
        for file_path, analysis in self.file_analysis.items():
            if analysis.get('roles'):
                print(f"\n  ARCHIVO: {file_path}")
                for role in sorted(analysis['roles']):
                    print(f"    - {role}")
        
        # Mostrar configuraciones
        print(f"\nCONFIGURACIONES ENCONTRADAS:")
        all_configs = {}
        for analysis in self.file_analysis.values():
            all_configs.update(analysis.get('configs', {}))
        
        for key, value in sorted(all_configs.items()):
            print(f"  - {key} = {value}")
        
        # Mostrar problemas encontrados
        if self.config_inconsistencies:
            print(f"\nPROBLEMAS ENCONTRADOS:")
            for issue in self.config_inconsistencies:
                print(f"  - {issue}")
        else:
            print(f"\nNO SE ENCONTRARON PROBLEMAS DE CONFIGURACION")
    
    def find_inconsistencies(self):
        """Buscar inconsistencias en las configuraciones"""
        # Roles estándar esperados
        expected_roles = {'USER', 'ADMIN', 'GERENTE', 'COBRANZAS'}
        
        # Recopilar todos los roles encontrados
        all_roles = set()
        for analysis in self.file_analysis.values():
            all_roles.update(analysis.get('roles', set()))
        
        # Verificar roles faltantes o extra
        missing_roles = expected_roles - all_roles
        extra_roles = all_roles - expected_roles
        
        if missing_roles:
            self.config_inconsistencies.append(f"Roles faltantes: {missing_roles}")
        
        if extra_roles:
            self.config_inconsistencies.append(f"Roles extra encontrados: {extra_roles}")
        
        # Verificar archivos con definiciones de roles diferentes
        role_definitions = {}
        for file_path, analysis in self.file_analysis.items():
            roles = analysis.get('roles', set())
            if roles:
                role_definitions[file_path] = roles
        
        # Comparar definiciones
        if len(role_definitions) > 1:
            base_roles = None
            for file_path, roles in role_definitions.items():
                if base_roles is None:
                    base_roles = roles
                elif roles != base_roles:
                    self.config_inconsistencies.append(
                        f"Inconsistencia en roles entre archivos: {file_path} tiene {roles} vs base {base_roles}"
                    )

def main():
    """Función principal"""
    analyzer = BackendConfigAnalyzer()
    analyzer.analyze_all_files()
    
    print(f"\nRESUMEN:")
    print(f"  - Archivos analizados: {len(analyzer.file_analysis)}")
    print(f"  - Roles únicos encontrados: {len(set().union(*[a.get('roles', set()) for a in analyzer.file_analysis.values()]))}")
    print(f"  - Problemas encontrados: {len(analyzer.config_inconsistencies)}")

if __name__ == "__main__":
    main()
