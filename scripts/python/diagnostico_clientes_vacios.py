"""
Script de diagnóstico para identificar por qué el endpoint de clientes retorna array vacío
"""

import os
import sys
from pathlib import Path

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    # Configurar encoding para Windows
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    from sqlalchemy import func, nullslast
    from app.core.config import settings
    from app.db.session import SessionLocal
    from app.models.cliente import Cliente
    from app.schemas.cliente import ClienteResponse
    import logging

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    def diagnosticar_clientes():
        """Diagnostica por qué el endpoint retorna array vacío"""
        print("=" * 70)
        print("DIAGNÓSTICO: Endpoint /clientes retorna array vacío")
        print("=" * 70)
        
        db = SessionLocal()
        try:
            # 1. Verificar total de clientes
            print("\n1. VERIFICANDO TOTAL DE CLIENTES")
            print("-" * 70)
            total = db.query(func.count(Cliente.id)).scalar()
            print(f"   ✅ Total de clientes en BD: {total}")
            
            if total == 0:
                print("   ⚠️  No hay clientes en la base de datos")
                return
            
            # 2. Verificar query básica sin paginación
            print("\n2. VERIFICANDO QUERY BÁSICA (sin paginación)")
            print("-" * 70)
            clientes_basicos = db.query(Cliente).limit(5).all()
            print(f"   ✅ Query básica retornó: {len(clientes_basicos)} clientes")
            
            if len(clientes_basicos) == 0:
                print("   ❌ ERROR: Query básica retorna 0 registros aunque total={total}")
                return
            
            # 3. Verificar ordenamiento
            print("\n3. VERIFICANDO ORDENAMIENTO")
            print("-" * 70)
            try:
                query_ordenada = db.query(Cliente).order_by(nullslast(Cliente.fecha_registro.desc()), Cliente.id.desc()).limit(5).all()
                print(f"   ✅ Query con ordenamiento retornó: {len(query_ordenada)} clientes")
                if len(query_ordenada) > 0:
                    print(f"   ✅ Primer cliente ID: {query_ordenada[0].id}")
            except Exception as e:
                print(f"   ❌ ERROR en ordenamiento: {e}")
                # Intentar sin nullslast
                try:
                    query_simple = db.query(Cliente).order_by(Cliente.id.desc()).limit(5).all()
                    print(f"   ✅ Query simple (por ID) retornó: {len(query_simple)} clientes")
                except Exception as e2:
                    print(f"   ❌ ERROR en query simple: {e2}")
            
            # 4. Verificar paginación
            print("\n4. VERIFICANDO PAGINACIÓN")
            print("-" * 70)
            page = 1
            per_page = 20
            offset = (page - 1) * per_page
            
            query_paginada = db.query(Cliente).order_by(nullslast(Cliente.fecha_registro.desc()), Cliente.id.desc()).offset(offset).limit(per_page).all()
            print(f"   ✅ Query paginada (page={page}, per_page={per_page}, offset={offset}) retornó: {len(query_paginada)} clientes")
            
            if len(query_paginada) == 0:
                print("   ❌ ERROR: Query paginada retorna 0 registros")
                # Verificar sin offset
                query_sin_offset = db.query(Cliente).order_by(nullslast(Cliente.fecha_registro.desc()), Cliente.id.desc()).limit(per_page).all()
                print(f"   🔍 Query sin offset retornó: {len(query_sin_offset)} clientes")
                if len(query_sin_offset) > 0:
                    print("   ⚠️  El problema está en el OFFSET")
            
            # 5. Verificar serialización
            print("\n5. VERIFICANDO SERIALIZACIÓN")
            print("-" * 70)
            if len(query_paginada) > 0:
                cliente_prueba = query_paginada[0]
                print(f"   🔍 Intentando serializar cliente ID: {cliente_prueba.id}")
                
                try:
                    cliente_data = ClienteResponse.model_validate(cliente_prueba).model_dump()
                    print(f"   ✅ Serialización exitosa")
                    print(f"   ✅ Campos serializados: {len(cliente_data)} campos")
                    print(f"   ✅ Primeros campos: {list(cliente_data.keys())[:5]}")
                    print(f"   ✅ Teléfono serializado: {cliente_data.get('telefono', 'N/A')}")
                    print(f"   ✅ Teléfono original: {getattr(cliente_prueba, 'telefono', 'N/A')}")
                    if cliente_data.get('telefono') != getattr(cliente_prueba, 'telefono', None):
                        print(f"   ⚠️  ADVERTENCIA: El teléfono fue modificado durante la serialización")
                    else:
                        print(f"   ✅ El teléfono original se restauró correctamente")
                except Exception as e:
                    print(f"   ❌ ERROR en serialización: {e}")
                    print(f"   🔍 Tipo de error: {type(e).__name__}")
                    import traceback
                    traceback.print_exc()
                    
                    # Verificar campos del cliente
                    print(f"\n   🔍 Información del cliente:")
                    print(f"      - ID: {cliente_prueba.id}")
                    print(f"      - Cédula: {getattr(cliente_prueba, 'cedula', 'N/A')}")
                    print(f"      - Nombres: {getattr(cliente_prueba, 'nombres', 'N/A')}")
                    print(f"      - Teléfono: {getattr(cliente_prueba, 'telefono', 'N/A')}")
                    print(f"      - Email: {getattr(cliente_prueba, 'email', 'N/A')}")
                    print(f"      - Fecha registro: {getattr(cliente_prueba, 'fecha_registro', 'N/A')}")
            
            # 6. Verificar campos problemáticos
            print("\n6. VERIFICANDO CAMPOS PROBLEMÁTICOS")
            print("-" * 70)
            clientes_problema = db.query(Cliente).filter(
                (Cliente.telefono == None) | 
                (Cliente.email == None) |
                (Cliente.nombres == None) |
                (Cliente.cedula == None)
            ).limit(10).all()
            
            if len(clientes_problema) > 0:
                print(f"   ⚠️  Encontrados {len(clientes_problema)} clientes con campos NULL")
                for c in clientes_problema[:3]:
                    print(f"      - Cliente ID {c.id}: telefono={c.telefono}, email={c.email}, nombres={c.nombres}, cedula={c.cedula}")
            else:
                print("   ✅ No se encontraron clientes con campos NULL críticos")
            
            print("\n" + "=" * 70)
            print("DIAGNÓSTICO COMPLETADO")
            print("=" * 70)
            
        finally:
            db.close()

    if __name__ == "__main__":
        diagnosticar_clientes()

except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("Asegúrate de estar en el directorio correcto y tener las dependencias instaladas")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
