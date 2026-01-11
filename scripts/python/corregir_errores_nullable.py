"""
Script para corregir errores introducidos por corregir_nullable_fase1.py
Elimina nullable de dentro de tipos (Numeric(12, 2, nullable=False) -> Numeric(12, 2))
"""

import re
from pathlib import Path

PROYECTO_ROOT = Path(__file__).parent.parent.parent
BACKEND_MODELS = PROYECTO_ROOT / "backend" / "app" / "models"

def corregir_errores_nullable_en_archivo(archivo_path: Path):
    """Corrige errores de nullable dentro de tipos"""
    cambios = []
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        contenido_original = contenido
        
        # Corregir Numeric(..., nullable=...)
        def corregir_numeric(match):
            precision = match.group(1)
            scale = match.group(2)
            nullable_val = match.group(3)
            resto = match.group(4)
            nuevo_nullable = match.group(5)
            
            cambios.append(f"Numeric({precision}, {scale}) - removido nullable de dentro del tipo")
            return f"Numeric({precision}, {scale}){resto}, nullable={nuevo_nullable}"
        
        # Patrón: Numeric(precision, scale, nullable=X), nullable=Y
        patron_numeric = r'Numeric\((\d+),\s*(\d+),\s*nullable=(True|False)\)(.*?), nullable=(True|False)'
        contenido = re.sub(patron_numeric, corregir_numeric, contenido)
        
        # Corregir String(..., nullable=...)
        def corregir_string(match):
            longitud = match.group(1)
            nullable_val = match.group(2)
            resto = match.group(3)
            nuevo_nullable = match.group(4)
            
            cambios.append(f"String({longitud}) - removido nullable de dentro del tipo")
            return f"String({longitud}){resto}, nullable={nuevo_nullable}"
        
        patron_string = r'String\((\d+),\s*nullable=(True|False)\)(.*?), nullable=(True|False)'
        contenido = re.sub(patron_string, corregir_string, contenido)
        
        # Corregir DateTime(timezone=True, nullable=...)
        def corregir_datetime(match):
            timezone = match.group(1)
            nullable_val = match.group(2)
            resto = match.group(3)
            nuevo_nullable = match.group(4)
            
            cambios.append(f"DateTime(timezone={timezone}) - removido nullable de dentro del tipo")
            return f"DateTime(timezone={timezone}){resto}, nullable={nuevo_nullable}"
        
        patron_datetime = r'DateTime\(timezone=(True|False),\s*nullable=(True|False)\)(.*?), nullable=(True|False)'
        contenido = re.sub(patron_datetime, corregir_datetime, contenido)
        
        # Corregir ForeignKey(..., nullable=...)
        def corregir_fk(match):
            tabla = match.group(1)
            nullable_val = match.group(2)
            resto = match.group(3)
            nuevo_nullable = match.group(4)
            
            cambios.append(f"ForeignKey({tabla}) - removido nullable de dentro del tipo")
            return f"ForeignKey({tabla}){resto}, nullable={nuevo_nullable}"
        
        patron_fk = r'ForeignKey\(([^,)]+),\s*nullable=(True|False)\)(.*?), nullable=(True|False)'
        contenido = re.sub(patron_fk, corregir_fk, contenido)
        
        # Corregir func.now(, nullable=...)
        contenido = re.sub(r'func\.now\(\s*,\s*nullable=(True|False)\)', 'func.now()', contenido)
        
        # Guardar solo si hubo cambios
        if contenido != contenido_original:
            with open(archivo_path, 'w', encoding='utf-8') as f:
                f.write(contenido)
            return cambios
        
    except Exception as e:
        print(f"Error corrigiendo {archivo_path}: {e}")
    
    return cambios


def main():
    """Función principal"""
    import sys
    import io
    
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 100)
    print("CORRECCIÓN DE ERRORES: Nullable dentro de tipos")
    print("=" * 100)
    print("")
    
    archivos_a_corregir = [
        'cliente.py',
        'amortizacion.py',
        'pago.py',
        'prestamo.py',
        'user.py'
    ]
    
    total_cambios = 0
    
    for archivo_nombre in archivos_a_corregir:
        archivo_path = BACKEND_MODELS / archivo_nombre
        if not archivo_path.exists():
            continue
        
        print(f"[PROCESANDO] {archivo_nombre}...")
        cambios = corregir_errores_nullable_en_archivo(archivo_path)
        
        if cambios:
            print(f"  ✅ {len(cambios)} correcciones realizadas")
            for cambio in cambios[:5]:
                print(f"    - {cambio}")
            if len(cambios) > 5:
                print(f"    ... y {len(cambios) - 5} más")
            total_cambios += len(cambios)
        else:
            print(f"  ℹ️  Sin correcciones necesarias")
        print("")
    
    print("=" * 100)
    print(f"RESUMEN: {total_cambios} correcciones realizadas")
    print("=" * 100)


if __name__ == "__main__":
    main()
