#!/usr/bin/env python3
"""
Script para verificar y corregir TODAS las importaciones incorrectas en el proyecto
"""
import os
import re
from pathlib import Path
from typing import List, Tuple

class ImportFixer:
    def __init__(self, base_dir: str = "backend/app"):
        self.base_dir = Path(base_dir)
        self.corrections = []
        
    def find_python_files(self) -> List[Path]:
        """Encuentra todos los archivos .py"""
        return list(self.base_dir.rglob("*.py"))
    
    def check_imports(self, filepath: Path) -> List[str]:
        """Verifica qué importaciones incorrectas tiene un archivo"""
        issues = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Buscar diferentes patrones de importación incorrecta
            patterns = [
                (r'from app\.config import', 'from app.core.config import'),
                (r'from app\.settings import', 'from app.core.config import'),
            ]
            
            for old_pattern, new_pattern in patterns:
                if re.search(old_pattern, content):
                    issues.append(f"❌ {old_pattern} → debe ser → {new_pattern}")
                    
        except Exception as e:
            issues.append(f"⚠️  Error leyendo archivo: {e}")
            
        return issues
    
    def fix_imports(self, filepath: Path) -> Tuple[bool, List[str]]:
        """Corrige las importaciones en un archivo"""
        changes = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                original = f.read()
            
            content = original
            
            # Aplicar correcciones
            replacements = [
                (r'from app\.config import', 'from app.core.config import'),
                (r'from app\.settings import', 'from app.core.config import'),
            ]
            
            for old_pattern, new_text in replacements:
                if re.search(old_pattern, content):
                    content = re.sub(old_pattern, new_text, content)
                    changes.append(f"  ✅ {old_pattern} → {new_text}")
            
            # Guardar si hubo cambios
            if content != original:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True, changes
            
            return False, []
            
        except Exception as e:
            return False, [f"❌ Error: {e}"]
    
    def scan_project(self):
        """Escanea todo el proyecto buscando problemas"""
        print("🔍 ESCANEANDO PROYECTO...")
        print("="*60)
        
        files = self.find_python_files()
        problematic_files = []
        
        for filepath in files:
            issues = self.check_imports(filepath)
            if issues:
                problematic_files.append((filepath, issues))
        
        if not problematic_files:
            print("✅ No se encontraron problemas de importación")
            return []
        
        print(f"\n📋 ARCHIVOS CON PROBLEMAS ({len(problematic_files)}):\n")
        
        for filepath, issues in problematic_files:
            rel_path = filepath.relative_to(self.base_dir.parent)
            print(f"📄 {rel_path}")
            for issue in issues:
                print(f"   {issue}")
            print()
        
        return problematic_files
    
    def fix_all(self):
        """Corrige todos los archivos"""
        print("\n🔧 APLICANDO CORRECCIONES...")
        print("="*60)
        
        files = self.find_python_files()
        fixed_count = 0
        
        for filepath in files:
            was_fixed, changes = self.fix_imports(filepath)
            
            if was_fixed:
                rel_path = filepath.relative_to(self.base_dir.parent)
                print(f"\n✅ {rel_path}")
                for change in changes:
                    print(change)
                fixed_count += 1
        
        print(f"\n{'='*60}")
        print(f"✅ TOTAL DE ARCHIVOS CORREGIDOS: {fixed_count}")
        
        # Verificación final
        print(f"\n🔍 VERIFICACIÓN FINAL...")
        remaining = self.scan_project()
        
        if not remaining:
            print("\n✅ TODAS LAS IMPORTACIONES FUERON CORREGIDAS")
        else:
            print(f"\n⚠️  Aún quedan {len(remaining)} archivos con problemas")
    
    def generate_report(self):
        """Genera reporte de problemas"""
        print("\n📊 GENERANDO REPORTE...")
        print("="*60)
        
        problematic = self.scan_project()
        
        if not problematic:
            return
        
        # Guardar reporte
        report_path = Path("import_issues_report.txt")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("REPORTE DE PROBLEMAS DE IMPORTACIÓN\n")
            f.write("="*60 + "\n\n")
            
            for filepath, issues in problematic:
                rel_path = filepath.relative_to(self.base_dir.parent)
                f.write(f"Archivo: {rel_path}\n")
                for issue in issues:
                    f.write(f"  {issue}\n")
                f.write("\n")
        
        print(f"📝 Reporte guardado en: {report_path}")


def main():
    print("🚀 VERIFICADOR Y CORRECTOR DE IMPORTACIONES")
    print("="*60)
    
    fixer = ImportFixer()
    
    # Escanear
    problematic = fixer.scan_project()
    
    if not problematic:
        print("\n🎉 ¡No hay problemas de importación!")
        return
    
    # Preguntar si corregir
    print("\n" + "="*60)
    response = input("¿Deseas corregir automáticamente estos archivos? (s/n): ").strip().lower()
    
    if response in ['s', 'si', 'sí', 'y', 'yes']:
        fixer.fix_all()
        
        print("\n📝 PRÓXIMOS PASOS:")
        print("  1. Revisar cambios: git diff")
        print("  2. Eliminar archivos __init__.py problemáticos:")
        print("     - backend/app/api/v1/__init__.py")
        print("     - backend/app/api/v1/endpoints/__init__.py")
        print("  3. Reemplazar backend/app/main.py con el corregido")
        print("  4. Reiniciar servidor: uvicorn app.main:app --reload")
    else:
        print("\n📊 Generando solo reporte...")
        fixer.generate_report()
        print("\n❌ Correcciones canceladas")


if __name__ == "__main__":
    main()
