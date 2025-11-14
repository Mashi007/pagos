"""
Servicio de Machine Learning
"""

import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

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
            risk_level = risk_levels[prediction] if prediction < len(risk_levels) else "Desconocido"

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

    def train_risk_model(
        self,
        training_data: List[Dict],
        algoritmo: str = "random_forest",
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        """
        Entrenar modelo de riesgo crediticio

        Args:
            training_data: Lista de dicts con features y target
            algoritmo: Algoritmo a usar (random_forest, xgboost, etc.)
            test_size: Proporción de datos para test (0.2 = 20%)
            random_state: Semilla para reproducibilidad

        Returns:
            Dict con métricas y ruta del modelo guardado
        """
        try:
            if not training_data or len(training_data) < 10:
                raise ValueError("Se necesitan al menos 10 muestras para entrenar")

            # Extraer features y target
            X = []
            y = []

            for sample in training_data:
                features = [
                    sample.get("edad", 0),
                    sample.get("ingreso", 0),
                    sample.get("deuda_total", 0),
                    sample.get("ratio_deuda_ingreso", 0),
                    sample.get("historial_pagos", 0),
                    sample.get("dias_ultimo_prestamo", 0),
                    sample.get("numero_prestamos_previos", 0),
                ]
                X.append(features)
                y.append(sample.get("target", 0))  # 0=Bajo, 1=Medio, 2=Alto

            X = np.array(X)
            y = np.array(y)

            # Dividir en train y test
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state, stratify=y
            )

            # Escalar features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Entrenar modelo según algoritmo
            if algoritmo == "random_forest":
                model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=random_state,
                    n_jobs=-1,
                )
            else:
                # Por defecto usar Random Forest
                model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=random_state,
                    n_jobs=-1,
                )

            model.fit(X_train_scaled, y_train)

            # Evaluar modelo
            y_pred = model.predict(X_test_scaled)
            y_pred_proba = model.predict_proba(X_test_scaled)

            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, average="weighted", zero_division=0)
            recall = recall_score(y_test, y_pred, average="weighted", zero_division=0)
            f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

            # ROC AUC (solo si hay al menos 2 clases)
            roc_auc = None
            if len(np.unique(y)) >= 2:
                try:
                    if len(np.unique(y)) == 2:
                        roc_auc = roc_auc_score(y_test, y_pred_proba[:, 1])
                    else:
                        roc_auc = roc_auc_score(y_test, y_pred_proba, multi_class="ovr", average="weighted")
                except Exception as e:
                    logger.warning(f"No se pudo calcular ROC AUC: {e}")

            # Guardar modelo y scaler
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_filename = f"risk_model_{timestamp}.pkl"
            scaler_filename = f"risk_scaler_{timestamp}.pkl"

            model_path = self.model_path / model_filename
            scaler_path = self.model_path / scaler_filename

            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            with open(scaler_path, "wb") as f:
                pickle.dump(scaler, f)

            # Guardar también como archivos por defecto
            default_model_path = self.model_path / "risk_model.pkl"
            default_scaler_path = self.model_path / "risk_scaler.pkl"

            with open(default_model_path, "wb") as f:
                pickle.dump(model, f)

            with open(default_scaler_path, "wb") as f:
                pickle.dump(scaler, f)

            # Actualizar modelos en memoria
            self.models["risk_model"] = model
            self.scalers["risk_scaler"] = scaler

            logger.info(f"✅ Modelo entrenado exitosamente: {model_filename}")
            logger.info(f"   Accuracy: {accuracy:.4f}, F1: {f1:.4f}")

            return {
                "success": True,
                "model_path": str(model_path),
                "scaler_path": str(scaler_path),
                "metrics": {
                    "accuracy": float(accuracy),
                    "precision": float(precision),
                    "recall": float(recall),
                    "f1_score": float(f1),
                    "roc_auc": float(roc_auc) if roc_auc else None,
                },
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "features": [
                    "edad",
                    "ingreso",
                    "deuda_total",
                    "ratio_deuda_ingreso",
                    "historial_pagos",
                    "dias_ultimo_prestamo",
                    "numero_prestamos_previos",
                ],
            }

        except Exception as e:
            logger.error(f"Error entrenando modelo: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    def load_model_from_path(self, model_path: str, scaler_path: Optional[str] = None) -> bool:
        """
        Cargar modelo desde una ruta específica

        Args:
            model_path: Ruta al archivo del modelo
            scaler_path: Ruta al archivo del scaler (opcional)

        Returns:
            bool: True si se cargó exitosamente
        """
        try:
            model_file = Path(model_path)
            if not model_file.exists():
                logger.error(f"Modelo no encontrado: {model_path}")
                return False

            with open(model_file, "rb") as f:
                self.models["risk_model"] = pickle.load(f)

            if scaler_path:
                scaler_file = Path(scaler_path)
                if scaler_file.exists():
                    with open(scaler_file, "rb") as f:
                        self.scalers["risk_scaler"] = pickle.load(f)

            logger.info(f"✅ Modelo cargado desde: {model_path}")
            return True

        except Exception as e:
            logger.error(f"Error cargando modelo: {e}", exc_info=True)
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
