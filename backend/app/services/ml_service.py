# backend/app/services/ml_service.py
"""Servicio de Machine Learning

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

        Returns:
        """
        try:
            if not data:
                return {
                    "success": False,
                }

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
        return {
            "is_trained": self.is_trained,
            "models_available": list(self.models.keys()),
            "scalers_available": list(self.scalers.keys())
        }
