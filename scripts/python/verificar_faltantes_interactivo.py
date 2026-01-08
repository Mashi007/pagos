"""Verificar datos faltantes de forma interactiva - pega datos de 100 en 100"""
import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.db.session import SessionLocal
from sqlalchemy import text

def buscar_cedulas_en_bd(cedulas):
    """Buscar qué cédulas están en la base de datos"""
    db = SessionLocal()
    try:
        # Crear query con IN clause
        query = text("""
            SELECT cedula 
            FROM tabla_comparacion_externa 
            WHERE cedula = ANY(:cedulas)
        """)
        
        resultado = db.execute(query, {'cedulas': cedulas})
        encontradas = {row[0] for row in resultado.fetchall()}
        
        return encontradas
    finally:
        db.close()

def procesar_lote():
    """Procesar un lote de datos pegados"""
    print("=" * 80)
    print("VERIFICACIÓN DE DATOS FALTANTES")
    print("=" * 80)
    print("")
    print("INSTRUCCIONES:")
    print("1. Pega aquí las cédulas o datos (una por línea)")
    print("2. Puedes pegar solo cédulas o datos completos separados por tab/coma")
    print("3. Escribe 'FIN' en una línea nueva para procesar")
    print("4. Escribe 'SALIR' para terminar")
    print("")
    print("-" * 80)
    
    lineas = []
    while True:
        try:
            linea = input()
            if linea.strip().upper() == 'SALIR':
                return False
            if linea.strip().upper() == 'FIN':
                break
            if linea.strip():
                lineas.append(linea.strip())
        except EOFError:
            break
        except KeyboardInterrupt:
            print("\n\n❌ Cancelado por el usuario")
            return False
    
    if not lineas:
        print("\n❌ No se recibieron datos")
        return True
    
    # Extraer cédulas (primer campo)
    cedulas = []
    for linea in lineas:
        # Separar por tab o coma
        if '\t' in linea:
            campos = linea.split('\t')
        else:
            campos = linea.split(',')
        
        cedula = campos[0].strip() if campos else None
        if cedula:
            cedulas.append(cedula)
    
    if not cedulas:
        print("\n❌ No se encontraron cédulas válidas")
        return True
    
    print(f"\n✅ Procesando {len(cedulas)} cédulas...")
    print("")
    
    # Buscar en BD
    encontradas = buscar_cedulas_en_bd(cedulas)
    faltantes = [c for c in cedulas if c not in encontradas]
    
    # Mostrar resultados
    print("=" * 80)
    print("RESULTADOS:")
    print("=" * 80)
    print(f"Total cédulas procesadas: {len(cedulas)}")
    print(f"Cédulas encontradas en BD: {len(encontradas)}")
    print(f"Cédulas FALTANTES: {len(faltantes)}")
    print("")
    
    if faltantes:
        print("CÉDULAS FALTANTES:")
        print("-" * 80)
        for i, cedula in enumerate(faltantes, 1):
            print(f"{i}. {cedula}")
        print("-" * 80)
        print(f"\n✅ Total faltantes en este lote: {len(faltantes)}")
    else:
        print("✅ Todas las cédulas de este lote están en la base de datos")
    
    print("")
    print("=" * 80)
    
    return True

def main():
    """Función principal"""
    print("=" * 80)
    print("VERIFICACIÓN DE DATOS FALTANTES - MODO INTERACTIVO")
    print("=" * 80)
    print("")
    print("Puedes pegar datos de 100 en 100 para verificar qué falta.")
    print("")
    
    continuar = True
    total_faltantes = []
    
    while continuar:
        continuar = procesar_lote()
        
        if continuar:
            print("")
            respuesta = input("¿Quieres procesar otro lote? (s/n): ").strip().lower()
            if respuesta not in ['s', 'si', 'sí', 'y', 'yes']:
                continuar = False
    
    print("")
    print("=" * 80)
    print("VERIFICACIÓN COMPLETADA")
    print("=" * 80)
    print("")

if __name__ == "__main__":
    main()
