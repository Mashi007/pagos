#!/usr/bin/env python3
"""
Script para corregir automáticamente bloques catch (error: any) → catch (error: unknown)
y agregar imports de getErrorMessage cuando sea necesario
"""
import re
import os
from pathlib import Path

def fix_catch_block(content: str) -> tuple[str, bool]:
    """Corrige bloques catch (error: any) → catch (error: unknown)"""
    modified = False
    
    # Patrón para catch (error: any) o catch (err: any)
    pattern = r'catch\s*\(\s*(\w+)\s*:\s*any\s*\)'
    
    def replace_catch(match):
        nonlocal modified
        var_name = match.group(1)
        modified = True
        return f'catch ({var_name}: unknown)'
    
    new_content = re.sub(pattern, replace_catch, content)
    
    return new_content, modified

def add_error_imports(content: str) -> tuple[str, bool]:
    """Agrega imports de getErrorMessage si se usa pero no está importado"""
    modified = False
    
    # Verificar si usa getErrorMessage o isAxiosError
    uses_get_error_message = 'getErrorMessage' in content or 'isAxiosError' in content
    has_import = 'from \'@/types/errors\'' in content or 'from "@/types/errors"' in content
    
    if uses_get_error_message and not has_import:
        # Buscar el último import statement
        import_pattern = r"(import.*from.*['\"].*['\"];?\n)"
        imports = re.findall(import_pattern, content)
        
        if imports:
            # Agregar después del último import
            last_import = imports[-1]
            new_import = "import { getErrorMessage, isAxiosError } from '@/types/errors'\n"
            
            # Solo agregar si no existe ya
            if new_import.strip() not in content:
                content = content.replace(last_import, last_import + new_import)
                modified = True
    
    return content, modified

def process_file(file_path: Path) -> bool:
    """Procesa un archivo TypeScript/TSX"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Corregir catch blocks
        content, modified1 = fix_catch_block(content)
        
        # Agregar imports si es necesario
        content, modified2 = add_error_imports(content)
        
        if modified1 or modified2:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Corregido: {file_path}")
            return True
        
        return False
    except Exception as e:
        print(f"❌ Error procesando {file_path}: {e}")
        return False

def main():
    """Procesa todos los archivos TypeScript en frontend/src"""
    frontend_src = Path('frontend/src')
    
    if not frontend_src.exists():
        print(f"❌ Directorio {frontend_src} no existe")
        return
    
    files_modified = 0
    total_files = 0
    
    for file_path in frontend_src.rglob('*.{ts,tsx}'):
        # Omitir node_modules y dist
        if 'node_modules' in str(file_path) or 'dist' in str(file_path):
            continue
        
        total_files += 1
        if process_file(file_path):
            files_modified += 1
    
    print(f"\n✅ Procesados {total_files} archivos")
    print(f"✅ Modificados {files_modified} archivos")

if __name__ == '__main__':
    main()

