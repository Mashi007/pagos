"""
Servicio de Machine Learning
"""

import logging
import pickle
import numpy as np
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class MLService:
    """Servicio de Machine Learning para análisis de riesgo crediticio"""

    def __init__(self):
        """Inicializar servicio ML"""
        self.models = {}
        self.scalers = {}
        self.model_path = Path("ml_models")
        self.model_path.mkdir(exist_ok=True)

    def load_models(self) -> bool:
        """
        Cargar modelos ML desde archivos

        Returns:
            bool: True si se cargaron exitosamente
        """
        try:
            # Cargar modelo de riesgo
            risk_model_path = self.model_path / "risk_model.pkl"
            if risk_model_path.exists():
                with open(risk_model_path, "rb") as f:
                    self.models["risk_model"] = pickle.load(f)
                logger.info("Modelo de riesgo cargado exitosamente")
            else:
                logger.warning("Modelo de riesgo no encontrado")

            # Cargar scaler de riesgo
            risk_scaler_path = self.model_path / "risk_scaler.pkl"
            if risk_scaler_path.exists():
                with open(risk_scaler_path, "rb") as f:
                    self.scalers["risk_scaler"] = pickle.load(f)
                logger.info("Scaler de riesgo cargado exitosamente")
            else:
                logger.warning("Scaler de riesgo no encontrado")

            return len(self.models) > 0

        except Exception as e:
            logger.error(f"Error cargando modelos: {e}")
            return False

    def predict_risk(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predecir nivel de riesgo crediticio

        Args:
            client_data: Datos del cliente

        Returns:
            Dict con predicción de riesgo
        """
        try:
            if "risk_model" not in self.models:
                return {
                    "risk_level": "Desconocido",
                    "confidence": 0.0,
                    "recommendation": "Modelo no disponible",
                }

            # Preparar características
            features = np.array(
                [
                    [
                        client_data.get("age", 0),
                        client_data.get("income", 0),
                        client_data.get("debt_ratio", 0),
                        client_data.get("credit_score", 0),
                    ]
                ]
            )

            # Escalar características
            if "risk_scaler" in self.scalers:
                scaler = self.scalers["risk_scaler"]
                features_scaled = scaler.transform(features)
            else:
                features_scaled = features

            # Predecir
            model = self.models["risk_model"]
            prediction = model.predict(features_scaled)[0]
            probability = model.predict_proba(features_scaled)[0]

            # Mapear predicción a nivel de riesgo
            risk_levels = ["Bajo", "Medio", "Alto"]
            risk_level = (
                risk_levels[prediction]
                if prediction < len(risk_levels)
                else "Desconocido"
            )

            # Obtener confianza (probabilidad máxima)
            confidence = float(np.max(probability))

            # Obtener recomendación
            recommendation = self._get_risk_recommendation(risk_level)

            return {
                "risk_level": risk_level,
                "confidence": confidence,
                "recommendation": recommendation,
                "features_used": {
                    "age": client_data.get("age", 0),
                    "income": client_data.get("income", 0),
                    "debt_ratio": client_data.get("debt_ratio", 0),
                    "credit_score": client_data.get("credit_score", 0),
                },
            }

        except Exception as e:
            logger.error(f"Error prediciendo riesgo: {e}")
            return {
                "risk_level": "Error",
                "confidence": 0.0,
                "recommendation": f"Error en predicción: {str(e)}",
            }

    def _get_risk_recommendation(self, risk_level: str) -> str:
        """Obtener recomendación basada en nivel de riesgo"""
        recommendations = {
            "Bajo": "Aprobar préstamo con condiciones estándar.",
            "Medio": "Aprobar préstamo con condiciones revisadas.",
            "Alto": "Revisar caso manualmente antes de aprobar.",
            "Desconocido": "Revisar caso manualmente.",
            "Error": "Error en análisis, revisar manualmente.",
        }
        return recommendations.get(risk_level, "Revisar caso manualmente.")

    def get_model_status(self) -> Dict[str, Any]:
        """
        Obtener estado de los modelos

        Returns:
            Dict con estado de los modelos
        """
        return {
            "models_loaded": len(self.models),
            "scalers_loaded": len(self.scalers),
            "available_models": list(self.models.keys()),
            "available_scalers": list(self.scalers.keys()),
            "model_path": str(self.model_path),
        }

    def train_risk_model(self, training_data: list) -> bool:
        """
        Entrenar modelo de riesgo (placeholder)

        Args:
            training_data: Datos de entrenamiento

        Returns:
            bool: True si se entrenó exitosamente
        """
        try:
            # Placeholder para entrenamiento
            logger.info("Entrenamiento de modelo no implementado")
            return False

        except Exception as e:
            logger.error(f"Error entrenando modelo: {e}")
            return False

    def save_models(self) -> bool:
        """
        Guardar modelos en archivos

        Returns:
            bool: True si se guardaron exitosamente
        """
        try:
            # Guardar modelo de riesgo
            if "risk_model" in self.models:
                risk_model_path = self.model_path / "risk_model.pkl"
                with open(risk_model_path, "wb") as f:
                    pickle.dump(self.models["risk_model"], f)
                logger.info("Modelo de riesgo guardado")

            # Guardar scaler de riesgo
            if "risk_scaler" in self.scalers:
                risk_scaler_path = self.model_path / "risk_scaler.pkl"
                with open(risk_scaler_path, "wb") as f:
                    pickle.dump(self.scalers["risk_scaler"], f)
                logger.info("Scaler de riesgo guardado")

            return True

        except Exception as e:
            logger.error(f"Error guardando modelos: {e}")
            return False
