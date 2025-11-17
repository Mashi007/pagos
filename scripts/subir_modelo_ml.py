"""
Script para subir el modelo ML al repositorio Git
Este script verifica si el archivo del modelo existe localmente y lo prepara para subir a Git
"""

import sys
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.modelo_impago_cuotas import ModeloImpagoCuotas


def main():
    """Verificar y mostrar información sobre el modelo activo"""
    db: Session = SessionLocal()
    
    try:
        # Obtener modelo activo
        modelo_activo = db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.activo.is_(True)).first()
        
        if not modelo_activo:
            print("❌ No hay modelo ML Impago activo en la base de datos")
            return
        
        print(f"✅ Modelo activo encontrado:")
        print(f"   ID: {modelo_activo.id}")
        print(f"   Nombre: {modelo_activo.nombre}")
        print(f"   Ruta en BD: {modelo_activo.ruta_archivo}")
        
        # Verificar si el archivo existe localmente
        ruta_archivo = Path(backend_path) / modelo_activo.ruta_archivo
        
        if ruta_archivo.exists():
            tamaño_kb = ruta_archivo.stat().st_size / 1024
            print(f"\n✅ Archivo encontrado localmente:")
            print(f"   Ruta: {ruta_archivo.absolute()}")
            print(f"   Tamaño: {tamaño_kb:.2f} KB")
            print(f"\n📝 Para subir el archivo al repositorio, ejecuta:")
            print(f"   git add {ruta_archivo.relative_to(Path.cwd())}")
            print(f"   git commit -m 'Agregar modelo ML Impago: {modelo_activo.nombre}'")
            print(f"   git push")
        else:
            print(f"\n❌ Archivo NO encontrado localmente en:")
            print(f"   {ruta_archivo.absolute()}")
            print(f"\n💡 Soluciones:")
            print(f"   1. Reentrenar el modelo desde la aplicación")
            print(f"   2. Si tienes el archivo en otra ubicación, cópialo a:")
            print(f"      {ruta_archivo.absolute()}")
            print(f"   3. Luego ejecuta los comandos git para subirlo")
            
            # Buscar archivos .pkl en el directorio ml_models
            ml_models_dir = backend_path / "ml_models"
            if ml_models_dir.exists():
                archivos_pkl = list(ml_models_dir.glob("*.pkl"))
                if archivos_pkl:
                    print(f"\n📦 Archivos .pkl encontrados en ml_models:")
                    for archivo in archivos_pkl:
                        tamaño_kb = archivo.stat().st_size / 1024
                        print(f"   - {archivo.name} ({tamaño_kb:.2f} KB)")
                        if modelo_activo.ruta_archivo.endswith(archivo.name):
                            print(f"     ⚠️  Este archivo coincide con el nombre del modelo activo")
                            print(f"     💡 Puedes renombrarlo o actualizar la ruta en la BD")
                else:
                    print(f"\n📦 No se encontraron archivos .pkl en {ml_models_dir}")
            else:
                print(f"\n📦 El directorio {ml_models_dir} no existe")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()

