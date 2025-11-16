#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar el almacenamiento de embeddings
Verifica si la tabla existe, su estructura y datos
"""

import sys
import os
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    os.system('chcp 65001 > nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# Agregar el directorio del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

def verificar_embeddings():
    """Verifica el almacenamiento de embeddings"""
    print("=" * 60)
    print("VERIFICACION DE ALMACENAMIENTO DE EMBEDDINGS")
    print("=" * 60)
    
    try:
        # Crear conexión
        print("\n[1] Conectando a la base de datos...")
        engine = create_engine(settings.DATABASE_URL)
        inspector = inspect(engine)
        
        # 1. Verificar si la tabla existe
        print("\n[1] Verificando existencia de la tabla...")
        tablas = inspector.get_table_names()
        tabla_existe = 'documento_ai_embeddings' in tablas
        
        if tabla_existe:
            print("   [OK] Tabla 'documento_ai_embeddings' EXISTE")
        else:
            print("   [ERROR] Tabla 'documento_ai_embeddings' NO EXISTE")
            print("   [WARN] Necesitas ejecutar las migraciones: alembic upgrade head")
            return
        
        # 2. Verificar estructura de la tabla
        print("\n[2] Verificando estructura de la tabla...")
        columnas = inspector.get_columns('documento_ai_embeddings')
        columnas_esperadas = [
            'id', 'documento_id', 'embedding', 'chunk_index', 
            'texto_chunk', 'modelo_embedding', 'dimensiones',
            'creado_en', 'actualizado_en'
        ]
        
        columnas_encontradas = [col['name'] for col in columnas]
        print(f"   Columnas encontradas: {len(columnas_encontradas)}")
        for col in columnas:
            print(f"      - {col['name']}: {col['type']} (nullable: {col['nullable']})")
        
        faltantes = set(columnas_esperadas) - set(columnas_encontradas)
        if faltantes:
            print(f"   [WARN] Columnas faltantes: {faltantes}")
        else:
            print("   [OK] Todas las columnas esperadas estan presentes")
        
        # 3. Verificar índices
        print("\n[3] Verificando indices...")
        indices = inspector.get_indexes('documento_ai_embeddings')
        print(f"   Índices encontrados: {len(indices)}")
        for idx in indices:
            print(f"      - {idx['name']}: {idx['column_names']}")
        
        # 4. Verificar Foreign Keys
        print("\n[4] Verificando Foreign Keys...")
        fks = inspector.get_foreign_keys('documento_ai_embeddings')
        if fks:
            for fk in fks:
                print(f"      - {fk['name']}: {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
        else:
            print("   [WARN] No se encontraron Foreign Keys")
        
        # 5. Contar registros
        print("\n[5] Contando registros...")
        with engine.connect() as conn:
            # Total embeddings
            result = conn.execute(text("SELECT COUNT(*) FROM documento_ai_embeddings"))
            total_embeddings = result.scalar() or 0
            print(f"   Total embeddings: {total_embeddings}")
            
            # Documentos con embeddings
            result = conn.execute(text("SELECT COUNT(DISTINCT documento_id) FROM documento_ai_embeddings"))
            documentos_con_embeddings = result.scalar() or 0
            print(f"   Documentos con embeddings: {documentos_con_embeddings}")
            
            # Modelos usados
            result = conn.execute(text("""
                SELECT modelo_embedding, dimensiones, COUNT(*) as cantidad
                FROM documento_ai_embeddings
                GROUP BY modelo_embedding, dimensiones
            """))
            modelos = result.fetchall()
            if modelos:
                print("   Modelos de embedding usados:")
                for modelo, dim, cantidad in modelos:
                    print(f"      - {modelo} (dimensiones: {dim}): {cantidad} embeddings")
            else:
                print("   [WARN] No hay embeddings generados aun")
            
            # Fechas
            result = conn.execute(text("""
                SELECT 
                    MIN(creado_en) as primer_embedding,
                    MAX(creado_en) as ultimo_embedding
                FROM documento_ai_embeddings
            """))
            fechas = result.fetchone()
            if fechas and fechas[0]:
                print(f"   Primer embedding: {fechas[0]}")
                print(f"   Último embedding: {fechas[1]}")
        
        # 6. Verificar documentos activos disponibles
        print("\n[6] Verificando documentos disponibles...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE activo = true) as activos,
                    COUNT(*) FILTER (WHERE contenido_procesado = true) as procesados,
                    COUNT(*) FILTER (WHERE activo = true AND contenido_procesado = true) as activos_procesados
                FROM documentos_ai
            """))
            stats = result.fetchone()
            if stats:
                print(f"   Total documentos: {stats[0]}")
                print(f"   Documentos activos: {stats[1]}")
                print(f"   Documentos procesados: {stats[2]}")
                print(f"   Documentos activos y procesados: {stats[3]}")
        
        # 7. Verificar relación documentos-embeddings
        print("\n[7] Verificando relacion documentos-embeddings...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    d.id,
                    d.titulo,
                    d.activo,
                    d.contenido_procesado,
                    COUNT(e.id) as total_embeddings
                FROM documentos_ai d
                LEFT JOIN documento_ai_embeddings e ON d.id = e.documento_id
                GROUP BY d.id, d.titulo, d.activo, d.contenido_procesado
                ORDER BY total_embeddings DESC
                LIMIT 10
            """))
            documentos = result.fetchall()
            if documentos:
                print("   Top 10 documentos:")
                for doc_id, titulo, activo, procesado, embeddings in documentos:
                    estado = "[OK]" if activo and procesado else "[WARN]"
                    titulo_safe = (titulo or '')[:40] if titulo else ''
                    print(f"      {estado} [{doc_id}] {titulo_safe:<40} - {embeddings} embeddings")
        
        # 8. Resumen final
        print("\n" + "=" * 60)
        print("RESUMEN")
        print("=" * 60)
        print(f"[OK] Tabla existe: {tabla_existe}")
        print(f"[OK] Total embeddings: {total_embeddings}")
        print(f"[OK] Documentos con embeddings: {documentos_con_embeddings}")
        
        if total_embeddings == 0:
            print("\n[WARN] NO HAY EMBEDDINGS GENERADOS")
            print("   Para generar embeddings:")
            print("   1. Ve a Configuracion > AI > RAG")
            print("   2. Sube y procesa documentos")
            print("   3. Haz clic en 'Generar Embeddings'")
        else:
            print("\n[OK] El sistema de embeddings esta funcionando correctamente")
            print("   El chat AI usara busqueda semantica cuando haya embeddings disponibles")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] Error durante la verificacion: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    verificar_embeddings()

