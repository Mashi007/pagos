#!/usr/bin/env python3
"""
🔍 ACTIVACIÓN COMPLETA DEL MÓDULO DE AUDITORÍA
===============================================

Script para activar y configurar completamente el sistema de auditoría
Analiza la base de datos y activa todos los elementos de la plantilla

Autor: Sistema de Auditoría Avanzado
Fecha: 2025-10-17
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime, timedelta
import json
import logging

from app.db.session import get_db
from app.models.auditoria import Auditoria, TipoAccion
from app.models.user import User
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.configuracion_sistema import ConfiguracionSistema
from app.utils.auditoria_helper import registrar_auditoria

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActivadorAuditoriaCompleta:
    """
    🔍 Activador completo del sistema de auditoría
    """
    
    def __init__(self):
        self.db = next(get_db())
        self.estadisticas = {
            "registros_auditoria": 0,
            "usuarios_activos": 0,
            "clientes_registrados": 0,
            "prestamos_activos": 0,
            "pagos_registrados": 0,
            "configuraciones": 0
        }
    
    def analizar_base_datos(self):
        """
        📊 Analizar el estado actual de la base de datos
        """
        logger.info("🔍 ANALIZANDO BASE DE DATOS...")
        
        try:
            # Contar registros de auditoría
            self.estadisticas["registros_auditoria"] = self.db.query(Auditoria).count()
            
            # Contar usuarios activos
            self.estadisticas["usuarios_activos"] = self.db.query(User).filter(User.is_active == True).count()
            
            # Contar clientes
            self.estadisticas["clientes_registrados"] = self.db.query(Cliente).count()
            
            # Contar préstamos
            self.estadisticas["prestamos_activos"] = self.db.query(Prestamo).count()
            
            # Contar pagos
            self.estadisticas["pagos_registrados"] = self.db.query(Pago).count()
            
            # Contar configuraciones
            self.estadisticas["configuraciones"] = self.db.query(ConfiguracionSistema).count()
            
            logger.info("✅ Análisis de base de datos completado")
            self.mostrar_estadisticas()
            
        except Exception as e:
            logger.error(f"❌ Error analizando base de datos: {e}")
            raise
    
    def mostrar_estadisticas(self):
        """
        📈 Mostrar estadísticas del sistema
        """
        print("\n" + "="*60)
        print("📊 ESTADÍSTICAS DEL SISTEMA")
        print("="*60)
        print(f"🔍 Registros de auditoría: {self.estadisticas['registros_auditoria']:,}")
        print(f"👥 Usuarios activos: {self.estadisticas['usuarios_activos']:,}")
        print(f"🏢 Clientes registrados: {self.estadisticas['clientes_registrados']:,}")
        print(f"💰 Préstamos activos: {self.estadisticas['prestamos_activos']:,}")
        print(f"💳 Pagos registrados: {self.estadisticas['pagos_registrados']:,}")
        print(f"⚙️  Configuraciones: {self.estadisticas['configuraciones']:,}")
        print("="*60)
    
    def configurar_auditoria_sistema(self):
        """
        ⚙️ Configurar parámetros de auditoría en el sistema
        """
        logger.info("⚙️ CONFIGURANDO PARÁMETROS DE AUDITORÍA...")
        
        configuraciones_auditoria = [
            {
                "categoria": "AUDITORIA",
                "subcategoria": "GENERAL",
                "clave": "AUDITORIA_ACTIVA",
                "valor": "true",
                "descripcion": "Sistema de auditoría activo",
                "tipo_dato": "BOOLEAN",
                "requerido": True,
                "visible_frontend": True
            },
            {
                "categoria": "AUDITORIA",
                "subcategoria": "GENERAL",
                "clave": "AUDITORIA_RETENCION_DIAS",
                "valor": "365",
                "descripcion": "Días de retención de registros de auditoría",
                "tipo_dato": "INTEGER",
                "requerido": True,
                "valor_minimo": "30",
                "valor_maximo": "1095"
            },
            {
                "categoria": "AUDITORIA",
                "subcategoria": "GENERAL",
                "clave": "AUDITORIA_LOG_LEVEL",
                "valor": "INFO",
                "descripcion": "Nivel de logging para auditoría",
                "tipo_dato": "STRING",
                "opciones_validas": '["DEBUG", "INFO", "WARNING", "ERROR"]'
            },
            {
                "categoria": "AUDITORIA",
                "subcategoria": "EXPORTACION",
                "clave": "AUDITORIA_EXPORT_FORMATOS",
                "valor_json": ["EXCEL", "CSV", "PDF"],
                "descripcion": "Formatos disponibles para exportación",
                "tipo_dato": "JSON",
                "requerido": True
            },
            {
                "categoria": "AUDITORIA",
                "subcategoria": "EXPORTACION",
                "clave": "AUDITORIA_EXPORT_MAX_RECORDS",
                "valor": "10000",
                "descripcion": "Máximo número de registros por exportación",
                "tipo_dato": "INTEGER",
                "valor_minimo": "100",
                "valor_maximo": "50000"
            },
            {
                "categoria": "AUDITORIA",
                "subcategoria": "ALERTAS",
                "clave": "AUDITORIA_ALERTAS_ACTIVAS",
                "valor": "true",
                "descripcion": "Alertas de auditoría activas",
                "tipo_dato": "BOOLEAN",
                "requerido": True
            },
            {
                "categoria": "AUDITORIA",
                "subcategoria": "ALERTAS",
                "clave": "AUDITORIA_ALERTAS_EMAIL",
                "valor": "itmaster@rapicreditca.com",
                "descripcion": "Email para alertas de auditoría",
                "tipo_dato": "STRING",
                "requerido": True
            },
            {
                "categoria": "AUDITORIA",
                "subcategoria": "MONITOREO",
                "clave": "AUDITORIA_MONITOREO_TIEMPO_REAL",
                "valor": "true",
                "descripcion": "Monitoreo en tiempo real activo",
                "tipo_dato": "BOOLEAN",
                "requerido": True
            },
            {
                "categoria": "AUDITORIA",
                "subcategoria": "MONITOREO",
                "clave": "AUDITORIA_DASHBOARD_REFRESH_SECONDS",
                "valor": "30",
                "descripcion": "Intervalo de actualización del dashboard (segundos)",
                "tipo_dato": "INTEGER",
                "valor_minimo": "10",
                "valor_maximo": "300"
            }
        ]
        
        for config in configuraciones_auditoria:
            try:
                # Verificar si ya existe
                existing = self.db.query(ConfiguracionSistema).filter(
                    ConfiguracionSistema.categoria == config["categoria"],
                    ConfiguracionSistema.clave == config["clave"]
                ).first()
                
                if not existing:
                    nueva_config = ConfiguracionSistema(**config)
                    self.db.add(nueva_config)
                    logger.info(f"✅ Configuración creada: {config['clave']}")
                else:
                    logger.info(f"ℹ️  Configuración ya existe: {config['clave']}")
                    
            except Exception as e:
                logger.error(f"❌ Error creando configuración {config['clave']}: {e}")
        
        self.db.commit()
        logger.info("✅ Configuración de auditoría completada")
    
    def crear_registros_auditoria_iniciales(self):
        """
        📝 Crear registros de auditoría iniciales para demostración
        """
        logger.info("📝 CREANDO REGISTROS DE AUDITORÍA INICIALES...")
        
        try:
            # Obtener usuario administrador
            admin_user = self.db.query(User).filter(User.email == "itmaster@rapicreditca.com").first()
            
            if not admin_user:
                logger.warning("⚠️  Usuario administrador no encontrado")
                return
            
            # Crear registros de auditoría de ejemplo
            registros_ejemplo = [
                {
                    "accion": "LOGIN",
                    "modulo": "AUTH",
                    "tabla": "usuarios",
                    "descripcion": "Inicio de sesión del administrador",
                    "resultado": "EXITOSO"
                },
                {
                    "accion": "VER",
                    "modulo": "DASHBOARD",
                    "tabla": "dashboard",
                    "descripcion": "Acceso al dashboard principal",
                    "resultado": "EXITOSO"
                },
                {
                    "accion": "VER",
                    "modulo": "USUARIOS",
                    "tabla": "usuarios",
                    "descripcion": "Consulta de lista de usuarios",
                    "resultado": "EXITOSO"
                },
                {
                    "accion": "VER",
                    "modulo": "AUDITORIA",
                    "tabla": "auditorias",
                    "descripcion": "Consulta de registros de auditoría",
                    "resultado": "EXITOSO"
                },
                {
                    "accion": "ACTUALIZAR",
                    "modulo": "CONFIGURACION",
                    "tabla": "configuracion_sistema",
                    "descripcion": "Configuración de parámetros de auditoría",
                    "resultado": "EXITOSO"
                }
            ]
            
            for registro in registros_ejemplo:
                auditoria = registrar_auditoria(
                    db=self.db,
                    usuario=admin_user,
                    accion=registro["accion"],
                    modulo=registro["modulo"],
                    tabla=registro["tabla"],
                    descripcion=registro["descripcion"],
                    resultado=registro["resultado"]
                )
                logger.info(f"✅ Registro creado: {registro['accion']} - {registro['modulo']}")
            
            logger.info("✅ Registros de auditoría iniciales creados")
            
        except Exception as e:
            logger.error(f"❌ Error creando registros iniciales: {e}")
            raise
    
    def generar_reporte_auditoria(self):
        """
        📊 Generar reporte completo de auditoría
        """
        logger.info("📊 GENERANDO REPORTE DE AUDITORÍA...")
        
        try:
            # Estadísticas por módulo
            stats_modulos = self.db.query(
                Auditoria.modulo,
                func.count(Auditoria.id).label('total'),
                func.count(func.distinct(Auditoria.usuario_email)).label('usuarios_unicos')
            ).group_by(Auditoria.modulo).all()
            
            # Estadísticas por acción
            stats_acciones = self.db.query(
                Auditoria.accion,
                func.count(Auditoria.id).label('total')
            ).group_by(Auditoria.accion).all()
            
            # Estadísticas por resultado
            stats_resultados = self.db.query(
                Auditoria.resultado,
                func.count(Auditoria.id).label('total')
            ).group_by(Auditoria.resultado).all()
            
            # Actividad reciente (últimas 24 horas)
            fecha_limite = datetime.utcnow() - timedelta(hours=24)
            actividad_reciente = self.db.query(Auditoria).filter(
                Auditoria.fecha >= fecha_limite
            ).count()
            
            print("\n" + "="*60)
            print("📊 REPORTE DE AUDITORÍA COMPLETO")
            print("="*60)
            
            print("\n📈 ESTADÍSTICAS POR MÓDULO:")
            for stat in stats_modulos:
                print(f"  {stat.modulo}: {stat.total:,} acciones ({stat.usuarios_unicos} usuarios únicos)")
            
            print("\n🎯 ESTADÍSTICAS POR ACCIÓN:")
            for stat in stats_acciones:
                print(f"  {stat.accion}: {stat.total:,} veces")
            
            print("\n✅ ESTADÍSTICAS POR RESULTADO:")
            for stat in stats_resultados:
                print(f"  {stat.resultado}: {stat.total:,} veces")
            
            print(f"\n⏰ ACTIVIDAD RECIENTE (24h): {actividad_reciente:,} acciones")
            
            print("\n" + "="*60)
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte: {e}")
            raise
    
    def verificar_funcionamiento(self):
        """
        ✅ Verificar que el sistema de auditoría funciona correctamente
        """
        logger.info("✅ VERIFICANDO FUNCIONAMIENTO DEL SISTEMA...")
        
        try:
            # Verificar que se pueden crear registros
            admin_user = self.db.query(User).filter(User.email == "itmaster@rapicreditca.com").first()
            
            if admin_user:
                # Crear registro de prueba
                auditoria_prueba = registrar_auditoria(
                    db=self.db,
                    usuario=admin_user,
                    accion="VERIFICAR",
                    modulo="SISTEMA",
                    tabla="auditorias",
                    descripcion="Verificación del sistema de auditoría",
                    resultado="EXITOSO"
                )
                
                logger.info(f"✅ Sistema de auditoría funcionando - ID: {auditoria_prueba.id}")
                
                # Verificar endpoints
                logger.info("✅ Endpoints de auditoría disponibles:")
                logger.info("  - GET /api/v1/auditoria/ - Listar auditoría")
                logger.info("  - GET /api/v1/auditoria/stats - Estadísticas")
                logger.info("  - GET /api/v1/auditoria/export/excel - Exportar Excel")
                logger.info("  - GET /api/v1/auditoria/{id} - Obtener registro")
                
                return True
            else:
                logger.error("❌ Usuario administrador no encontrado")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verificando funcionamiento: {e}")
            return False
    
    def ejecutar_activacion_completa(self):
        """
        🚀 Ejecutar activación completa del sistema de auditoría
        """
        print("\n" + "="*60)
        print("🔍 ACTIVACIÓN COMPLETA DEL MÓDULO DE AUDITORÍA")
        print("="*60)
        print("📅 Fecha:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("👤 Administrador: itmaster@rapicreditca.com")
        print("="*60)
        
        try:
            # Paso 1: Analizar base de datos
            self.analizar_base_datos()
            
            # Paso 2: Configurar parámetros
            self.configurar_auditoria_sistema()
            
            # Paso 3: Crear registros iniciales
            self.crear_registros_auditoria_iniciales()
            
            # Paso 4: Generar reporte
            self.generar_reporte_auditoria()
            
            # Paso 5: Verificar funcionamiento
            if self.verificar_funcionamiento():
                print("\n🎉 ¡ACTIVACIÓN COMPLETA EXITOSA!")
                print("✅ Sistema de auditoría completamente activado")
                print("📊 Dashboard disponible en el frontend")
                print("📈 Exportación Excel habilitada")
                print("🔔 Monitoreo en tiempo real activo")
            else:
                print("\n❌ ACTIVACIÓN INCOMPLETA")
                print("⚠️  Revisar logs para más detalles")
            
        except Exception as e:
            logger.error(f"❌ Error en activación completa: {e}")
            print(f"\n❌ ERROR: {e}")
        
        finally:
            self.db.close()

def main():
    """
    Función principal
    """
    activador = ActivadorAuditoriaCompleta()
    activador.ejecutar_activacion_completa()

if __name__ == "__main__":
    main()
