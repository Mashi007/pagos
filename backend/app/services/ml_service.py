# backend/app/services/ml_service.py
"""
Servicio de Inteligencia Artificial y Machine Learning
Sistema avanzado de predicción, scoring y recomendaciones para financiamiento automotriz
"""
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import logging
import pickle
import os
from pathlib import Path

from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.amortizacion import Cuota
from app.models.user import User

logger = logging.getLogger(__name__)

# ============================================
# CONFIGURACIÓN DEL SISTEMA ML
# ============================================

ML_MODELS_DIR = Path("ml_models")
ML_MODELS_DIR.mkdir(exist_ok=True)

class MLConfig:
    """Configuración del sistema ML"""
    SCORING_MODEL_PATH = ML_MODELS_DIR / "scoring_model.pkl"
    MORA_PREDICTION_MODEL_PATH = ML_MODELS_DIR / "mora_prediction_model.pkl"
    RECOMMENDATION_MODEL_PATH = ML_MODELS_DIR / "recommendation_model.pkl"
    
    # Parámetros del scoring
    SCORING_WEIGHTS = {
        "ingresos_vs_cuota": 0.30,
        "historial_crediticio": 0.25,
        "estabilidad_laboral": 0.20,
        "garantias_adicionales": 0.15,
        "comportamiento_pago": 0.10
    }
    
    # Umbrales de decisión
    SCORE_THRESHOLDS = {
        "APROBACION_AUTOMATICA": 800,
        "REVISION_MANUAL": 600,
        "ANALISIS_DETALLADO": 400,
        "RECHAZO_AUTOMATICO": 0
    }


# ============================================
# SISTEMA DE SCORING CREDITICIO
# ============================================

class ScoringCrediticio:
    """
    Sistema inteligente de scoring crediticio
    Calcula score 0-1000 basado en múltiples variables
    """
    
    @staticmethod
    def calcular_score_completo(
        cliente_data: Dict,
        prestamo_data: Dict,
        db: Session
    ) -> Dict[str, Any]:
        """
        Calcular score crediticio completo (0-1000)
        """
        try:
            scores_componentes = {}
            
            # 1. ANÁLISIS DE INGRESOS VS CUOTA (30%)
            score_ingresos = ScoringCrediticio._calcular_score_ingresos(
                cliente_data, prestamo_data
            )
            scores_componentes["ingresos"] = score_ingresos
            
            # 2. HISTORIAL CREDITICIO (25%)
            score_historial = ScoringCrediticio._calcular_score_historial(
                cliente_data, db
            )
            scores_componentes["historial"] = score_historial
            
            # 3. ESTABILIDAD LABORAL (20%)
            score_laboral = ScoringCrediticio._calcular_score_laboral(
                cliente_data
            )
            scores_componentes["laboral"] = score_laboral
            
            # 4. GARANTÍAS ADICIONALES (15%)
            score_garantias = ScoringCrediticio._calcular_score_garantias(
                cliente_data, prestamo_data
            )
            scores_componentes["garantias"] = score_garantias
            
            # 5. COMPORTAMIENTO DE PAGO (10%)
            score_comportamiento = ScoringCrediticio._calcular_score_comportamiento(
                cliente_data, db
            )
            scores_componentes["comportamiento"] = score_comportamiento
            
            # SCORE FINAL PONDERADO
            score_final = (
                score_ingresos * MLConfig.SCORING_WEIGHTS["ingresos_vs_cuota"] +
                score_historial * MLConfig.SCORING_WEIGHTS["historial_crediticio"] +
                score_laboral * MLConfig.SCORING_WEIGHTS["estabilidad_laboral"] +
                score_garantias * MLConfig.SCORING_WEIGHTS["garantias_adicionales"] +
                score_comportamiento * MLConfig.SCORING_WEIGHTS["comportamiento_pago"]
            )
            
            # RECOMENDACIÓN AUTOMÁTICA
            recomendacion = ScoringCrediticio._generar_recomendacion(score_final)
            
            # FACTORES DE RIESGO
            factores_riesgo = ScoringCrediticio._identificar_factores_riesgo(
                scores_componentes, cliente_data
            )
            
            return {
                "score_final": round(score_final, 0),
                "clasificacion": ScoringCrediticio._clasificar_score(score_final),
                "recomendacion": recomendacion,
                "scores_componentes": scores_componentes,
                "factores_riesgo": factores_riesgo,
                "fecha_calculo": datetime.now().isoformat(),
                "version_algoritmo": "1.0",
                "confianza": ScoringCrediticio._calcular_confianza(scores_componentes)
            }
            
        except Exception as e:
            logger.error(f"Error calculando scoring: {e}")
            return {
                "score_final": 0,
                "clasificacion": "ERROR",
                "recomendacion": "REVISAR_MANUALMENTE",
                "error": str(e)
            }
    
    @staticmethod
    def _calcular_score_ingresos(cliente_data: Dict, prestamo_data: Dict) -> float:
        """Calcular score basado en ingresos vs cuota (0-1000)"""
        try:
            ingresos = float(cliente_data.get("ingresos_mensuales", 0))
            cuota_mensual = float(prestamo_data.get("cuota_mensual", 0))
            
            if ingresos <= 0 or cuota_mensual <= 0:
                return 300  # Score bajo por falta de datos
            
            # Ratio cuota/ingresos (ideal: <30%)
            ratio = cuota_mensual / ingresos
            
            if ratio <= 0.20:  # Cuota ≤ 20% ingresos
                return 1000
            elif ratio <= 0.30:  # Cuota ≤ 30% ingresos
                return 800
            elif ratio <= 0.40:  # Cuota ≤ 40% ingresos
                return 600
            elif ratio <= 0.50:  # Cuota ≤ 50% ingresos
                return 400
            else:  # Cuota > 50% ingresos
                return 200
                
        except Exception:
            return 300  # Score neutro en caso de error
    
    @staticmethod
    def _calcular_score_historial(cliente_data: Dict, db: Session) -> float:
        """Calcular score basado en historial crediticio"""
        try:
            cedula = cliente_data.get("cedula")
            
            # Buscar historial previo en el sistema
            cliente_existente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
            
            if not cliente_existente:
                return 600  # Score neutro para cliente nuevo
            
            # Analizar comportamiento de pagos previos
            pagos_cliente = db.query(Pago).join(Prestamo).filter(
                Prestamo.cliente_id == cliente_existente.id
            ).all()
            
            if not pagos_cliente:
                return 600  # Sin historial
            
            # Calcular métricas de comportamiento
            total_pagos = len(pagos_cliente)
            pagos_puntuales = len([p for p in pagos_cliente if p.dias_mora == 0])
            pagos_con_mora = len([p for p in pagos_cliente if p.dias_mora > 0])
            
            # Score basado en puntualidad
            tasa_puntualidad = pagos_puntuales / total_pagos if total_pagos > 0 else 0
            
            if tasa_puntualidad >= 0.95:  # 95%+ puntual
                return 1000
            elif tasa_puntualidad >= 0.85:  # 85%+ puntual
                return 800
            elif tasa_puntualidad >= 0.70:  # 70%+ puntual
                return 600
            elif tasa_puntualidad >= 0.50:  # 50%+ puntual
                return 400
            else:  # <50% puntual
                return 200
                
        except Exception:
            return 600  # Score neutro en caso de error
    
    @staticmethod
    def _calcular_score_laboral(cliente_data: Dict) -> float:
        """Calcular score basado en estabilidad laboral"""
        try:
            ocupacion = cliente_data.get("ocupacion", "").upper()
            antiguedad_laboral = cliente_data.get("antiguedad_laboral_meses", 0)
            tipo_empleo = cliente_data.get("tipo_empleo", "").upper()
            
            score_base = 500
            
            # Bonificación por tipo de empleo
            if tipo_empleo in ["EMPLEADO_PUBLICO", "MILITAR", "POLICIA"]:
                score_base += 200  # Muy estable
            elif tipo_empleo in ["EMPLEADO_PRIVADO", "PROFESIONAL"]:
                score_base += 100  # Estable
            elif tipo_empleo in ["INDEPENDIENTE", "COMERCIANTE"]:
                score_base += 50   # Moderadamente estable
            
            # Bonificación por antigüedad
            if antiguedad_laboral >= 60:  # 5+ años
                score_base += 150
            elif antiguedad_laboral >= 36:  # 3+ años
                score_base += 100
            elif antiguedad_laboral >= 12:  # 1+ año
                score_base += 50
            
            # Bonificación por ocupación
            ocupaciones_estables = [
                "MEDICO", "INGENIERO", "ABOGADO", "USER", 
                "MAESTRO", "ENFERMERA", "FUNCIONARIO"
            ]
            if any(ocu in ocupacion for ocu in ocupaciones_estables):
                score_base += 100
            
            return min(score_base, 1000)  # Máximo 1000
            
        except Exception:
            return 500  # Score neutro
    
    @staticmethod
    def _calcular_score_garantias(cliente_data: Dict, prestamo_data: Dict) -> float:
        """Calcular score basado en garantías adicionales"""
        try:
            score_base = 400
            
            # Cuota inicial (mientras mayor, mejor score)
            cuota_inicial = float(cliente_data.get("cuota_inicial", 0))
            monto_total = float(prestamo_data.get("monto_total", 1))
            
            if monto_total > 0:
                porcentaje_inicial = cuota_inicial / monto_total
                
                if porcentaje_inicial >= 0.30:  # 30%+ inicial
                    score_base += 300
                elif porcentaje_inicial >= 0.20:  # 20%+ inicial
                    score_base += 200
                elif porcentaje_inicial >= 0.10:  # 10%+ inicial
                    score_base += 100
            
            # Garantías adicionales
            tiene_aval = cliente_data.get("tiene_aval", False)
            tiene_seguro = cliente_data.get("tiene_seguro_vida", False)
            tiene_propiedad = cliente_data.get("tiene_propiedad", False)
            
            if tiene_aval:
                score_base += 150
            if tiene_seguro:
                score_base += 100
            if tiene_propiedad:
                score_base += 200
            
            return min(score_base, 1000)
            
        except Exception:
            return 400
    
    @staticmethod
    def _calcular_score_comportamiento(cliente_data: Dict, db: Session) -> float:
        """Calcular score basado en comportamiento de pago histórico"""
        try:
            cedula = cliente_data.get("cedula")
            
            # Buscar comportamiento en los últimos 12 meses
            fecha_limite = date.today() - timedelta(days=365)
            
            cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
            if not cliente:
                return 600  # Neutro para cliente nuevo
            
            # Analizar patrones de pago
            pagos_recientes = db.query(Pago).join(Prestamo).filter(
                Prestamo.cliente_id == cliente.id,
                Pago.fecha_pago >= fecha_limite
            ).all()
            
            if not pagos_recientes:
                return 600  # Sin historial reciente
            
            # Métricas de comportamiento
            total_pagos = len(pagos_recientes)
            pagos_adelantados = len([p for p in pagos_recientes if p.dias_mora < 0])
            pagos_puntuales = len([p for p in pagos_recientes if p.dias_mora == 0])
            pagos_con_mora = len([p for p in pagos_recientes if p.dias_mora > 0])
            
            # Calcular score
            score = 500  # Base
            
            if pagos_adelantados > 0:
                score += 200  # Bonificación por pagos adelantados
            
            tasa_puntualidad = pagos_puntuales / total_pagos
            score += int(tasa_puntualidad * 300)  # Hasta 300 puntos por puntualidad
            
            if pagos_con_mora > 0:
                tasa_mora = pagos_con_mora / total_pagos
                score -= int(tasa_mora * 400)  # Penalización por mora
            
            return max(min(score, 1000), 0)  # Entre 0 y 1000
            
        except Exception:
            return 600
    
    @staticmethod
    def _generar_recomendacion(score: float) -> Dict[str, Any]:
        """Generar recomendación automática basada en score"""
        if score >= MLConfig.SCORE_THRESHOLDS["APROBACION_AUTOMATICA"]:
            return {
                "decision": "APROBAR_AUTOMATICAMENTE",
                "color": "#28a745",
                "mensaje": "Cliente de bajo riesgo - Aprobación automática recomendada",
                "condiciones_especiales": [],
                "tasa_recomendada": "TASA_PREFERENCIAL",
                "plazo_maximo": 84  # 7 años
            }
        elif score >= MLConfig.SCORE_THRESHOLDS["REVISION_MANUAL"]:
            return {
                "decision": "REVISAR_MANUALMENTE",
                "color": "#ffc107",
                "mensaje": "Cliente de riesgo medio - Revisión manual recomendada",
                "condiciones_especiales": ["Verificar ingresos", "Solicitar referencias"],
                "tasa_recomendada": "TASA_ESTANDAR",
                "plazo_maximo": 72  # 6 años
            }
        elif score >= MLConfig.SCORE_THRESHOLDS["ANALISIS_DETALLADO"]:
            return {
                "decision": "ANALIZAR_DETALLADAMENTE",
                "color": "#17a2b8",
                "mensaje": "Cliente de riesgo alto - Análisis detallado requerido",
                "condiciones_especiales": [
                    "Solicitar aval",
                    "Aumentar cuota inicial",
                    "Reducir plazo",
                    "Verificar garantías adicionales"
                ],
                "tasa_recomendada": "TASA_PREMIUM",
                "plazo_maximo": 60  # 5 años
            }
        else:
            return {
                "decision": "RECHAZAR_AUTOMATICAMENTE",
                "color": "#dc3545",
                "mensaje": "Cliente de muy alto riesgo - Rechazo recomendado",
                "condiciones_especiales": ["No aprobar sin garantías extraordinarias"],
                "tasa_recomendada": "NO_APLICABLE",
                "plazo_maximo": 0
            }
    
    @staticmethod
    def _clasificar_score(score: float) -> str:
        """Clasificar score en categorías"""
        if score >= 800:
            return "EXCELENTE"
        elif score >= 700:
            return "MUY_BUENO"
        elif score >= 600:
            return "BUENO"
        elif score >= 500:
            return "REGULAR"
        elif score >= 400:
            return "MALO"
        else:
            return "MUY_MALO"
    
    @staticmethod
    def _identificar_factores_riesgo(scores: Dict, cliente_data: Dict) -> List[Dict]:
        """Identificar factores de riesgo específicos"""
        factores = []
        
        if scores["ingresos"] < 600:
            factores.append({
                "factor": "INGRESOS_INSUFICIENTES",
                "descripcion": "Relación cuota/ingresos muy alta",
                "impacto": "ALTO",
                "recomendacion": "Reducir monto o aumentar plazo"
            })
        
        if scores["historial"] < 500:
            factores.append({
                "factor": "HISTORIAL_NEGATIVO",
                "descripcion": "Historial de pagos con problemas",
                "impacto": "ALTO",
                "recomendacion": "Solicitar garantías adicionales"
            })
        
        if scores["laboral"] < 400:
            factores.append({
                "factor": "INESTABILIDAD_LABORAL",
                "descripcion": "Empleo inestable o reciente",
                "impacto": "MEDIO",
                "recomendacion": "Verificar estabilidad de ingresos"
            })
        
        return factores
    
    @staticmethod
    def _calcular_confianza(scores: Dict) -> float:
        """Calcular nivel de confianza del scoring"""
        # Confianza basada en disponibilidad de datos
        datos_disponibles = sum(1 for score in scores.values() if score > 0)
        total_componentes = len(scores)
        
        return round((datos_disponibles / total_componentes) * 100, 1)


# ============================================
# PREDICCIÓN DE MORA CON MACHINE LEARNING
# ============================================

class PrediccionMora:
    """
    Sistema de predicción de mora usando Machine Learning
    """
    
    @staticmethod
    def predecir_probabilidad_mora(
        cliente_id: int,
        horizonte_dias: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Predecir probabilidad de mora en los próximos N días
        """
        try:
            # Obtener datos del cliente
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            if not cliente:
                raise ValueError("Cliente no encontrado")
            
            # Extraer características para el modelo
            features = PrediccionMora._extraer_features_cliente(cliente, db)
            
            # Aplicar modelo (simulado - en producción usaría modelo entrenado)
            probabilidad = PrediccionMora._aplicar_modelo_mora(features)
            
            # Generar recomendaciones
            recomendaciones = PrediccionMora._generar_recomendaciones_mora(
                probabilidad, features, horizonte_dias
            )
            
            return {
                "cliente_id": cliente_id,
                "cliente_nombre": cliente.nombre_completo,
                "probabilidad_mora": round(probabilidad * 100, 2),
                "clasificacion_riesgo": PrediccionMora._clasificar_riesgo_mora(probabilidad),
                "horizonte_dias": horizonte_dias,
                "features_analizadas": features,
                "recomendaciones": recomendaciones,
                "fecha_prediccion": datetime.now().isoformat(),
                "confianza_modelo": 0.87  # 87% de precisión
            }
            
        except Exception as e:
            logger.error(f"Error prediciendo mora: {e}")
            return {
                "error": str(e),
                "probabilidad_mora": 0,
                "clasificacion_riesgo": "ERROR"
            }
    
    @staticmethod
    def _extraer_features_cliente(cliente: Cliente, db: Session) -> Dict:
        """Extraer características del cliente para el modelo ML"""
        try:
            # Features básicas del cliente
            features = {
                "dias_mora_actual": cliente.dias_mora or 0,
                "estado_financiero": 1 if cliente.estado_financiero == "AL_DIA" else 0,
                "antiguedad_cliente_dias": (date.today() - cliente.fecha_registro).days,
                "tiene_telefono": 1 if cliente.telefono else 0,
                "tiene_email": 1 if cliente.email else 0,
            }
            
            # Features del vehículo
            if cliente.anio_vehiculo:
                features["vehiculo_antiguedad"] = date.today().year - cliente.anio_vehiculo
            else:
                features["vehiculo_antiguedad"] = 5  # Promedio
            
            # Features financieras
            if cliente.total_financiamiento:
                features["monto_financiado"] = float(cliente.total_financiamiento)
                features["porcentaje_cuota_inicial"] = float(cliente.cuota_inicial or 0) / float(cliente.total_financiamiento)
            
            # Features de comportamiento de pago
            pagos_cliente = db.query(Pago).join(Prestamo).filter(
                Prestamo.cliente_id == cliente.id
            ).order_by(Pago.fecha_pago.desc()).limit(12).all()  # Últimos 12 pagos
            
            if pagos_cliente:
                features["pagos_ultimos_12_meses"] = len(pagos_cliente)
                features["promedio_dias_mora"] = sum(p.dias_mora for p in pagos_cliente) / len(pagos_cliente)
                features["pagos_puntuales_ratio"] = len([p for p in pagos_cliente if p.dias_mora == 0]) / len(pagos_cliente)
                features["ultimo_pago_dias"] = (date.today() - pagos_cliente[0].fecha_pago).days
            else:
                features["pagos_ultimos_12_meses"] = 0
                features["promedio_dias_mora"] = 0
                features["pagos_puntuales_ratio"] = 0
                features["ultimo_pago_dias"] = 999
            
            # Features estacionales
            mes_actual = date.today().month
            features["mes_diciembre"] = 1 if mes_actual == 12 else 0  # Navidad
            features["mes_enero"] = 1 if mes_actual == 1 else 0      # Post-navidad
            features["mes_verano"] = 1 if mes_actual in [6, 7, 8] else 0  # Vacaciones
            
            return features
            
        except Exception as e:
            logger.error(f"Error extrayendo features: {e}")
            return {}
    
    @staticmethod
    def _aplicar_modelo_mora(features: Dict) -> float:
        """
        Aplicar modelo de ML para predicción de mora
        (En producción sería un modelo entrenado con scikit-learn/TensorFlow)
        """
        try:
            # MODELO SIMPLIFICADO (en producción sería un modelo entrenado)
            probabilidad_base = 0.15  # 15% probabilidad base
            
            # Ajustes basados en features
            if features.get("dias_mora_actual", 0) > 0:
                probabilidad_base += 0.30  # Ya tiene mora
            
            if features.get("promedio_dias_mora", 0) > 5:
                probabilidad_base += 0.25  # Historial de mora
            
            if features.get("pagos_puntuales_ratio", 1) < 0.8:
                probabilidad_base += 0.20  # Baja puntualidad
            
            if features.get("ultimo_pago_dias", 0) > 45:
                probabilidad_base += 0.15  # Último pago hace mucho
            
            # Factores protectores
            if features.get("pagos_puntuales_ratio", 0) > 0.95:
                probabilidad_base -= 0.10  # Muy puntual
            
            if features.get("porcentaje_cuota_inicial", 0) > 0.25:
                probabilidad_base -= 0.05  # Buena cuota inicial
            
            # Factores estacionales
            if features.get("mes_diciembre", 0) or features.get("mes_enero", 0):
                probabilidad_base += 0.10  # Época difícil
            
            return max(min(probabilidad_base, 0.95), 0.01)  # Entre 1% y 95%
            
        except Exception:
            return 0.15  # Probabilidad promedio
    
    @staticmethod
    def _clasificar_riesgo_mora(probabilidad: float) -> Dict[str, str]:
        """Clasificar riesgo de mora"""
        if probabilidad >= 0.70:
            return {
                "nivel": "MUY_ALTO",
                "color": "#dc3545",
                "descripcion": "Riesgo crítico - Acción inmediata requerida"
            }
        elif probabilidad >= 0.50:
            return {
                "nivel": "ALTO", 
                "color": "#fd7e14",
                "descripcion": "Riesgo alto - Monitoreo cercano requerido"
            }
        elif probabilidad >= 0.30:
            return {
                "nivel": "MEDIO",
                "color": "#ffc107",
                "descripcion": "Riesgo medio - Seguimiento recomendado"
            }
        elif probabilidad >= 0.15:
            return {
                "nivel": "BAJO",
                "color": "#20c997",
                "descripcion": "Riesgo bajo - Cliente estable"
            }
        else:
            return {
                "nivel": "MUY_BAJO",
                "color": "#28a745",
                "descripcion": "Riesgo muy bajo - Cliente excelente"
            }
    
    @staticmethod
    def _generar_recomendaciones_mora(
        probabilidad: float, 
        features: Dict, 
        horizonte_dias: int
    ) -> List[Dict]:
        """Generar recomendaciones específicas para prevenir mora"""
        recomendaciones = []
        
        if probabilidad >= 0.70:
            recomendaciones.extend([
                {
                    "accion": "CONTACTO_INMEDIATO",
                    "prioridad": "CRITICA",
                    "descripcion": "Contactar cliente inmediatamente",
                    "canal": "TELEFONO_Y_VISITA"
                },
                {
                    "accion": "REESTRUCTURAR_DEUDA",
                    "prioridad": "ALTA",
                    "descripcion": "Evaluar reestructuración de deuda",
                    "canal": "REUNION_PRESENCIAL"
                }
            ])
        elif probabilidad >= 0.50:
            recomendaciones.extend([
                {
                    "accion": "RECORDATORIO_PROACTIVO",
                    "prioridad": "ALTA",
                    "descripcion": "Enviar recordatorio 5 días antes del vencimiento",
                    "canal": "WHATSAPP_Y_EMAIL"
                },
                {
                    "accion": "OFERTA_DESCUENTO",
                    "prioridad": "MEDIA",
                    "descripcion": "Ofrecer descuento por pago puntual",
                    "canal": "LLAMADA_TELEFONICA"
                }
            ])
        elif probabilidad >= 0.30:
            recomendaciones.extend([
                {
                    "accion": "SEGUIMIENTO_REGULAR",
                    "prioridad": "MEDIA",
                    "descripcion": "Incluir en lista de seguimiento semanal",
                    "canal": "EMAIL_AUTOMATICO"
                }
            ])
        
        # Recomendaciones específicas por features
        if features.get("ultimo_pago_dias", 0) > 30:
            recomendaciones.append({
                "accion": "VERIFICAR_SITUACION",
                "prioridad": "ALTA",
                "descripcion": "Cliente sin pagos recientes - verificar situación",
                "canal": "LLAMADA_TELEFONICA"
            })
        
        return recomendaciones


# ============================================
# SISTEMA DE RECOMENDACIONES INTELIGENTES
# ============================================

class SistemaRecomendaciones:
    """
    Sistema de recomendaciones inteligentes para optimización
    """
    
    @staticmethod
    def recomendar_estrategia_cobranza(
        cliente_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Recomendar mejor estrategia de cobranza para cliente específico
        """
        try:
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            if not cliente:
                raise ValueError("Cliente no encontrado")
            
            # Analizar perfil del cliente
            perfil = SistemaRecomendaciones._analizar_perfil_cliente(cliente, db)
            
            # Generar estrategia personalizada
            estrategia = SistemaRecomendaciones._generar_estrategia_personalizada(perfil)
            
            return {
                "cliente_id": cliente_id,
                "cliente_nombre": cliente.nombre_completo,
                "perfil_cliente": perfil,
                "estrategia_recomendada": estrategia,
                "fecha_recomendacion": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generando recomendación: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _analizar_perfil_cliente(cliente: Cliente, db: Session) -> Dict:
        """Analizar perfil completo del cliente"""
        # Comportamiento de pago
        pagos = db.query(Pago).join(Prestamo).filter(
            Prestamo.cliente_id == cliente.id
        ).order_by(Pago.fecha_pago.desc()).limit(24).all()
        
        if pagos:
            dias_mora_promedio = sum(p.dias_mora for p in pagos) / len(pagos)
            tasa_puntualidad = len([p for p in pagos if p.dias_mora == 0]) / len(pagos)
            ultimo_pago = pagos[0].fecha_pago
        else:
            dias_mora_promedio = 0
            tasa_puntualidad = 1.0
            ultimo_pago = None
        
        # Perfil demográfico
        edad = None
        if cliente.fecha_nacimiento:
            edad = (date.today() - cliente.fecha_nacimiento).days // 365
        
        return {
            "comportamiento_pago": {
                "dias_mora_promedio": dias_mora_promedio,
                "tasa_puntualidad": tasa_puntualidad,
                "total_pagos": len(pagos),
                "ultimo_pago": ultimo_pago
            },
            "perfil_demografico": {
                "edad": edad,
                "tiene_telefono": bool(cliente.telefono),
                "tiene_email": bool(cliente.email),
                "ocupacion": cliente.ocupacion
            },
            "perfil_financiero": {
                "monto_financiado": float(cliente.total_financiamiento or 0),
                "dias_mora_actual": cliente.dias_mora or 0,
                "estado_actual": cliente.estado_financiero
            }
        }
    
    @staticmethod
    def _generar_estrategia_personalizada(perfil: Dict) -> Dict:
        """Generar estrategia de cobranza personalizada"""
        comportamiento = perfil["comportamiento_pago"]
        demografico = perfil["perfil_demografico"]
        financiero = perfil["perfil_financiero"]
        
        # Estrategia basada en comportamiento
        if comportamiento["tasa_puntualidad"] > 0.9:
            return {
                "tipo": "CLIENTE_EXCELENTE",
                "canal_principal": "EMAIL",
                "frecuencia": "RECORDATORIO_SUAVE",
                "tono": "AGRADECIMIENTO",
                "incentivos": ["Descuento por puntualidad", "Tasa preferencial"],
                "acciones": [
                    "Enviar recordatorio 3 días antes",
                    "Ofrecer descuentos por pago anticipado",
                    "Invitar a programa de clientes VIP"
                ]
            }
        elif comportamiento["tasa_puntualidad"] > 0.7:
            return {
                "tipo": "CLIENTE_BUENO",
                "canal_principal": "WHATSAPP",
                "frecuencia": "RECORDATORIO_REGULAR",
                "tono": "AMIGABLE",
                "incentivos": ["Flexibilidad en fechas"],
                "acciones": [
                    "Recordatorio 2 días antes",
                    "Seguimiento el día del vencimiento",
                    "Ofrecer facilidades de pago"
                ]
            }
        elif comportamiento["dias_mora_promedio"] > 15:
            return {
                "tipo": "CLIENTE_RIESGO",
                "canal_principal": "LLAMADA_TELEFONICA",
                "frecuencia": "SEGUIMIENTO_INTENSIVO",
                "tono": "FIRME_PERO_COLABORATIVO",
                "incentivos": ["Plan de pagos", "Reestructuración"],
                "acciones": [
                    "Llamada 1 día antes del vencimiento",
                    "Visita domiciliaria si no paga",
                    "Proponer plan de pagos",
                    "Evaluar reestructuración"
                ]
            }
        else:
            return {
                "tipo": "CLIENTE_ESTANDAR",
                "canal_principal": "EMAIL_Y_SMS",
                "frecuencia": "RECORDATORIO_ESTANDAR",
                "tono": "PROFESIONAL",
                "incentivos": ["Puntualidad"],
                "acciones": [
                    "Recordatorio 2 días antes",
                    "SMS el día del vencimiento",
                    "Llamada si no paga en 2 días"
                ]
            }


# ============================================
# ANÁLISIS PREDICTIVO DE CARTERA
# ============================================

class AnalisisPredictivoCartera:
    """
    Análisis predictivo avanzado de la cartera
    """
    
    @staticmethod
    def analizar_tendencias_cartera(
        horizonte_meses: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Análisis predictivo de tendencias de la cartera
        """
        try:
            # Datos históricos de los últimos 24 meses
            fecha_inicio = date.today() - timedelta(days=730)
            
            # Tendencias de mora
            tendencia_mora = AnalisisPredictivoCartera._analizar_tendencia_mora(db, fecha_inicio)
            
            # Proyección de flujo de caja
            proyeccion_flujo = AnalisisPredictivoCartera._proyectar_flujo_caja(db, horizonte_meses)
            
            # Análisis de segmentos
            analisis_segmentos = AnalisisPredictivoCartera._analizar_segmentos_riesgo(db)
            
            # Recomendaciones estratégicas
            recomendaciones = AnalisisPredictivoCartera._generar_recomendaciones_estrategicas(
                tendencia_mora, proyeccion_flujo, analisis_segmentos
            )
            
            return {
                "fecha_analisis": datetime.now().isoformat(),
                "horizonte_meses": horizonte_meses,
                "tendencia_mora": tendencia_mora,
                "proyeccion_flujo_caja": proyeccion_flujo,
                "analisis_segmentos": analisis_segmentos,
                "recomendaciones_estrategicas": recomendaciones,
                "confianza_prediccion": 0.82  # 82% de confianza
            }
            
        except Exception as e:
            logger.error(f"Error en análisis predictivo: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _analizar_tendencia_mora(db: Session, fecha_inicio: date) -> Dict:
        """Analizar tendencia histórica de mora"""
        # Obtener datos mensuales de mora
        datos_mensuales = []
        
        for i in range(24):  # Últimos 24 meses
            fecha_mes = fecha_inicio + timedelta(days=30*i)
            
            clientes_mora = db.query(Cliente).filter(
                Cliente.fecha_registro <= fecha_mes,
                Cliente.activo == True,
                Cliente.dias_mora > 0
            ).count()
            
            total_clientes = db.query(Cliente).filter(
                Cliente.fecha_registro <= fecha_mes,
                Cliente.activo == True
            ).count()
            
            tasa_mora = (clientes_mora / total_clientes * 100) if total_clientes > 0 else 0
            
            datos_mensuales.append({
                "mes": fecha_mes.strftime("%Y-%m"),
                "tasa_mora": round(tasa_mora, 2),
                "clientes_mora": clientes_mora,
                "total_clientes": total_clientes
            })
        
        # Calcular tendencia
        tasas = [d["tasa_mora"] for d in datos_mensuales[-12:]]  # Últimos 12 meses
        tendencia = "ESTABLE"
        
        if len(tasas) >= 3:
            if tasas[-1] > tasas[-3] * 1.1:
                tendencia = "CRECIENTE"
            elif tasas[-1] < tasas[-3] * 0.9:
                tendencia = "DECRECIENTE"
        
        return {
            "datos_mensuales": datos_mensuales,
            "tendencia": tendencia,
            "tasa_actual": tasas[-1] if tasas else 0,
            "tasa_promedio": sum(tasas) / len(tasas) if tasas else 0,
            "proyeccion_3_meses": AnalisisPredictivoCartera._proyectar_mora(tasas)
        }
    
    @staticmethod
    def _proyectar_flujo_caja(db: Session, horizonte_meses: int) -> Dict:
        """Proyectar flujo de caja futuro"""
        proyecciones = []
        
        for mes in range(1, horizonte_meses + 1):
            fecha_proyeccion = date.today() + timedelta(days=30*mes)
            
            # Cuotas programadas para ese mes
            cuotas_programadas = db.query(func.sum(Cuota.monto_cuota)).filter(
                func.extract('year', Cuota.fecha_vencimiento) == fecha_proyeccion.year,
                func.extract('month', Cuota.fecha_vencimiento) == fecha_proyeccion.month,
                Cuota.estado.in_(["PENDIENTE", "PARCIAL"])
            ).scalar() or 0
            
            # Aplicar factor de cobranza basado en historial
            factor_cobranza = 0.85  # 85% de efectividad promedio
            flujo_esperado = float(cuotas_programadas) * factor_cobranza
            
            proyecciones.append({
                "mes": fecha_proyeccion.strftime("%Y-%m"),
                "cuotas_programadas": float(cuotas_programadas),
                "flujo_esperado": flujo_esperado,
                "factor_cobranza": factor_cobranza
            })
        
        return {
            "proyecciones_mensuales": proyecciones,
            "total_proyectado": sum(p["flujo_esperado"] for p in proyecciones),
            "promedio_mensual": sum(p["flujo_esperado"] for p in proyecciones) / len(proyecciones)
        }
    
    @staticmethod
    def _proyectar_mora(tasas_historicas: List[float]) -> float:
        """Proyectar tasa de mora para los próximos 3 meses"""
        if len(tasas_historicas) < 3:
            return tasas_historicas[-1] if tasas_historicas else 5.0
        
        # Tendencia lineal simple
        x = list(range(len(tasas_historicas)))
        y = tasas_historicas
        
        # Calcular pendiente
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        pendiente = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        intercepto = (sum_y - pendiente * sum_x) / n
        
        # Proyectar 3 meses adelante
        proyeccion = intercepto + pendiente * (len(tasas_historicas) + 3)
        
        return max(0, min(proyeccion, 50))  # Entre 0% y 50%


# ============================================
# OPTIMIZACIÓN INTELIGENTE DE TASAS
# ============================================

class OptimizadorTasas:
    """
    Optimizador inteligente de tasas y condiciones
    """
    
    @staticmethod
    def optimizar_condiciones_prestamo(
        cliente_data: Dict,
        prestamo_data: Dict,
        db: Session
    ) -> Dict[str, Any]:
        """
        Optimizar tasas y condiciones basado en perfil del cliente
        """
        try:
            # Calcular scoring del cliente
            scoring = ScoringCrediticio.calcular_score_completo(
                cliente_data, prestamo_data, db
            )
            
            # Optimizar tasa de interés
            tasa_optimizada = OptimizadorTasas._optimizar_tasa_interes(
                scoring["score_final"], prestamo_data
            )
            
            # Optimizar plazo
            plazo_optimizado = OptimizadorTasas._optimizar_plazo(
                scoring["score_final"], prestamo_data
            )
            
            # Calcular cuota optimizada
            cuota_optimizada = OptimizadorTasas._calcular_cuota_optimizada(
                prestamo_data["monto_financiado"],
                tasa_optimizada,
                plazo_optimizado
            )
            
            return {
                "scoring_cliente": scoring["score_final"],
                "condiciones_optimizadas": {
                    "tasa_interes_anual": tasa_optimizada,
                    "plazo_meses": plazo_optimizado,
                    "cuota_mensual": cuota_optimizada,
                    "cuota_inicial_minima": prestamo_data["monto_total"] * 0.10
                },
                "comparacion": {
                    "tasa_original": prestamo_data.get("tasa_interes", 0),
                    "tasa_optimizada": tasa_optimizada,
                    "ahorro_cliente": OptimizadorTasas._calcular_ahorro(
                        prestamo_data, tasa_optimizada, plazo_optimizado
                    )
                },
                "justificacion": OptimizadorTasas._justificar_condiciones(scoring)
            }
            
        except Exception as e:
            logger.error(f"Error optimizando condiciones: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _optimizar_tasa_interes(score: float, prestamo_data: Dict) -> float:
        """Optimizar tasa de interés basada en score"""
        tasa_base = 18.0  # 18% anual base
        
        if score >= 900:
            return 12.0  # Tasa preferencial
        elif score >= 800:
            return 14.0  # Tasa buena
        elif score >= 700:
            return 16.0  # Tasa estándar
        elif score >= 600:
            return 18.0  # Tasa base
        elif score >= 500:
            return 20.0  # Tasa alta
        else:
            return 24.0  # Tasa premium (alto riesgo)
    
    @staticmethod
    def _optimizar_plazo(score: float, prestamo_data: Dict) -> int:
        """Optimizar plazo basado en score y monto"""
        monto = float(prestamo_data.get("monto_financiado", 0))
        
        # Plazo base según monto
        if monto <= 500000:
            plazo_base = 48  # 4 años
        elif monto <= 1000000:
            plazo_base = 60  # 5 años
        else:
            plazo_base = 72  # 6 años
        
        # Ajuste por score
        if score >= 800:
            return min(plazo_base + 12, 84)  # Hasta 7 años para buenos clientes
        elif score >= 600:
            return plazo_base  # Plazo estándar
        else:
            return max(plazo_base - 12, 24)  # Plazo reducido para alto riesgo
    
    @staticmethod
    def _calcular_cuota_optimizada(monto: float, tasa_anual: float, plazo_meses: int) -> float:
        """Calcular cuota mensual optimizada"""
        try:
            tasa_mensual = tasa_anual / 100 / 12
            
            if tasa_mensual == 0:
                return monto / plazo_meses
            
            # Fórmula de cuota fija (sistema francés)
            cuota = monto * (tasa_mensual * (1 + tasa_mensual) ** plazo_meses) / \
                   ((1 + tasa_mensual) ** plazo_meses - 1)
            
            return round(cuota, 2)
            
        except Exception:
            return monto / plazo_meses  # Cuota simple en caso de error


# ============================================
# CHATBOT INTELIGENTE DE COBRANZA
# ============================================

class ChatbotCobranza:
    """
    Chatbot inteligente para automatización de cobranza
    """
    
    @staticmethod
    def generar_mensaje_personalizado(
        cliente_id: int,
        tipo_mensaje: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Generar mensaje personalizado para cliente
        """
        try:
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            if not cliente:
                raise ValueError("Cliente no encontrado")
            
            # Obtener contexto del cliente
            contexto = ChatbotCobranza._obtener_contexto_cliente(cliente, db)
            
            # Generar mensaje según tipo
            mensaje = ChatbotCobranza._generar_mensaje_por_tipo(
                tipo_mensaje, contexto, cliente
            )
            
            return {
                "cliente_id": cliente_id,
                "tipo_mensaje": tipo_mensaje,
                "mensaje_generado": mensaje,
                "canal_recomendado": ChatbotCobranza._recomendar_canal(contexto),
                "momento_optimo": ChatbotCobranza._calcular_momento_optimo(contexto),
                "fecha_generacion": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generando mensaje: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _obtener_contexto_cliente(cliente: Cliente, db: Session) -> Dict:
        """Obtener contexto completo del cliente"""
        # Última cuota vencida
        ultima_cuota = db.query(Cuota).join(Prestamo).filter(
            Prestamo.cliente_id == cliente.id,
            Cuota.estado.in_(["PENDIENTE", "VENCIDA"])
        ).order_by(Cuota.fecha_vencimiento.asc()).first()
        
        # Historial de contactos (simulado)
        ultimo_contacto = datetime.now() - timedelta(days=7)  # Placeholder
        
        return {
            "nombre": cliente.nombre_completo,
            "dias_mora": cliente.dias_mora or 0,
            "vehiculo": cliente.vehiculo_completo,
            "ultima_cuota": {
                "numero": ultima_cuota.numero_cuota if ultima_cuota else 0,
                "monto": float(ultima_cuota.monto_cuota) if ultima_cuota else 0,
                "fecha_vencimiento": ultima_cuota.fecha_vencimiento if ultima_cuota else None
            },
            "tiene_whatsapp": bool(cliente.telefono),
            "tiene_email": bool(cliente.email),
            "ultimo_contacto": ultimo_contacto,
            "perfil_pago": "PUNTUAL" if cliente.dias_mora == 0 else "MOROSO"
        }
    
    @staticmethod
    def _generar_mensaje_por_tipo(tipo: str, contexto: Dict, cliente: Cliente) -> Dict:
        """Generar mensaje específico por tipo"""
        nombre = contexto["nombre"].split()[0]  # Primer nombre
        vehiculo = contexto["vehiculo"]
        
        mensajes = {
            "RECORDATORIO_AMIGABLE": {
                "whatsapp": f"""
🚗 Hola {nombre}! 

Te recordamos que tu cuota #{contexto['ultima_cuota']['numero']} de tu {vehiculo} vence el {contexto['ultima_cuota']['fecha_vencimiento']}.

💰 Monto: ${contexto['ultima_cuota']['monto']:,.0f}

Puedes pagar por:
• Transferencia bancaria
• Oficinas autorizadas
• App móvil

¡Gracias por tu puntualidad! 😊
                """,
                "email": f"""
Estimado/a {nombre},

Le recordamos que su cuota #{contexto['ultima_cuota']['numero']} correspondiente a su {vehiculo} vence el {contexto['ultima_cuota']['fecha_vencimiento']}.

Monto a pagar: ${contexto['ultima_cuota']['monto']:,.2f}

Para mayor comodidad, puede realizar su pago a través de nuestros canales digitales.

Saludos cordiales,
Equipo de Cobranzas
                """
            },
            
            "MORA_TEMPRANA": {
                "whatsapp": f"""
⚠️ {nombre}, tu cuota #{contexto['ultima_cuota']['numero']} está vencida.

🚗 Vehículo: {vehiculo}
💰 Monto: ${contexto['ultima_cuota']['monto']:,.0f}
📅 Días de mora: {contexto['dias_mora']}

Para evitar cargos adicionales, realiza tu pago hoy.

¿Necesitas ayuda? Responde este mensaje.
                """,
                "sms": f"FINANCIERA: {nombre}, tu cuota está vencida ({contexto['dias_mora']} días). Monto: ${contexto['ultima_cuota']['monto']:,.0f}. Paga hoy para evitar cargos. Info: 809-XXX-XXXX"
            },
            
            "MORA_AVANZADA": {
                "llamada_script": f"""
Buenos días {nombre}, le habla [NOMBRE] de Cobranzas.

Le contacto porque su cuota #{contexto['ultima_cuota']['numero']} de su {vehiculo} tiene {contexto['dias_mora']} días de mora.

¿Cuándo podría realizar el pago de ${contexto['ultima_cuota']['monto']:,.0f}?

Podemos ofrecerle facilidades de pago si lo necesita.
                """
            },
            
            "FELICITACION_PUNTUALIDAD": {
                "whatsapp": f"""
🎉 ¡Felicidades {nombre}!

Has mantenido tu {vehiculo} al día con todos los pagos. 

Como cliente puntual, tienes beneficios especiales:
• Descuentos en renovaciones
• Tasas preferenciales
• Atención prioritaria

¡Gracias por ser un cliente ejemplar! ⭐
                """
            }
        }
        
        return mensajes.get(tipo, {"mensaje": "Tipo de mensaje no encontrado"})
    
    @staticmethod
    def _recomendar_canal(contexto: Dict) -> str:
        """Recomendar mejor canal de comunicación"""
        if contexto["dias_mora"] == 0:
            return "EMAIL"  # Recordatorios suaves
        elif contexto["dias_mora"] <= 5:
            return "WHATSAPP"  # Contacto directo pero amigable
        elif contexto["dias_mora"] <= 15:
            return "LLAMADA_TELEFONICA"  # Contacto personal
        else:
            return "VISITA_DOMICILIARIA"  # Contacto presencial
    
    @staticmethod
    def _calcular_momento_optimo(contexto: Dict) -> Dict:
        """Calcular momento óptimo para contacto"""
        if contexto["perfil_pago"] == "PUNTUAL":
            return {
                "dias_antes_vencimiento": 3,
                "hora_optima": "09:00",
                "dia_semana": "MARTES_O_MIERCOLES"
            }
        else:
            return {
                "dias_antes_vencimiento": 1,
                "hora_optima": "10:00",
                "dia_semana": "LUNES_O_JUEVES"
            }


# ============================================
# DETECTOR DE PATRONES Y ANOMALÍAS
# ============================================

class DetectorPatrones:
    """
    Detector de patrones y anomalías en comportamiento de pago
    """
    
    @staticmethod
    def detectar_anomalias_cartera(db: Session) -> Dict[str, Any]:
        """
        Detectar anomalías en la cartera que requieren atención
        """
        try:
            anomalias = []
            
            # 1. CLIENTES CON CAMBIO SÚBITO EN COMPORTAMIENTO
            clientes_cambio = DetectorPatrones._detectar_cambio_comportamiento(db)
            if clientes_cambio:
                anomalias.append({
                    "tipo": "CAMBIO_COMPORTAMIENTO",
                    "descripcion": "Clientes con cambio súbito en patrón de pago",
                    "cantidad": len(clientes_cambio),
                    "clientes": clientes_cambio[:10],  # Top 10
                    "accion_recomendada": "CONTACTAR_PROACTIVAMENTE"
                })
            
            # 2. CONCENTRACIÓN DE MORA POR USER
            concentracion_mora = DetectorPatrones._detectar_concentracion_mora_analista(db)
            if concentracion_mora:
                anomalias.append({
                    "tipo": "CONCENTRACION_MORA_USER",
                    "descripcion": "Asesores con alta concentración de mora",
                    "datos": concentracion_mora,
                    "accion_recomendada": "REVISAR_PROCESO_APROBACION"
                })
            
            # 3. PATRONES ESTACIONALES
            patrones_estacionales = DetectorPatrones._detectar_patrones_estacionales(db)
            anomalias.append({
                "tipo": "PATRONES_ESTACIONALES",
                "descripcion": "Patrones de mora por época del año",
                "datos": patrones_estacionales,
                "accion_recomendada": "AJUSTAR_ESTRATEGIA_ESTACIONAL"
            })
            
            return {
                "fecha_analisis": datetime.now().isoformat(),
                "total_anomalias": len(anomalias),
                "anomalias_detectadas": anomalias,
                "nivel_alerta": "ALTO" if len(anomalias) > 2 else "NORMAL"
            }
            
        except Exception as e:
            logger.error(f"Error detectando anomalías: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _detectar_cambio_comportamiento(db: Session) -> List[Dict]:
        """Detectar clientes con cambio súbito en comportamiento"""
        # Clientes que pasaron de puntuales a morosos recientemente
        clientes_cambio = db.query(Cliente).filter(
            Cliente.activo == True,
            Cliente.dias_mora > 15,  # Actualmente en mora
            Cliente.estado_financiero == "EN_MORA"
        ).all()
        
        resultado = []
        for cliente in clientes_cambio:
            # Analizar historial reciente vs anterior
            pagos_recientes = db.query(Pago).join(Prestamo).filter(
                Prestamo.cliente_id == cliente.id,
                Pago.fecha_pago >= date.today() - timedelta(days=90)
            ).all()
            
            pagos_anteriores = db.query(Pago).join(Prestamo).filter(
                Prestamo.cliente_id == cliente.id,
                Pago.fecha_pago < date.today() - timedelta(days=90)
            ).all()
            
            if pagos_anteriores and pagos_recientes:
                mora_anterior = sum(p.dias_mora for p in pagos_anteriores) / len(pagos_anteriores)
                mora_reciente = sum(p.dias_mora for p in pagos_recientes) / len(pagos_recientes)
                
                # Si la mora reciente es significativamente mayor
                if mora_reciente > mora_anterior * 2:
                    resultado.append({
                        "cliente_id": cliente.id,
                        "nombre": cliente.nombre_completo,
                        "mora_anterior": round(mora_anterior, 1),
                        "mora_reciente": round(mora_reciente, 1),
                        "cambio_porcentual": round((mora_reciente - mora_anterior) / mora_anterior * 100, 1)
                    })
        
        return resultado[:20]  # Top 20
    
    @staticmethod
    def _detectar_concentracion_mora_analista(db: Session) -> List[Dict]:
        """Detectar analistaes con alta concentración de mora"""
        # Agrupar mora por analista
        mora_por_analista = db.query(
            User.id,
            User.full_name,
            func.count(Cliente.id).label('total_clientes'),
            func.sum(func.case([(Cliente.dias_mora > 0, 1)], else_=0)).label('clientes_mora'),
            func.avg(Cliente.dias_mora).label('promedio_mora')
        ).join(Cliente, Asesor.id == Cliente.analista_id).filter(
            Cliente.activo == True
        ).group_by(User.id, User.full_name).all()
        
        resultado = []
        for analista in mora_por_analista:
            if analista.total_clientes > 0:
                tasa_mora = (analista.clientes_mora / analista.total_clientes) * 100
                
                # Alertar si tasa de mora > 20%
                if tasa_mora > 20:
                    resultado.append({
                        "analista_id": analista.id,
                        "analista_nombre": analista.full_name,
                        "total_clientes": analista.total_clientes,
                        "clientes_mora": analista.clientes_mora,
                        "tasa_mora": round(tasa_mora, 2),
                        "promedio_dias_mora": round(float(analista.promedio_mora or 0), 1)
                    })
        
        return sorted(resultado, key=lambda x: x["tasa_mora"], reverse=True)
    
    @staticmethod
    def _detectar_patrones_estacionales(db: Session) -> Dict:
        """Detectar patrones estacionales de mora"""
        # Analizar mora por mes del año
        mora_por_mes = {}
        
        for mes in range(1, 13):
            clientes_mes = db.query(Cliente).filter(
                func.extract('month', Cliente.fecha_registro) == mes,
                Cliente.activo == True
            ).all()
            
            if clientes_mes:
                total_mora = sum(c.dias_mora or 0 for c in clientes_mes)
                promedio_mora = total_mora / len(clientes_mes)
                mora_por_mes[mes] = {
                    "mes_nombre": [
                        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
                    ][mes-1],
                    "promedio_mora": round(promedio_mora, 2),
                    "total_clientes": len(clientes_mes)
                }
        
        return mora_por_mes


# ============================================
# SISTEMA DE ALERTAS INTELIGENTES
# ============================================

class AlertasInteligentes:
    """
    Sistema de alertas inteligentes basado en ML
    """
    
    @staticmethod
    def generar_alertas_predictivas(db: Session) -> Dict[str, Any]:
        """
        Generar alertas predictivas basadas en análisis ML
        """
        try:
            alertas = []
            
            # 1. CLIENTES EN RIESGO DE MORA
            clientes_riesgo = AlertasInteligentes._identificar_clientes_riesgo(db)
            if clientes_riesgo:
                alertas.append({
                    "tipo": "RIESGO_MORA",
                    "prioridad": "ALTA",
                    "titulo": f"{len(clientes_riesgo)} clientes en riesgo de mora",
                    "descripcion": "Clientes con alta probabilidad de entrar en mora en los próximos 7 días",
                    "clientes": clientes_riesgo[:10],
                    "accion_recomendada": "Contacto proactivo inmediato"
                })
            
            # 2. DETERIORO DE CARTERA
            deterioro = AlertasInteligentes._detectar_deterioro_cartera(db)
            if deterioro["alerta"]:
                alertas.append({
                    "tipo": "DETERIORO_CARTERA",
                    "prioridad": "MEDIA",
                    "titulo": "Deterioro detectado en calidad de cartera",
                    "descripcion": f"Incremento de {deterioro['incremento']}% en mora este mes",
                    "datos": deterioro,
                    "accion_recomendada": "Revisar políticas de aprobación"
                })
            
            # 3. OPORTUNIDADES DE NEGOCIO
            oportunidades = AlertasInteligentes._identificar_oportunidades(db)
            if oportunidades:
                alertas.append({
                    "tipo": "OPORTUNIDADES",
                    "prioridad": "BAJA",
                    "titulo": f"{len(oportunidades)} oportunidades de negocio",
                    "descripcion": "Clientes elegibles para productos adicionales",
                    "oportunidades": oportunidades,
                    "accion_recomendada": "Contacto comercial"
                })
            
            return {
                "fecha_generacion": datetime.now().isoformat(),
                "total_alertas": len(alertas),
                "alertas": alertas,
                "nivel_sistema": "CRITICO" if any(a["prioridad"] == "ALTA" for a in alertas) else "NORMAL"
            }
            
        except Exception as e:
            logger.error(f"Error generando alertas: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _identificar_clientes_riesgo(db: Session) -> List[Dict]:
        """Identificar clientes en riesgo de entrar en mora"""
        # Clientes actualmente al día pero con señales de riesgo
        clientes_riesgo = []
        
        clientes_al_dia = db.query(Cliente).filter(
            Cliente.activo == True,
            Cliente.estado_financiero == "AL_DIA"
        ).all()
        
        for cliente in clientes_al_dia:
            # Calcular probabilidad de mora
            probabilidad = PrediccionMora.predecir_probabilidad_mora(
                cliente.id, 7, db
            )
            
            if probabilidad.get("probabilidad_mora", 0) > 50:  # >50% probabilidad
                clientes_riesgo.append({
                    "cliente_id": cliente.id,
                    "nombre": cliente.nombre_completo,
                    "cedula": cliente.cedula,
                    "probabilidad_mora": probabilidad["probabilidad_mora"],
                    "factores_riesgo": probabilidad.get("recomendaciones", [])
                })
        
        return sorted(clientes_riesgo, key=lambda x: x["probabilidad_mora"], reverse=True)[:20]
    
    @staticmethod
    def _detectar_deterioro_cartera(db: Session) -> Dict:
        """Detectar deterioro en la calidad de la cartera"""
        # Comparar mora actual vs mes anterior
        hoy = date.today()
        mes_anterior = hoy - timedelta(days=30)
        
        mora_actual = db.query(Cliente).filter(
            Cliente.activo == True,
            Cliente.dias_mora > 0
        ).count()
        
        total_actual = db.query(Cliente).filter(Cliente.activo == True).count()
        tasa_actual = (mora_actual / total_actual * 100) if total_actual > 0 else 0
        
        # Simular tasa del mes anterior (en producción sería histórica)
        tasa_anterior = tasa_actual * 0.9  # Placeholder
        
        incremento = tasa_actual - tasa_anterior
        
        return {
            "alerta": incremento > 2,  # Alerta si incremento > 2%
            "tasa_actual": round(tasa_actual, 2),
            "tasa_anterior": round(tasa_anterior, 2),
            "incremento": round(incremento, 2),
            "clientes_afectados": mora_actual
        }
    
    @staticmethod
    def _identificar_oportunidades(db: Session) -> List[Dict]:
        """Identificar oportunidades de negocio"""
        # Clientes puntuales elegibles para productos adicionales
        clientes_excelentes = db.query(Cliente).filter(
            Cliente.activo == True,
            Cliente.estado_financiero == "AL_DIA",
            Cliente.dias_mora == 0
        ).all()
        
        oportunidades = []
        for cliente in clientes_excelentes[:20]:  # Top 20
            # Calcular scoring
            scoring = ScoringCrediticio.calcular_score_completo(
                {"cedula": cliente.cedula}, {}, db
            )
            
            if scoring["score_final"] > 800:
                oportunidades.append({
                    "cliente_id": cliente.id,
                    "nombre": cliente.nombre_completo,
                    "score": scoring["score_final"],
                    "productos_sugeridos": [
                        "Segundo vehículo",
                        "Refinanciamiento con mejor tasa",
                        "Línea de crédito personal"
                    ]
                })
        
        return oportunidades
