#!/usr/bin/env python3
"""
Script para corregir errores críticos de sintaxis detectados por GitHub Actions
Corrige los 83 errores más comunes de forma sistemática
"""

import os
import re
import glob
from pathlib import Path

def fix_unterminated_triple_quotes(file_path):
    """Corregir triple-quoted strings no terminadas"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Buscar triple quotes no cerradas al final del archivo
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            # Si la línea tiene triple quotes pero no está cerrada
            if '"""' in line and line.count('"""') == 1:
                # Si es la última línea o la siguiente no tiene triple quotes
                if i == len(lines) - 1 or '"""' not in lines[i + 1]:
                    # Agregar triple quotes de cierre
                    fixed_lines.append(line + '"""')
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        if fixed_lines != lines:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(fixed_lines))
            print(f"[OK] Corregido: {file_path}")
            return True
    except Exception as e:
        print(f"[ERROR] Error en {file_path}: {e}")
    return False

def fix_incomplete_imports(file_path):
    """Corregir imports incompletos"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Patrones comunes de imports rotos
        patterns = [
            (r'from app\.schemas\.(\w+) import \s*$', r'from app.schemas.\1 import \1Create, \1Update, \1Response'),
            (r'from app\.models\.(\w+) import \s*$', r'from app.models.\1 import \1'),
            (r'(\w+) = \s*$', r'\1 = None'),
            (r'(\w+) = \s*\n', r'\1 = None\n'),
        ]

        original_content = content
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[OK] Corregido imports: {file_path}")
            return True
    except Exception as e:
        print(f"[ERROR] Error en {file_path}: {e}")
    return False

def fix_indentation_errors(file_path):
    """Corregir errores de indentación comunes"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # Corregir líneas que empiezan con espacios incorrectos
            if re.match(r'^\s{1,3}[a-zA-Z_]', line) and not re.match(r'^\s{4}[a-zA-Z_]', line):
                # Si tiene indentación incorrecta, corregir a múltiplos de 4
                indent_match = re.match(r'^(\s+)', line)
                if indent_match:
                    indent = indent_match.group(1)
                    if len(indent) % 4 != 0:
                        # Corregir a múltiplo de 4 más cercano
                        new_indent = ' ' * ((len(indent) // 4 + 1) * 4)
                        line = re.sub(r'^\s+', new_indent, line)

            fixed_lines.append(line)

        if fixed_lines != lines:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(fixed_lines))
            print(f"[OK] Corregido indentación: {file_path}")
            return True
    except Exception as e:
        print(f"[ERROR] Error en {file_path}: {e}")
    return False

def fix_unmatched_brackets(file_path):
    """Corregir paréntesis y llaves no balanceados"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Buscar líneas con paréntesis/llaves no balanceados
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # Si la línea tiene un paréntesis abierto pero no cerrado
            if '(' in line and ')' not in line and not line.strip().endswith(','):
                # Agregar paréntesis de cierre
                line = line.rstrip() + ')'
            # Si la línea tiene una llave abierta pero no cerrada
            elif '{' in line and '}' not in line and not line.strip().endswith(','):
                # Agregar llave de cierre
                line = line.rstrip() + '}'

            fixed_lines.append(line)

        if fixed_lines != lines:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(fixed_lines))
            print(f"[OK] Corregido brackets: {file_path}")
            return True
    except Exception as e:
        print(f"[ERROR] Error en {file_path}: {e}")
    return False

def main():
    """Función principal para corregir errores"""
    backend_dir = Path("backend")

    if not backend_dir.exists():
        print("[ERROR] Directorio backend no encontrado")
        return

    # Archivos con errores críticos según GitHub Actions
    critical_files = [
        "app/api/v1/endpoints/amortizacion.py",
        "app/api/v1/endpoints/analistas.py",
        "app/api/v1/endpoints/aprobaciones.py",
        "app/api/v1/endpoints/architectural_analysis.py",
        "app/api/v1/endpoints/auditoria.py",
        "app/api/v1/endpoints/auth_flow_analyzer.py",
        "app/api/v1/endpoints/carga_masiva.py",
        "app/api/v1/endpoints/clientes.py",
        "app/api/v1/endpoints/comparative_analysis.py",
        "app/api/v1/endpoints/concesionarios.py",
        "app/api/v1/endpoints/conciliacion.py",
        "app/api/v1/endpoints/conciliacion_bancaria.py",
        "app/api/v1/endpoints/configuracion.py",
        "app/api/v1/endpoints/critical_error_monitor.py",
        "app/api/v1/endpoints/cross_validation_auth.py",
        "app/api/v1/endpoints/dashboard.py",
        "app/api/v1/endpoints/dashboard_diagnostico.py",
        "app/api/v1/endpoints/diagnostico.py",
        "app/api/v1/endpoints/diagnostico_auth.py",
        "app/api/v1/endpoints/diagnostico_refresh_token.py",
        "app/api/v1/endpoints/forensic_analysis.py",
        "app/api/v1/endpoints/impact_analysis.py",
        "app/api/v1/endpoints/inteligencia_artificial.py",
        "app/api/v1/endpoints/intelligent_alerts.py",
        "app/api/v1/endpoints/intelligent_alerts_system.py",
        "app/api/v1/endpoints/intermittent_failure_analyzer.py",
        "app/api/v1/endpoints/migracion_emergencia.py",
        "app/api/v1/endpoints/network_diagnostic.py",
        "app/api/v1/endpoints/notificaciones.py",
        "app/api/v1/endpoints/notificaciones_multicanal.py",
        "app/api/v1/endpoints/pagos.py",
        "app/api/v1/endpoints/predictive_analyzer.py",
        "app/api/v1/endpoints/predictive_token_analyzer.py",
        "app/api/v1/endpoints/real_time_monitor.py",
        "app/api/v1/endpoints/realtime_specific_monitor.py",
        "app/api/v1/endpoints/reportes.py",
        "app/api/v1/endpoints/solicitudes.py",
        "app/api/v1/endpoints/strategic_measurements.py",
        "app/api/v1/endpoints/temporal_analysis.py",
        "app/api/v1/endpoints/token_verification.py",
        "app/api/v1/endpoints/users.py",
        "app/api/v1/endpoints/validadores.py",
        "app/api/v1/endpoints/verificar_concesionarios.py",
        "app/core/config.py",
        "app/core/endpoint_specific_analysis.py",
        "app/core/error_impact_analysis.py",
        "app/core/impact_monitoring.py",
        "app/core/permissions_simple.py",
        "app/core/security.py",
        "app/db/init_db.py",
        "app/db/session.py",
        "app/models/__init__.py",
        "app/models/amortizacion.py",
        "app/models/analista.py",
        "app/models/aprobacion.py",
        "app/models/auditoria.py",
        "app/models/cliente.py",
        "app/models/concesionario.py",
        "app/models/configuracion_sistema.py",
        "app/models/modelo_vehiculo.py",
        "app/models/notificacion.py",
        "app/models/pago.py",
        "app/models/prestamo.py",
        "app/models/user.py",
        "app/schemas/conciliacion.py",
        "app/schemas/kpis.py",
        "app/schemas/notificacion.py",
        "app/schemas/prestamo.py",
        "app/schemas/reportes.py",
        "app/schemas/user.py",
        "app/services/__init__.py",
        "app/services/auth_service.py",
        "app/services/email_service.py",
        "app/services/logging_config.py",
        "app/services/ml_service.py",
        "app/services/notification_multicanal_service.py",
        "app/services/validators_service.py",
        "app/services/whatsapp_service.py",
        "app/utils/__init__.py",
        "app/utils/analistas_cache.py",
        "app/utils/auditoria_helper.py",
        "app/utils/date_helpers.py",
        "app/utils/validators.py",
    ]

    print(f"[INFO] Iniciando corrección de {len(critical_files)} archivos críticos...")

    fixed_count = 0
    for file_path in critical_files:
        full_path = backend_dir / file_path
        if full_path.exists():
            print(f"[INFO] Procesando: {file_path}")

            # Aplicar todas las correcciones
            if (fix_unterminated_triple_quotes(full_path) or
                fix_incomplete_imports(full_path) or
                fix_indentation_errors(full_path) or
                fix_unmatched_brackets(full_path)):
                fixed_count += 1
        else:
            print(f"[WARN] Archivo no encontrado: {file_path}")

    print(f"\n[OK] Corrección completada: {fixed_count} archivos corregidos")
    print("[INFO] Ejecuta 'flake8 app/ --count --select=E9,F63,F7,F82' para verificar")

if __name__ == "__main__":
    main()
