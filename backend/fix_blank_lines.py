"""
Script to fix blank lines with whitespace in Python files
"""
import re
import os

files_to_fix = [
    "app/api/v1/endpoints/analistas.py",
    "app/api/v1/endpoints/auth.py",
    "app/models/concesionario.py",
    "app/api/v1/endpoints/validadores.py",
    "app/services/validators_service.py"
]

for file_path in files_to_fix:
    full_path = os.path.join("backend", file_path)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove whitespace from blank lines
        content = re.sub(r'^[ \t]+$', '', content, flags=re.MULTILINE)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed: {file_path}")

