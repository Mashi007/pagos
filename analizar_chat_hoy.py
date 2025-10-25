#!/usr/bin/env python3
"""
Script para analizar el último chat de hoy
Obtiene las notificaciones más recientes del sistema
"""
import os
import sys
import logging
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Any

# Agregar el directorio backend al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.config import settings
from app.models.notificacion import Notificacion
from app.models.cliente import Cliente
from app.models.user import User

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def conectar_base_datos():
    """Conectar a la base de datos"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    except Exception as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        return None

def obtener_notificaciones_hoy(db) -> List[Dict[str, Any]]:
    """Obtener notificaciones del día de hoy"""
    try:
        hoy = date.today()
        
        # Consultar notificaciones de hoy ordenadas por fecha de creación descendente
        notificaciones = db.query(Notificacion).filter(
            func.date(Notificacion.creado_en) == hoy
        ).order_by(desc(Notificacion.creado_en)).limit(50).all()
        
        logger.info(f"Encontradas {len(notificaciones)} notificaciones de hoy")
        
        # Convertir a diccionarios con información relevante
        notificaciones_data = []
        for notif in notificaciones:
            # Obtener información del cliente si existe
            cliente_info = None
            if notif.cliente_id:
                cliente = db.query(Cliente).filter(Cliente.id == notif.cliente_id).first()
                if cliente:
                    cliente_info = {
                        "id": cliente.id,
                        "nombre": f"{cliente.nombres} {cliente.apellidos}",
                        "cedula": cliente.cedula,
                        "telefono": cliente.telefono,
                        "email": cliente.email
                    }
            
            notif_data = {
                "id": notif.id,
                "tipo": notif.tipo.value if hasattr(notif.tipo, 'value') else str(notif.tipo),
                "categoria": notif.categoria.value if hasattr(notif.categoria, 'value') else str(notif.categoria),
                "asunto": notif.asunto,
                "mensaje": notif.mensaje,
                "estado": notif.estado.value if hasattr(notif.estado, 'value') else str(notif.estado),
                "fecha_creacion": notif.creado_en.isoformat() if notif.creado_en else None,
                "fecha_envio": notif.enviada_en.isoformat() if notif.enviada_en else None,
                "fecha_lectura": notif.leida_en.isoformat() if notif.leida_en else None,
                "intentos": notif.intentos,
                "cliente": cliente_info,
                "destinatario_email": notif.destinatario_email,
                "destinatario_telefono": notif.destinatario_telefono,
                "destinatario_nombre": notif.destinatario_nombre
            }
            notificaciones_data.append(notif_data)
        
        return notificaciones_data
        
    except Exception as e:
        logger.error(f"Error obteniendo notificaciones: {e}")
        return []

def obtener_ultima_notificacion(db) -> Dict[str, Any]:
    """Obtener la última notificación enviada"""
    try:
        # Buscar la notificación más reciente que haya sido enviada
        ultima_notif = db.query(Notificacion).filter(
            Notificacion.estado == "ENVIADA"
        ).order_by(desc(Notificacion.enviada_en)).first()
        
        if not ultima_notif:
            # Si no hay enviadas, buscar la más reciente en general
            ultima_notif = db.query(Notificacion).order_by(desc(Notificacion.creado_en)).first()
        
        if not ultima_notif:
            return {}
        
        # Obtener información del cliente
        cliente_info = None
        if ultima_notif.cliente_id:
            cliente = db.query(Cliente).filter(Cliente.id == ultima_notif.cliente_id).first()
            if cliente:
                cliente_info = {
                    "id": cliente.id,
                    "nombre": f"{cliente.nombres} {cliente.apellidos}",
                    "cedula": cliente.cedula,
                    "telefono": cliente.telefono,
                    "email": cliente.email
                }
        
        return {
            "id": ultima_notif.id,
            "tipo": ultima_notif.tipo.value if hasattr(ultima_notif.tipo, 'value') else str(ultima_notif.tipo),
            "categoria": ultima_notif.categoria.value if hasattr(ultima_notif.categoria, 'value') else str(ultima_notif.categoria),
            "asunto": ultima_notif.asunto,
            "mensaje": ultima_notif.mensaje,
            "estado": ultima_notif.estado.value if hasattr(ultima_notif.estado, 'value') else str(ultima_notif.estado),
            "fecha_creacion": ultima_notif.creado_en.isoformat() if ultima_notif.creado_en else None,
            "fecha_envio": ultima_notif.enviada_en.isoformat() if ultima_notif.enviada_en else None,
            "fecha_lectura": ultima_notif.leida_en.isoformat() if ultima_notif.leida_en else None,
            "intentos": ultima_notif.intentos,
            "cliente": cliente_info,
            "destinatario_email": ultima_notif.destinatario_email,
            "destinatario_telefono": ultima_notif.destinatario_telefono,
            "destinatario_nombre": ultima_notif.destinatario_nombre
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo última notificación: {e}")
        return {}

def analizar_patrones_mensajes(notificaciones: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analizar patrones en los mensajes"""
    if not notificaciones:
        return {}
    
    # Contar por tipo
    tipos = {}
    categorias = {}
    estados = {}
    
    for notif in notificaciones:
        tipo = notif.get('tipo', 'DESCONOCIDO')
        categoria = notif.get('categoria', 'DESCONOCIDA')
        estado = notif.get('estado', 'DESCONOCIDO')
        
        tipos[tipo] = tipos.get(tipo, 0) + 1
        categorias[categoria] = categorias.get(categoria, 0) + 1
        estados[estado] = estados.get(estado, 0) + 1
    
    return {
        "total_notificaciones": len(notificaciones),
        "por_tipo": tipos,
        "por_categoria": categorias,
        "por_estado": estados,
        "fecha_analisis": datetime.now().isoformat()
    }

def generar_reporte(notificaciones_hoy: List[Dict[str, Any]], ultima_notif: Dict[str, Any], patrones: Dict[str, Any]):
    """Generar reporte del análisis"""
    print("=" * 80)
    print("📊 ANÁLISIS DEL ÚLTIMO CHAT DE HOY")
    print("=" * 80)
    print(f"📅 Fecha de análisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if not notificaciones_hoy:
        print("❌ No se encontraron notificaciones para el día de hoy")
        return
    
    print(f"📈 RESUMEN GENERAL:")
    print(f"   • Total de notificaciones hoy: {patrones.get('total_notificaciones', 0)}")
    print(f"   • Tipos más comunes: {', '.join([f'{k}({v})' for k, v in patrones.get('por_tipo', {}).items()])}")
    print(f"   • Estados: {', '.join([f'{k}({v})' for k, v in patrones.get('por_estado', {}).items()])}")
    print()
    
    if ultima_notif:
        print("🔔 ÚLTIMA NOTIFICACIÓN ENVIADA:")
        print(f"   • ID: {ultima_notif.get('id')}")
        print(f"   • Tipo: {ultima_notif.get('tipo')}")
        print(f"   • Categoría: {ultima_notif.get('categoria')}")
        print(f"   • Asunto: {ultima_notif.get('asunto')}")
        print(f"   • Estado: {ultima_notif.get('estado')}")
        print(f"   • Fecha de envío: {ultima_notif.get('fecha_envio')}")
        
        if ultima_notif.get('cliente'):
            cliente = ultima_notif['cliente']
            print(f"   • Cliente: {cliente.get('nombre')} (Cédula: {cliente.get('cedula')})")
        
        print(f"   • Mensaje:")
        mensaje = ultima_notif.get('mensaje', '')
        if mensaje:
            # Mostrar solo los primeros 200 caracteres del mensaje
            mensaje_corto = mensaje[:200] + "..." if len(mensaje) > 200 else mensaje
            print(f"     {mensaje_corto}")
        print()
    
    print("📋 NOTIFICACIONES RECIENTES (últimas 5):")
    for i, notif in enumerate(notificaciones_hoy[:5], 1):
        print(f"   {i}. [{notif.get('tipo')}] {notif.get('asunto')} - {notif.get('estado')}")
        print(f"      Cliente: {notif.get('cliente', {}).get('nombre', 'N/A')}")
        print(f"      Fecha: {notif.get('fecha_creacion')}")
        print()

def main():
    """Función principal"""
    print("🔍 Iniciando análisis del último chat de hoy...")
    
    # Conectar a la base de datos
    db = conectar_base_datos()
    if not db:
        print("❌ No se pudo conectar a la base de datos")
        return
    
    try:
        # Obtener datos
        notificaciones_hoy = obtener_notificaciones_hoy(db)
        ultima_notif = obtener_ultima_notificacion(db)
        patrones = analizar_patrones_mensajes(notificaciones_hoy)
        
        # Generar reporte
        generar_reporte(notificaciones_hoy, ultima_notif, patrones)
        
    except Exception as e:
        logger.error(f"Error en el análisis: {e}")
        print(f"❌ Error durante el análisis: {e}")
    
    finally:
        db.close()

if __name__ == "__main__":
    main()









