#!/usr/bin/env python3
"""
Script para reescribir todos los archivos de servicios corruptos desde cero
"""

import os
import shutil

def create_clean_service_file(file_path, content):
    """Crear archivo de servicio limpio desde cero"""
    
    print(f"Creando archivo limpio: {file_path}")
    
    # Crear backup del archivo original
    if os.path.exists(file_path):
        backup_path = file_path + ".backup_corrupt"
        shutil.copy2(file_path, backup_path)
        print(f"  Backup creado: {backup_path}")
    
    # Escribir archivo completamente nuevo
    try:
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        print(f"  OK: Archivo creado exitosamente")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def create_auth_service():
    """Crear auth_service.py limpio"""
    
    content = '''# backend/app/services/auth_service.py
"""Servicio de autenticación

Lógica de negocio para login, logout, refresh tokens
"""

import logging
from datetime import datetime
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, Token

logger = logging.getLogger(__name__)


# Servicio de autenticación principal
class AuthService:
    """Servicio de autenticación"""

    @staticmethod
    def authenticate_user(
        db: Session, email: str, password: str
    ) -> Optional[User]:
        """
        Autentica un usuario con email y contraseña
        
        Args:
            db: Sesión de base de datos
            email: Email del usuario
            password: Contraseña en texto plano
            
        Returns:
            Usuario si la autenticación es exitosa, None si no
        """
        # Consulta específica solo con columnas necesarias para autenticación
        # CASE INSENSITIVE: Normalizar email a minúsculas para búsqueda
        email_normalized = email.lower().strip()
        
        logger.info(
            f"AuthService.authenticate_user - Intentando autenticar "
            f"usuario: {email_normalized}"
        )
        
        user = (
            db.query(User)
            .filter(func.lower(User.email) == email_normalized, User.is_active)
            .first()
        )
        
        if not user:
            logger.warning(
                f"AuthService.authenticate_user - Usuario "
                f"no encontrado: {email_normalized}"
            )
            return None
        
        if not verify_password(password, user.hashed_password):
            logger.warning(
                f"AuthService.authenticate_user - Contraseña incorrecta "
                f"para: {email_normalized}"
            )
            return None
        
        logger.info(
            f"AuthService.authenticate_user - "
            f"Autenticación exitosa para: {email_normalized}"
        )
        return user

    @staticmethod
    def login(db: Session, login_data: LoginRequest) -> Tuple[Token, User]:
        """
        Realiza el login de un usuario
        
        Args:
            db: Sesión de base de datos
            login_data: Datos de login (email, password)
            
        Returns:
            Tupla de (Token, User)
            
        Raises:
            HTTPException: Si las credenciales son inválidas o el usuario está inactivo
        """
        # Autenticar usuario
        logger.info(
            f"AuthService.login - "
            f"Iniciando proceso de login para: {login_data.email}"
        )
        
        user = AuthService.authenticate_user(
            db, login_data.email, login_data.password
        )
        
        if not user:
            logger.warning(
                f"AuthService.login - "
                f"Fallo en autenticación para: {login_data.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verificar que el usuario esté activo
        if not user.is_active:
            logger.warning(
                f"AuthService.login - Usuario inactivo: {login_data.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo. Contacte al administrador.",
            )
        
        # Actualizar last_login
        user.last_login = datetime.utcnow()
        db.commit()
        
        logger.info(
            f"AuthService.login - Login exitoso para: {login_data.email}"
        )
        
        # Crear tokens
        access_token = create_access_token(
            subject=user.id,
            additional_claims={
                "is_admin": user.is_admin,
                "email": user.email,
            },
        )
        refresh_token = create_refresh_token(subject=user.id)
        
        token = Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
        
        return token, user

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Token:
        """
        Genera un nuevo access token usando un refresh token
        
        Args:
            db: Sesión de base de datos
            refresh_token: Refresh token válido
            
        Returns:
            Nuevo par de tokens
            
        Raises:
            HTTPException: Si el refresh token es inválido
        """
        try:
            payload = decode_token(refresh_token)
            
            # Verificar que sea un refresh token
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido",
                )
            
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido",
                )
            
            # Buscar usuario
            user = db.query(User).filter(User.id == int(user_id)).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado",
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuario inactivo",
                )
            
            # Crear nuevos tokens
            new_access_token = create_access_token(
                subject=user.id,
                additional_claims={
                    "is_admin": user.is_admin,
                    "email": user.email,
                },
            )
            new_refresh_token = create_refresh_token(subject=user.id)
            
            return Token(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Error procesando token: {str(e)}",
            )

    @staticmethod
    def change_password(
        db: Session, user: User, current_password: str, new_password: str
    ) -> User:
        """
        Cambia la contraseña de un usuario
        
        Args:
            db: Sesión de base de datos
            user: Usuario actual
            current_password: Contraseña actual
            new_password: Nueva contraseña
            
        Returns:
            Usuario actualizado
            
        Raises:
            HTTPException: Si la contraseña actual es incorrecta o la nueva es débil
        """
        # Verificar contraseña actual
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contraseña actual incorrecta",
            )
        
        # Validar fortaleza de nueva contraseña
        is_valid, message = validate_password_strength(new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=message
            )
        
        # Actualizar contraseña
        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        return user

    @staticmethod
    def get_user_permissions(user: User) -> list[str]:
        """
        Obtiene los permisos de un usuario basado en su rol
        
        Args:
            user: Usuario
            
        Returns:
            Lista de permisos (strings)
        """
        try:
            # Usar is_admin directamente - evitar conflicto de nombres
            from app.core.permissions_simple import (
                get_user_permissions as get_permissions,
            )
            
            permissions = get_permissions(user.is_admin)
            permission_strings = [perm.value for perm in permissions]
            return permission_strings
            
        except Exception:
            # Si hay error, retornar permisos vacíos
            return []
'''
    
    return create_clean_service_file("backend/app/services/auth_service.py", content)

def create_email_service():
    """Crear email_service.py limpio"""
    
    content = '''# backend/app/services/email_service.py
"""Servicio de envío de emails

Configuración y envío de emails usando SMTP
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para envío de emails"""

    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        is_html: bool = False,
    ) -> Dict[str, any]:
        """
        Enviar email
        
        Args:
            to_emails: Lista de emails destinatarios
            subject: Asunto del email
            body: Cuerpo del email
            is_html: Si el cuerpo es HTML
            
        Returns:
            Dict con resultado del envío
        """
        try:
            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            
            # Agregar cuerpo
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Enviar email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            
            text = msg.as_string()
            server.sendmail(self.from_email, to_emails, text)
            server.quit()
            
            logger.info(f"Email enviado exitosamente a {to_emails}")
            return {
                "success": True,
                "message": "Email enviado exitosamente",
                "recipients": to_emails
            }
            
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
            return {
                "success": False,
                "error": str(e),
                "recipients": to_emails
            }

    def send_notification_email(
        self,
        to_email: str,
        notification_type: str,
        data: Dict[str, any]
    ) -> Dict[str, any]:
        """
        Enviar email de notificación
        
        Args:
            to_email: Email destinatario
            notification_type: Tipo de notificación
            data: Datos para el template
            
        Returns:
            Dict con resultado del envío
        """
        try:
            # Generar contenido basado en tipo
            if notification_type == "payment_reminder":
                subject = "Recordatorio de Pago"
                body = f"""
                Estimado/a {data.get('client_name', 'Cliente')},
                
                Le recordamos que tiene un pago pendiente por el monto de ${data.get('amount', '0')}.
                Fecha de vencimiento: {data.get('due_date', 'N/A')}
                
                Por favor, realice su pago a la brevedad posible.
                
                Saludos cordiales,
                Equipo de Financiamiento
                """
            else:
                subject = "Notificación del Sistema"
                body = f"""
                Estimado/a {data.get('client_name', 'Cliente')},
                
                {data.get('message', 'Tiene una nueva notificación del sistema.')}
                
                Saludos cordiales,
                Equipo de Financiamiento
                """
            
            return self.send_email([to_email], subject, body)
            
        except Exception as e:
            logger.error(f"Error enviando email de notificación: {e}")
            return {
                "success": False,
                "error": str(e)
            }
'''
    
    return create_clean_service_file("backend/app/services/email_service.py", content)

def create_ml_service():
    """Crear ml_service.py limpio"""
    
    content = '''# backend/app/services/ml_service.py
"""Servicio de Machine Learning

Modelos y predicciones para el sistema de financiamiento
"""

import logging
from typing import Dict, List, Optional
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class MLService:
    """Servicio de Machine Learning"""

    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.is_trained = False

    def train_risk_model(self, data: List[Dict]) -> Dict[str, any]:
        """
        Entrenar modelo de evaluación de riesgo
        
        Args:
            data: Datos de entrenamiento
            
        Returns:
            Dict con resultados del entrenamiento
        """
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No hay datos para entrenar"
                }
            
            # Preparar datos
            X = []
            y = []
            
            for record in data:
                features = [
                    record.get('age', 0),
                    record.get('income', 0),
                    record.get('debt_ratio', 0),
                    record.get('credit_score', 0),
                ]
                X.append(features)
                y.append(record.get('risk_level', 0))
            
            X = np.array(X)
            y = np.array(y)
            
            # Dividir datos
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Escalar características
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Entrenar modelo
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_train_scaled, y_train)
            
            # Guardar modelo y scaler
            self.models['risk_model'] = model
            self.scalers['risk_scaler'] = scaler
            self.is_trained = True
            
            # Calcular precisión
            accuracy = model.score(X_test_scaled, y_test)
            
            logger.info(f"Modelo de riesgo entrenado con precisión: {accuracy:.2f}")
            
            return {
                "success": True,
                "accuracy": accuracy,
                "message": "Modelo entrenado exitosamente"
            }
            
        except Exception as e:
            logger.error(f"Error entrenando modelo: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def predict_risk(self, client_data: Dict) -> Dict[str, any]:
        """
        Predecir nivel de riesgo de un cliente
        
        Args:
            client_data: Datos del cliente
            
        Returns:
            Dict con predicción de riesgo
        """
        try:
            if not self.is_trained:
                return {
                    "success": False,
                    "error": "Modelo no entrenado"
                }
            
            # Preparar características
            features = np.array([[
                client_data.get('age', 0),
                client_data.get('income', 0),
                client_data.get('debt_ratio', 0),
                client_data.get('credit_score', 0),
            ]])
            
            # Escalar características
            scaler = self.scalers['risk_scaler']
            features_scaled = scaler.transform(features)
            
            # Predecir
            model = self.models['risk_model']
            prediction = model.predict(features_scaled)[0]
            probability = model.predict_proba(features_scaled)[0]
            
            # Mapear predicción a nivel de riesgo
            risk_levels = ['Bajo', 'Medio', 'Alto']
            risk_level = risk_levels[prediction] if prediction < len(risk_levels) else 'Desconocido'
            
            return {
                "success": True,
                "risk_level": risk_level,
                "risk_score": prediction,
                "probabilities": probability.tolist(),
                "recommendation": self._get_risk_recommendation(risk_level)
            }
            
        except Exception as e:
            logger.error(f"Error prediciendo riesgo: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _get_risk_recommendation(self, risk_level: str) -> str:
        """Obtener recomendación basada en nivel de riesgo"""
        recommendations = {
            'Bajo': 'Cliente de bajo riesgo. Aprobar financiamiento.',
            'Medio': 'Cliente de riesgo medio. Revisar documentación adicional.',
            'Alto': 'Cliente de alto riesgo. Requiere análisis detallado.'
        }
        return recommendations.get(risk_level, 'Revisar caso manualmente.')

    def get_model_status(self) -> Dict[str, any]:
        """Obtener estado de los modelos"""
        return {
            "is_trained": self.is_trained,
            "models_available": list(self.models.keys()),
            "scalers_available": list(self.scalers.keys())
        }
'''
    
    return create_clean_service_file("backend/app/services/ml_service.py", content)

def create_whatsapp_service():
    """Crear whatsapp_service.py limpio"""
    
    content = '''# backend/app/services/whatsapp_service.py
"""Servicio para envío de mensajes WhatsApp

Usando Meta Developers API
"""

import logging
import re
from typing import Any, Dict, Optional
import aiohttp

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Servicio para gestión de WhatsApp usando Meta Developers API"""

    def __init__(self):
        # Configuración de Meta Developers API
        self.api_url = getattr(settings, 'WHATSAPP_API_URL', 'https://graph.facebook.com/v18.0')
        self.access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)
        self.phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None)
        
        # Verificar configuración
        if not self.access_token or not self.phone_number_id:
            logger.warning("Credenciales de Meta Developers no configuradas")

    async def send_message(
        self,
        to_number: str,
        message: str,
        template_name: Optional[str] = None,
        template_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Enviar mensaje WhatsApp usando Meta Developers API
        
        Args:
            to_number: Número de teléfono destinatario
            message: Mensaje a enviar
            template_name: Nombre del template (opcional)
            template_params: Parámetros del template (opcional)
            
        Returns:
            Dict con resultado del envío
        """
        try:
            if not self.access_token or not self.phone_number_id:
                return {
                    "success": False,
                    "error": "WhatsApp no configurado. Faltan credenciales de Meta",
                    "message_id": None,
                }

            # Formatear número
            clean_number = (
                to_number.replace("+", "").replace(" ", "").replace("-", "")
            )
            
            if not clean_number.isdigit():
                return {
                    "success": False,
                    "error": "Número de teléfono inválido",
                    "message_id": None,
                }

            # URL del endpoint de Meta
            url = f"{self.api_url}/{self.phone_number_id}/messages"

            # Headers
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            # Preparar payload
            if template_name and template_params:
                # Mensaje con template
                payload = {
                    "messaging_product": "whatsapp",
                    "to": clean_number,
                    "type": "template",
                    "template": {
                        "name": template_name,
                        "language": {"code": "es"},
                        "components": [
                            {
                                "type": "body",
                                "parameters": [
                                    {"type": "text", "text": str(value)}
                                    for value in template_params.values()
                                ],
                            }
                        ],
                    },
                }
            else:
                # Mensaje simple
                payload = {
                    "messaging_product": "whatsapp",
                    "to": clean_number,
                    "type": "text",
                    "text": {"body": message},
                }

            # Enviar mensaje
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers=headers, json=payload
                ) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        message_id = response_data.get("messages", [{}])[0].get("id")
                        
                        logger.info(f"Mensaje WhatsApp enviado: {message_id}")
                        return {
                            "success": True,
                            "message_id": message_id,
                            "status": "sent",
                            "error": None,
                        }
                    else:
                        error_msg = f"Error Meta API: {response_data}"
                        logger.error(error_msg)
                        return {
                            "success": False,
                            "error": error_msg,
                            "message_id": None,
                        }

        except Exception as e:
            error_msg = f"Error enviando WhatsApp: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "message_id": None}

    def validate_phone_number(self, phone_number: str) -> bool:
        """
        Validar formato de número de teléfono
        
        Args:
            phone_number: Número a validar
            
        Returns:
            True si es válido
        """
        # Formato esperado: +593999999999 o similar
        pattern = r"^\+\d{10,15}$"
        return bool(re.match(pattern, phone_number))

    def validate_meta_configuration(self) -> Dict[str, Any]:
        """
        Validar configuración de Meta Developers
        
        Returns:
            Dict con estado de la configuración
        """
        config_status = {
            "access_token": bool(self.access_token),
            "phone_number_id": bool(self.phone_number_id),
            "api_url": self.api_url,
        }
        config_status["ready"] = all([
            config_status["access_token"], 
            config_status["phone_number_id"]
        ])
        
        return config_status
'''
    
    return create_clean_service_file("backend/app/services/whatsapp_service.py", content)

def main():
    """Función principal"""
    
    print("REESCRIBIENDO ARCHIVOS DE SERVICIOS CORRUPTOS DESDE CERO")
    print("=" * 70)
    
    success_count = 0
    
    # Crear archivos de servicios desde cero
    if create_auth_service():
        success_count += 1
    
    if create_email_service():
        success_count += 1
    
    if create_ml_service():
        success_count += 1
    
    if create_whatsapp_service():
        success_count += 1
    
    print(f"\nRESUMEN: {success_count}/4 archivos de servicios creados exitosamente")
    print("Archivos reescritos desde cero con codificación UTF-8 limpia")

if __name__ == "__main__":
    main()
