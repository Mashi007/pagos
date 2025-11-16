"""
Servicio de Machine Learning
"""

import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Variables de módulo para evitar warnings duplicados
_sklearn_warning_logged = False
_xgboost_warning_logged = False

# Imports condicionales de scikit-learn
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
    from sklearn.model_selection import train_test_split
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    if not _sklearn_warning_logged:
        logger.warning("scikit-learn no está disponible. Funcionalidades de ML estarán limitadas.")
        _sklearn_warning_logged = True
    # Crear placeholders para evitar errores de referencia
    RandomForestClassifier = None
    MLPClassifier = None
    accuracy_score = None
    f1_score = None
    precision_score = None
    recall_score = None
    roc_auc_score = None
    train_test_split = None
    StandardScaler = None

# Imports condicionales de XGBoost
try:
    import xgboost as xgb
    from xgboost import XGBClassifier

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    if not _xgboost_warning_logged:
        logger.warning("xgboost no está disponible. XGBoost no podrá ser usado.")
        _xgboost_warning_logged = True
    XGBClassifier = None
    xgb = None


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
        # Verificar que al menos una librería ML esté disponible
        if not SKLEARN_AVAILABLE and not XGBOOST_AVAILABLE:
            return {
                "risk_level": "Error",
                "confidence": 0.0,
                "recommendation": "Librerías ML no están instaladas. Instala scikit-learn o xgboost.",
            }

        try:
            if "risk_model" not in self.models:
                return {
                    "risk_level": "Desconocido",
                    "confidence": 0.0,
                    "recommendation": "Modelo no disponible",
                }

            # Preparar características (debe coincidir con el orden de entrenamiento)
            # Orden: edad, ingreso, deuda_total, ratio_deuda_ingreso, historial_pagos, dias_ultimo_prestamo, numero_prestamos_previos
            features = np.array(
                [
                    [
                        client_data.get("age", 0),
                        client_data.get("income", 0),
                        client_data.get("debt_total", 0),
                        client_data.get("debt_ratio", 0),
                        client_data.get("credit_score", 0),  # historial_pagos
                        client_data.get("dias_ultimo_prestamo", 0),
                        client_data.get("numero_prestamos_previos", 0),
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
                    "debt_total": client_data.get("debt_total", 0),
                    "debt_ratio": client_data.get("debt_ratio", 0),
                    "credit_score": client_data.get("credit_score", 0),
                    "dias_ultimo_prestamo": client_data.get("dias_ultimo_prestamo", 0),
                    "numero_prestamos_previos": client_data.get("numero_prestamos_previos", 0),
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
        # Verificar que al menos una librería ML esté disponible
        if not SKLEARN_AVAILABLE and not XGBOOST_AVAILABLE:
            return {
                "success": False,
                "error": "Librerías ML no están instaladas. Instala scikit-learn o xgboost.",
            }

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
            # Usar stratify solo si hay suficientes muestras por clase
            unique_classes, counts = np.unique(y, return_counts=True)
            min_samples_per_class = min(counts) if len(counts) > 0 else 0

            # Stratify requiere al menos 2 muestras por clase en cada split
            use_stratify = min_samples_per_class >= 2 and len(unique_classes) > 1

            if use_stratify:
                try:
                    X_train, X_test, y_train, y_test = train_test_split(
                        X, y, test_size=test_size, random_state=random_state, stratify=y
                    )
                except ValueError as e:
                    # Si falla stratify, usar sin stratify
                    logger.warning(f"No se pudo usar stratify: {e}. Usando división sin stratify.")
                    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)
            else:
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

            # Escalar features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Entrenar modelo según algoritmo
            if algoritmo == "random_forest":
                if not SKLEARN_AVAILABLE or RandomForestClassifier is None:
                    raise ValueError("scikit-learn no está disponible. Instala con: pip install scikit-learn")
                model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=random_state,
                    n_jobs=-1,
                    class_weight="balanced",  # Manejar desbalance de clases
                )
                logger.info("Entrenando modelo Random Forest...")

            elif algoritmo == "xgboost":
                if not XGBOOST_AVAILABLE or XGBClassifier is None:
                    raise ValueError("xgboost no está disponible. Instala con: pip install xgboost")
                model = XGBClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=random_state,
                    n_jobs=-1,
                    tree_method="hist",  # Más rápido y eficiente en memoria
                    eval_metric="mlogloss",  # Para clasificación multiclase
                    use_label_encoder=False,
                )
                logger.info("Entrenando modelo XGBoost...")

            elif algoritmo == "neural_network":
                if not SKLEARN_AVAILABLE or MLPClassifier is None:
                    raise ValueError("scikit-learn no está disponible. Instala con: pip install scikit-learn")
                # Calcular tamaño de capas ocultas basado en número de features
                n_features = X_train_scaled.shape[1]
                # Arquitectura: primera capa más grande, segunda más pequeña
                hidden_layer_sizes = (max(50, n_features * 2), max(25, n_features))
                model = MLPClassifier(
                    hidden_layer_sizes=hidden_layer_sizes,
                    activation="relu",
                    solver="adam",
                    alpha=0.0001,  # Regularización L2
                    learning_rate="adaptive",
                    max_iter=500,
                    random_state=random_state,
                    early_stopping=True,
                    validation_fraction=0.1,
                    n_iter_no_change=10,
                    tol=1e-4,
                )
                logger.info(f"Entrenando modelo Neural Network con capas {hidden_layer_sizes}...")

            else:
                # Por defecto usar Random Forest si el algoritmo no es reconocido
                logger.warning(f"Algoritmo '{algoritmo}' no reconocido. Usando Random Forest por defecto.")
                if not SKLEARN_AVAILABLE or RandomForestClassifier is None:
                    raise ValueError("scikit-learn no está disponible. Instala con: pip install scikit-learn")
                model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=random_state,
                    n_jobs=-1,
                    class_weight="balanced",
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
