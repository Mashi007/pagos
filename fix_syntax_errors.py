#!/usr/bin/env python3
"""
Script para corregir automáticamente errores E999 (SyntaxError: unterminated string literal)
en archivos Python del proyecto.
"""

import os
import re
import sys
from pathlib import Path

def fix_f_string_syntax(file_path):
    """Corregir f-strings mal formateados en un archivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Patrón para encontrar f-strings mal formateados con saltos de línea
        # Busca f"texto {variable} más texto {otra_variable} final"
        pattern = r'f"([^"]*?)\{\s*([^}]+?)\s*\}([^"]*?)\{\s*([^}]+?)\s*\}([^"]*?)"'
        
        def fix_match(match):
            prefix = match.group(1)
            var1 = match.group(2).strip()
            middle = match.group(3)
            var2 = match.group(4).strip()
            suffix = match.group(5)
            
            # Reconstruir el f-string correctamente
            return f'f"{prefix}{{{var1}}}{middle}{{{var2}}}{suffix}"'
        
        # Aplicar la corrección
        content = re.sub(pattern, fix_match, content, flags=re.DOTALL)
        
        # Patrón más específico para f-strings con saltos de línea problemáticos
        # Busca f"texto {variable} más texto" que se extiende por múltiples líneas
        pattern2 = r'f"([^"]*?)\{\s*([^}]+?)\s*\}([^"]*?)"'
        
        def fix_multiline_match(match):
            prefix = match.group(1)
            var = match.group(2).strip()
            suffix = match.group(3)
            
            # Si hay saltos de línea en el contenido, dividir en múltiples f-strings
            if '\n' in prefix or '\n' in suffix:
                parts = []
                if prefix.strip():
                    parts.append(f'f"{prefix.strip()}"')
                if var:
                    parts.append(f'f"{{{var}}}"')
                if suffix.strip():
                    parts.append(f'f"{suffix.strip()}"')
                return ' '.join(parts)
            else:
                return f'f"{prefix}{{{var}}}{suffix}"'
        
        content = re.sub(pattern2, fix_multiline_match, content, flags=re.DOTALL)
        
        # Si el contenido cambió, escribir el archivo
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Corregido: {file_path}")
            return True
        else:
            print(f"⏭️  Sin cambios: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error procesando {file_path}: {e}")
        return False

def main():
    """Función principal"""
    backend_path = Path("backend/app")
    
    if not backend_path.exists():
        print("❌ No se encontró el directorio backend/app")
        return
    
    # Archivos específicos que tienen errores E999 según el log
    problem_files = [
        "api/v1/endpoints/amortizacion.py",
        "api/v1/endpoints/auth_flow_analyzer.py", 
        "api/v1/endpoints/carga_masiva.py",
        "api/v1/endpoints/carga_masiva_refactored.py",
        "api/v1/endpoints/clientes.py",
        "api/v1/endpoints/comparative_analysis.py",
        "api/v1/endpoints/conciliacion.py",
        "api/v1/endpoints/conciliacion_bancaria.py",
        "api/v1/endpoints/configuracion.py",
        "api/v1/endpoints/dashboard.py",
        "api/v1/endpoints/diagnostico_refresh_token.py",
        "api/v1/endpoints/health.py",
        "api/v1/endpoints/inteligencia_artificial.py",
        "api/v1/endpoints/modelos_vehiculos.py",
        "api/v1/endpoints/notificaciones.py",
        "api/v1/endpoints/predictive_analyzer.py",
        "api/v1/endpoints/predictive_token_analyzer.py",
        "api/v1/endpoints/reportes.py",
        "api/v1/endpoints/solicitudes.py",
        "api/v1/endpoints/temporal_analysis.py",
        "api/v1/endpoints/users.py",
        "api/v1/endpoints/validadores.py",
        "core/error_impact_analysis.py",
        "core/impact_monitoring.py",
        "models/analista.py",
        "models/cliente.py",
        "models/concesionario.py",
        "models/configuracion_sistema.py",
        "models/modelo_vehiculo.py",
        "models/pago.py",
        "models/user.py",
        "services/amortizacion_service.py",
        "services/ml_service.py",
        "services/notification_multicanal_service.py",
        "services/validators_service.py"
    ]
    
    print("🔧 Iniciando corrección automática de errores E999...")
    print(f"📁 Procesando {len(problem_files)} archivos...")
    
    corrected_count = 0
    for file_rel_path in problem_files:
        file_path = backend_path / file_rel_path
        if file_path.exists():
            if fix_f_string_syntax(file_path):
                corrected_count += 1
        else:
            print(f"⚠️  Archivo no encontrado: {file_path}")
    
    print(f"\n🎉 Corrección completada!")
    print(f"📊 Archivos corregidos: {corrected_count}/{len(problem_files)}")

if __name__ == "__main__":
    main()
