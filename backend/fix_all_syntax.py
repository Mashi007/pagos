import os

files_with_issues = [
    "backend/app/api/v1/endpoints/dashboard_conciliacion.py",
    "backend/app/scripts/ejecutar_correcciones_criticas.py",
    "backend/app/api/v1/endpoints/criticos.py",
    "backend/app/services/diagnostico_critico_service.py",
    "backend/app/api/v1/endpoints/auditoria_conciliacion.py",
    "backend/app/api/v1/endpoints/referencia_estados_cuota.py",
    "backend/app/api/v1/endpoints/conciliacion.py",
    "backend/app/models/auditoria_conciliacion_manual.py",
    "backend/app/services/conciliacion_automatica_service.py",
    "backend/app/services/ai_imagen_respuesta.py"
]

fixed_count = 0
for file_path in files_with_issues:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        if '"`"' in content:
            content = content.replace('"`"', '"""')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            fixed_count += 1
        else:
            print(f"No issues found: {file_path}")
    else:
        print(f"File not found: {file_path}")

print(f"\nTotal files fixed: {fixed_count}")
