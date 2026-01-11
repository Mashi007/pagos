#!/usr/bin/env python3
"""
Utilidades para buscar archivos de documentación en la carpeta Documentos
"""

from pathlib import Path
from typing import List, Optional


def buscar_documento_md(nombre_archivo: str, carpeta_base: Optional[Path] = None) -> Optional[Path]:
    """
    Busca un archivo .md en la carpeta Documentos y sus subcarpetas.
    
    Args:
        nombre_archivo: Nombre del archivo a buscar (con o sin extensión .md)
        carpeta_base: Carpeta base del proyecto (default: directorio actual)
    
    Returns:
        Path del archivo encontrado o None si no se encuentra
    """
    if carpeta_base is None:
        carpeta_base = Path.cwd()
    
    # Asegurar que el nombre tenga extensión .md
    if not nombre_archivo.endswith('.md'):
        nombre_archivo = f"{nombre_archivo}.md"
    
    # Buscar en Documentos recursivamente
    documentos_dir = carpeta_base / "Documentos"
    
    if documentos_dir.exists():
        for archivo in documentos_dir.rglob(nombre_archivo):
            return archivo
    
    return None


def listar_documentos_md(carpeta: Optional[str] = None, carpeta_base: Optional[Path] = None) -> List[Path]:
    """
    Lista todos los archivos .md en una carpeta específica dentro de Documentos.
    
    Args:
        carpeta: Subcarpeta dentro de Documentos (ej: "General", "Auditorias", None para todas)
        carpeta_base: Carpeta base del proyecto (default: directorio actual)
    
    Returns:
        Lista de Paths de archivos .md encontrados
    """
    if carpeta_base is None:
        carpeta_base = Path.cwd()
    
    documentos_dir = carpeta_base / "Documentos"
    
    if carpeta:
        documentos_dir = documentos_dir / carpeta
    
    if not documentos_dir.exists():
        return []
    
    return list(documentos_dir.rglob("*.md"))


def obtener_ruta_documento(ruta_relativa: str, carpeta_base: Optional[Path] = None) -> Optional[Path]:
    """
    Obtiene la ruta completa de un documento usando una ruta relativa desde Documentos.
    
    Args:
        ruta_relativa: Ruta relativa desde Documentos (ej: "General/README.md")
        carpeta_base: Carpeta base del proyecto (default: directorio actual)
    
    Returns:
        Path del archivo encontrado o None si no existe
    """
    if carpeta_base is None:
        carpeta_base = Path.cwd()
    
    documento_path = carpeta_base / "Documentos" / ruta_relativa
    
    if documento_path.exists():
        return documento_path
    
    return None
