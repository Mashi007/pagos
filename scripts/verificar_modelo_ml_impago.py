#!/usr/bin/env python3
"""
Script para verificar el archivo .pkl del modelo ML de impago de cuotas
Verifica:
1. Si hay un modelo activo en la BD
2. Si el archivo .pkl existe en la ruta especificada
3. Si el archivo es accesible y válido
4. Lista todos los archivos .pkl disponibles
"""

import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.modelo_impago_cuotas import ModeloImpagoCuotas
import pickle
import os


def verificar_modelo_activo(db: Session) -> ModeloImpagoCuotas | None:
    """Verificar si hay un modelo activo en la base de datos"""
    print("=" * 80)
    print("1. VERIFICANDO MODELO ACTIVO EN BASE DE DATOS")
    print("=" * 80)
    
    modelo_activo = db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.activo.is_(True)).first()
    
    if not modelo_activo:
        print("❌ No hay modelo ML Impago activo en la base de datos")
        print("\n📋 Modelos disponibles (inactivos):")
        modelos = db.query(ModeloImpagoCuotas).order_by(ModeloImpagoCuotas.entrenado_en.desc()).all()
        if modelos:
            for modelo in modelos:
                print(f"   - ID: {modelo.id}, Nombre: {modelo.nombre}, Activo: {modelo.activo}")
                print(f"     Ruta: {modelo.ruta_archivo}")
                print(f"     Entrenado: {modelo.entrenado_en}")
        else:
            print("   No hay modelos en la base de datos")
        return None
    
    print(f"✅ Modelo activo encontrado:")
    print(f"   ID: {modelo_activo.id}")
    print(f"   Nombre: {modelo_activo.nombre}")
    print(f"   Algoritmo: {modelo_activo.algoritmo}")
    print(f"   Ruta en BD: {modelo_activo.ruta_archivo}")
    print(f"   Accuracy: {modelo_activo.accuracy}")
    print(f"   Entrenado: {modelo_activo.entrenado_en}")
    
    return modelo_activo


def verificar_archivo_pkl(ruta_archivo: str) -> dict:
    """Verificar si el archivo .pkl existe y es accesible"""
    print("\n" + "=" * 80)
    print("2. VERIFICANDO ARCHIVO .PKL")
    print("=" * 80)
    
    resultado = {
        "archivo_encontrado": False,
        "ruta_absoluta": None,
        "tamaño_bytes": None,
        "es_valido": False,
        "error": None,
        "rutas_buscadas": [],
    }
    
    # Rutas a buscar
    rutas_buscar = []
    
    # Ruta original
    ruta_original = Path(ruta_archivo)
    rutas_buscar.append(("Ruta original", ruta_original))
    
    # Si es relativa, buscar en diferentes ubicaciones
    if not ruta_original.is_absolute():
        # Directorio ml_models en el directorio actual
        rutas_buscar.append(("ml_models/", Path("ml_models") / ruta_archivo))
        
        # Si tiene directorio en la ruta, extraer solo el nombre del archivo
        if "/" in ruta_archivo or "\\" in ruta_archivo:
            filename = Path(ruta_archivo).parts[-1]
            rutas_buscar.append(("ml_models/filename", Path("ml_models") / filename))
        
        # Directorio raíz del proyecto
        project_root = Path(__file__).parent.parent
        rutas_buscar.append(("project_root/ml_models/", project_root / "ml_models" / ruta_archivo))
        if "/" in ruta_archivo or "\\" in ruta_archivo:
            filename = Path(ruta_archivo).parts[-1]
            rutas_buscar.append(("project_root/ml_models/filename", project_root / "ml_models" / filename))
        
        # Directorio de trabajo actual
        rutas_buscar.append(("cwd/", Path.cwd() / ruta_archivo))
        if "/" in ruta_archivo or "\\" in ruta_archivo:
            filename = Path(ruta_archivo).parts[-1]
            rutas_buscar.append(("cwd/filename", Path.cwd() / filename))
    
    resultado["rutas_buscadas"] = [str(ruta) for _, ruta in rutas_buscar]
    
    print(f"🔍 Buscando archivo: {ruta_archivo}")
    print(f"   Total de rutas a verificar: {len(rutas_buscar)}\n")
    
    for descripcion, ruta in rutas_buscar:
        ruta_abs = ruta.absolute()
        existe = ruta.exists()
        es_archivo = ruta.is_file() if existe else False
        
        print(f"   [{descripcion}] {ruta_abs}")
        print(f"      Existe: {'✅' if existe else '❌'}, Es archivo: {'✅' if es_archivo else '❌'}")
        
        if existe and es_archivo:
            resultado["archivo_encontrado"] = True
            resultado["ruta_absoluta"] = str(ruta_abs)
            resultado["tamaño_bytes"] = ruta.stat().st_size
            print(f"      ✅ Archivo encontrado!")
            print(f"      Tamaño: {resultado['tamaño_bytes'] / 1024:.2f} KB")
            
            # Intentar cargar el archivo para verificar que es válido
            try:
                with open(ruta, "rb") as f:
                    modelo = pickle.load(f)
                resultado["es_valido"] = True
                print(f"      ✅ Archivo válido (pickle)")
                print(f"      Tipo de modelo: {type(modelo).__name__}")
            except Exception as e:
                resultado["es_valido"] = False
                resultado["error"] = str(e)
                print(f"      ❌ Error al cargar archivo: {e}")
            
            break
    
    if not resultado["archivo_encontrado"]:
        print(f"\n❌ Archivo no encontrado en ninguna de las rutas buscadas")
    
    return resultado


def listar_archivos_pkl() -> list:
    """Listar todos los archivos .pkl disponibles"""
    print("\n" + "=" * 80)
    print("3. LISTANDO ARCHIVOS .PKL DISPONIBLES")
    print("=" * 80)
    
    archivos_encontrados = []
    directorios_buscar = [
        ("ml_models/", Path("ml_models")),
        ("project_root/ml_models/", Path(__file__).parent.parent / "ml_models"),
        ("cwd/", Path.cwd()),
    ]
    
    for descripcion, directorio in directorios_buscar:
        if directorio.exists() and directorio.is_dir():
            archivos_pkl = list(directorio.glob("*.pkl"))
            if archivos_pkl:
                print(f"\n📁 {descripcion} ({directorio.absolute()}):")
                for archivo in sorted(archivos_pkl):
                    tamaño = archivo.stat().st_size
                    print(f"   - {archivo.name} ({tamaño / 1024:.2f} KB)")
                    archivos_encontrados.append({
                        "ruta": str(archivo.absolute()),
                        "nombre": archivo.name,
                        "tamaño": tamaño,
                        "directorio": descripcion,
                    })
        else:
            print(f"\n📁 {descripcion}: Directorio no existe")
    
    if not archivos_encontrados:
        print("\n❌ No se encontraron archivos .pkl en ningún directorio")
    
    return archivos_encontrados


def main():
    """Función principal"""
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE MODELO ML IMPAGO DE CUOTAS")
    print("=" * 80 + "\n")
    
    db: Session = SessionLocal()
    try:
        # 1. Verificar modelo activo
        modelo_activo = verificar_modelo_activo(db)
        
        if modelo_activo:
            # 2. Verificar archivo .pkl
            resultado_archivo = verificar_archivo_pkl(modelo_activo.ruta_archivo)
            
            # 3. Listar todos los archivos .pkl
            archivos_disponibles = listar_archivos_pkl()
            
            # Resumen
            print("\n" + "=" * 80)
            print("RESUMEN")
            print("=" * 80)
            
            if resultado_archivo["archivo_encontrado"]:
                print("✅ El archivo .pkl del modelo activo EXISTE y es ACCESIBLE")
                if resultado_archivo["es_valido"]:
                    print("✅ El archivo es VÁLIDO (se puede cargar con pickle)")
                else:
                    print("❌ El archivo NO es válido (error al cargar)")
                    print(f"   Error: {resultado_archivo['error']}")
            else:
                print("❌ El archivo .pkl del modelo activo NO EXISTE")
                print(f"   Ruta en BD: {modelo_activo.ruta_archivo}")
                print(f"\n💡 SUGERENCIAS:")
                print("   1. Verificar que el archivo existe en la ruta especificada")
                print("   2. Verificar permisos de acceso al archivo")
                print("   3. Si el archivo fue movido, actualizar la ruta en la BD")
                if archivos_disponibles:
                    print(f"\n   Archivos .pkl disponibles ({len(archivos_disponibles)}):")
                    for archivo in archivos_disponibles[:5]:  # Mostrar solo los primeros 5
                        print(f"      - {archivo['nombre']} ({archivo['ruta']})")
        else:
            print("\n" + "=" * 80)
            print("RESUMEN")
            print("=" * 80)
            print("❌ No hay modelo activo en la base de datos")
            print("\n💡 SUGERENCIAS:")
            print("   1. Entrenar un nuevo modelo desde la sección de configuración AI")
            print("   2. Activar un modelo existente desde la sección de configuración AI")
            
            # Listar archivos disponibles por si acaso
            archivos_disponibles = listar_archivos_pkl()
            if archivos_disponibles:
                print(f"\n   Archivos .pkl disponibles ({len(archivos_disponibles)}):")
                for archivo in archivos_disponibles[:5]:
                    print(f"      - {archivo['nombre']} ({archivo['ruta']})")
    
    except Exception as e:
        print(f"\n❌ Error durante la verificación: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()

