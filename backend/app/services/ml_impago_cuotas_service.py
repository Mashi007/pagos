"""
Servicio de Machine Learning para Predicción de Impago de Cuotas
Predice si un cliente pagará o no sus cuotas futuras basado en su historial de pagos
"""

import logging
import pickle
from datetime import date, datetime
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
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
    ML_IMPAGO_SERVICE_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    ML_IMPAGO_SERVICE_AVAILABLE = False
    if not _sklearn_warning_logged:
        logger.warning("scikit-learn no está disponible. Funcionalidades de ML estarán limitadas.")
        _sklearn_warning_logged = True
    RandomForestClassifier = None
    LogisticRegression = None
    accuracy_score = None
    f1_score = None
    precision_score = None
    recall_score = None
    roc_auc_score = None
    train_test_split = None
    StandardScaler = None

# Imports condicionales de XGBoost
try:
    from xgboost import XGBClassifier

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    if not _xgboost_warning_logged:
        logger.warning("xgboost no está disponible. XGBoost no podrá ser usado.")
        _xgboost_warning_logged = True
    XGBClassifier = None


class MLImpagoCuotasService:
    """Servicio de Machine Learning para predicción de impago de cuotas"""

    def __init__(self):
        """Inicializar servicio ML"""
        self.models = {}
        self.scalers = {}
        try:
            self.model_path = Path("ml_models")
            self.model_path.mkdir(exist_ok=True)
            logger.info(f"📁 Directorio de modelos ML: {self.model_path.absolute()}")
        except Exception as e:
            logger.error(f"Error creando directorio de modelos: {e}", exc_info=True)
            raise

    def extract_payment_features(
        self,
        cuotas: List[Any],
        prestamo: Any,
        fecha_actual: Optional[date] = None,
    ) -> Dict[str, float]:
        """
        Extraer features del historial de pagos para predicción de impago

        Args:
            cuotas: Lista de objetos Cuota del préstamo
            prestamo: Objeto Prestamo
            fecha_actual: Fecha actual (default: date.today())

        Returns:
            Dict con features extraídas
        """
        if fecha_actual is None:
            fecha_actual = date.today()

        if not cuotas:
            # Si no hay cuotas, retornar valores por defecto
            return {
                "porcentaje_cuotas_pagadas": 0.0,
                "promedio_dias_mora": 0.0,
                "numero_cuotas_atrasadas": 0.0,
                "numero_cuotas_parciales": 0.0,
                "tasa_cumplimiento": 0.0,
                "dias_desde_ultimo_pago": 0.0,
                "numero_cuotas_restantes": 0.0,
                "monto_promedio_cuota": 0.0,
                "ratio_monto_pendiente": 0.0,
                "tendencia_pagos": 0.0,  # -1 empeora, 0 estable, 1 mejora
                "cuotas_vencidas_sin_pagar": 0.0,
                "monto_total_pendiente": 0.0,
            }

        # Ordenar cuotas por número
        cuotas_ordenadas = sorted(cuotas, key=lambda c: c.numero_cuota)

        # Features básicas (manejar None en estado)
        total_cuotas = len(cuotas_ordenadas)
        cuotas_pagadas = sum(1 for c in cuotas_ordenadas if c.estado and c.estado == "PAGADO")
        cuotas_atrasadas = sum(1 for c in cuotas_ordenadas if c.estado and c.estado == "ATRASADO")
        cuotas_parciales = sum(1 for c in cuotas_ordenadas if c.estado and c.estado == "PARCIAL")
        cuotas_pendientes = sum(1 for c in cuotas_ordenadas if c.estado and c.estado == "PENDIENTE")

        # Porcentaje de cuotas pagadas
        porcentaje_cuotas_pagadas = (cuotas_pagadas / total_cuotas * 100) if total_cuotas > 0 else 0.0

        # Promedio de días de mora
        dias_mora_list = [c.dias_mora or 0 for c in cuotas_ordenadas if c.dias_mora and c.dias_mora > 0]
        promedio_dias_mora = np.mean(dias_mora_list) if dias_mora_list else 0.0

        # Tasa de cumplimiento (cuotas pagadas a tiempo / total de cuotas vencidas)
        cuotas_vencidas = [c for c in cuotas_ordenadas if c.fecha_vencimiento and c.fecha_vencimiento < fecha_actual]
        cuotas_vencidas_pagadas = sum(1 for c in cuotas_vencidas if c.estado == "PAGADO")
        tasa_cumplimiento = (cuotas_vencidas_pagadas / len(cuotas_vencidas) * 100) if cuotas_vencidas else 100.0

        # Días desde último pago
        cuotas_con_pago = [c for c in cuotas_ordenadas if c.fecha_pago is not None]
        if cuotas_con_pago:
            ultima_cuota_pagada = max(cuotas_con_pago, key=lambda c: c.fecha_pago)
            dias_desde_ultimo_pago = (fecha_actual - ultima_cuota_pagada.fecha_pago).days
        else:
            dias_desde_ultimo_pago = (fecha_actual - prestamo.fecha_aprobacion.date()).days if prestamo.fecha_aprobacion else 0

        # Número de cuotas restantes (pendientes o futuras)
        cuotas_restantes = cuotas_pendientes + sum(
            1 for c in cuotas_ordenadas if c.fecha_vencimiento and c.fecha_vencimiento > fecha_actual and c.estado != "PAGADO"
        )

        # Monto promedio de cuota (manejar None y Decimal)
        try:
            montos_cuota = []
            for c in cuotas_ordenadas:
                if c.monto_cuota is not None:
                    try:
                        montos_cuota.append(float(c.monto_cuota))
                    except (ValueError, TypeError):
                        continue
            monto_promedio_cuota = np.mean(montos_cuota) if montos_cuota else 0.0
        except Exception as e:
            logger.warning(f"Error calculando monto promedio de cuota: {e}, usando 0.0")
            monto_promedio_cuota = 0.0

        # Ratio de monto pendiente vs monto total (manejar None y Decimal)
        try:
            monto_total_prestamo = (
                float(prestamo.total_financiamiento or 0) if prestamo.total_financiamiento is not None else 0.0
            )
            monto_total_pagado = 0.0
            for c in cuotas_ordenadas:
                if c.total_pagado is not None:
                    try:
                        monto_total_pagado += float(c.total_pagado)
                    except (ValueError, TypeError):
                        continue
            monto_total_pendiente = monto_total_prestamo - monto_total_pagado
            ratio_monto_pendiente = (monto_total_pendiente / monto_total_prestamo * 100) if monto_total_prestamo > 0 else 0.0
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"Error calculando ratio monto pendiente: {e}, usando 0.0")
            monto_total_pendiente = 0.0
            ratio_monto_pendiente = 0.0

        # Tendencia de pagos (comparar primeras vs últimas cuotas)
        if len(cuotas_ordenadas) >= 4:
            primeras_cuotas = cuotas_ordenadas[: len(cuotas_ordenadas) // 2]
            ultimas_cuotas = cuotas_ordenadas[len(cuotas_ordenadas) // 2 :]

            tasa_primera_mitad = sum(1 for c in primeras_cuotas if c.estado == "PAGADO") / len(primeras_cuotas)
            tasa_ultima_mitad = sum(1 for c in ultimas_cuotas if c.estado == "PAGADO") / len(ultimas_cuotas)

            if tasa_ultima_mitad > tasa_primera_mitad:
                tendencia_pagos = 1.0  # Mejora
            elif tasa_ultima_mitad < tasa_primera_mitad:
                tendencia_pagos = -1.0  # Empeora
            else:
                tendencia_pagos = 0.0  # Estable
        else:
            tendencia_pagos = 0.0

        # Cuotas vencidas sin pagar
        cuotas_vencidas_sin_pagar = sum(
            1
            for c in cuotas_ordenadas
            if c.fecha_vencimiento
            and c.fecha_vencimiento < fecha_actual
            and c.estado
            and c.estado not in ["PAGADO", "PARCIAL"]
        )

        return {
            "porcentaje_cuotas_pagadas": float(porcentaje_cuotas_pagadas),
            "promedio_dias_mora": float(promedio_dias_mora),
            "numero_cuotas_atrasadas": float(cuotas_atrasadas),
            "numero_cuotas_parciales": float(cuotas_parciales),
            "tasa_cumplimiento": float(tasa_cumplimiento),
            "dias_desde_ultimo_pago": float(dias_desde_ultimo_pago),
            "numero_cuotas_restantes": float(cuotas_restantes),
            "monto_promedio_cuota": float(monto_promedio_cuota),
            "ratio_monto_pendiente": float(ratio_monto_pendiente),
            "tendencia_pagos": float(tendencia_pagos),
            "cuotas_vencidas_sin_pagar": float(cuotas_vencidas_sin_pagar),
            "monto_total_pendiente": float(monto_total_pendiente),
        }

    def train_impago_model(
        self,
        training_data: List[Dict],
        algoritmo: str = "random_forest",
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        """
        Entrenar modelo de predicción de impago de cuotas

        Args:
            training_data: Lista de dicts con features y target (0=Pagó, 1=No pagó)
            algoritmo: Algoritmo a usar (random_forest, xgboost, logistic_regression)
            test_size: Proporción de datos para test (0.2 = 20%)
            random_state: Semilla para reproducibilidad

        Returns:
            Dict con métricas y ruta del modelo guardado
        """
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

            # Orden de features (debe coincidir con extract_payment_features)
            feature_order = [
                "porcentaje_cuotas_pagadas",
                "promedio_dias_mora",
                "numero_cuotas_atrasadas",
                "numero_cuotas_parciales",
                "tasa_cumplimiento",
                "dias_desde_ultimo_pago",
                "numero_cuotas_restantes",
                "monto_promedio_cuota",
                "ratio_monto_pendiente",
                "tendencia_pagos",
                "cuotas_vencidas_sin_pagar",
                "monto_total_pendiente",
            ]

            for sample in training_data:
                # Validar y convertir features a float, manejar None
                features = []
                for feature in feature_order:
                    value = sample.get(feature, 0.0)
                    # Convertir None a 0.0 y asegurar que sea numérico
                    if value is None:
                        features.append(0.0)
                    else:
                        try:
                            features.append(float(value))
                        except (ValueError, TypeError):
                            logger.warning(f"Feature '{feature}' tiene valor inválido: {value}, usando 0.0")
                            features.append(0.0)

                # Validar que todas las features sean numéricas
                if len(features) != len(feature_order):
                    logger.error(
                        f"Error: número de features incorrecto. Esperado {len(feature_order)}, obtenido {len(features)}"
                    )
                    raise ValueError(f"Número de features incorrecto: {len(features)} != {len(feature_order)}")

                X.append(features)

                # Validar target
                target = sample.get("target", 0)
                if target is None:
                    target = 0
                try:
                    target = int(target)
                    if target not in [0, 1]:
                        logger.warning(f"Target inválido: {target}, usando 0")
                        target = 0
                except (ValueError, TypeError):
                    logger.warning(f"Target no numérico: {target}, usando 0")
                    target = 0
                y.append(target)

            # Validar que X e y tengan el mismo número de muestras
            if len(X) != len(y):
                raise ValueError(f"Número de muestras inconsistente: X={len(X)}, y={len(y)}")

            # Convertir a numpy array con validación
            try:
                X = np.array(X, dtype=np.float64)  # type: ignore[assignment]
                y = np.array(y, dtype=np.int32)  # type: ignore[assignment]
            except (ValueError, TypeError) as e:
                logger.error(f"Error convirtiendo a numpy array: {e}")
                logger.error(f"X sample: {X[0] if X else 'empty'}")
                logger.error(f"y sample: {y[:5] if len(y) > 5 else y}")
                raise ValueError(f"Error convirtiendo datos a numpy array: {e}")

            # Validar dimensiones
            if X.shape[0] == 0:
                raise ValueError("No hay muestras para entrenar")
            if X.shape[1] != len(feature_order):
                raise ValueError(f"Dimensiones incorrectas: X.shape={X.shape}, esperado {len(feature_order)} features")

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
                    class_weight="balanced",
                )
                logger.info("Entrenando modelo Random Forest para impago de cuotas...")

            elif algoritmo == "xgboost":
                if not XGBOOST_AVAILABLE or XGBClassifier is None:
                    raise ValueError("xgboost no está disponible. Instala con: pip install xgboost")
                model = XGBClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=random_state,
                    n_jobs=-1,
                    eval_metric="logloss",
                    use_label_encoder=False,
                )
                logger.info("Entrenando modelo XGBoost para impago de cuotas...")

            elif algoritmo == "logistic_regression":
                if not SKLEARN_AVAILABLE or LogisticRegression is None:
                    raise ValueError("scikit-learn no está disponible. Instala con: pip install scikit-learn")
                model = LogisticRegression(
                    max_iter=1000,
                    random_state=random_state,
                    class_weight="balanced",
                )
                logger.info("Entrenando modelo Logistic Regression para impago de cuotas...")

            else:
                # Por defecto usar Random Forest
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
            precision = precision_score(y_test, y_pred, average="binary", zero_division=0)
            recall = recall_score(y_test, y_pred, average="binary", zero_division=0)
            f1 = f1_score(y_test, y_pred, average="binary", zero_division=0)

            # ROC AUC
            roc_auc = None
            if len(np.unique(y)) >= 2:
                try:
                    roc_auc = roc_auc_score(y_test, y_pred_proba[:, 1])
                except Exception as e:
                    logger.warning(f"No se pudo calcular ROC AUC: {e}")

            # Guardar modelo y scaler
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_filename = f"impago_cuotas_model_{timestamp}.pkl"
            scaler_filename = f"impago_cuotas_scaler_{timestamp}.pkl"

            model_path = self.model_path / model_filename
            scaler_path = self.model_path / scaler_filename

            try:
                # Asegurar que el directorio existe
                self.model_path.mkdir(parents=True, exist_ok=True)

                with open(model_path, "wb") as f:
                    pickle.dump(model, f)
                logger.info(f"💾 Modelo guardado en: {model_path.absolute()}")

                with open(scaler_path, "wb") as f:
                    pickle.dump(scaler, f)
                logger.info(f"💾 Scaler guardado en: {scaler_path.absolute()}")
            except (IOError, OSError, PermissionError) as e:
                error_msg = f"Error guardando modelo en disco: {e}"
                logger.error(error_msg, exc_info=True)
                raise ValueError(error_msg)

            # Actualizar modelos en memoria
            self.models["impago_cuotas_model"] = model
            self.scalers["impago_cuotas_scaler"] = scaler

            logger.info(f"✅ Modelo de impago entrenado exitosamente: {model_filename}")
            roc_auc_str = f"{roc_auc:.4f}" if roc_auc is not None else "N/A"
            logger.info(f"   Accuracy: {accuracy:.4f}, F1: {f1:.4f}, ROC AUC: {roc_auc_str}")

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
                "features": feature_order,
            }

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"Error entrenando modelo de impago: {error_type}: {error_msg}", exc_info=True)
            return {
                "success": False,
                "error": f"{error_type}: {error_msg}",
            }

    def predict_impago(
        self,
        payment_features: Dict[str, float],
        model_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Predecir probabilidad de impago de cuotas futuras

        Args:
            payment_features: Features extraídas del historial de pagos
            model_path: Ruta al modelo (opcional, usa modelo en memoria si no se especifica)

        Returns:
            Dict con predicción de impago
        """
        if not SKLEARN_AVAILABLE and not XGBOOST_AVAILABLE:
            return {
                "probabilidad_impago": 0.0,
                "probabilidad_pago": 0.0,
                "prediccion": "Error",
                "confidence": 0.0,
                "recomendacion": "Librerías ML no están instaladas.",
            }

        try:
            # Cargar modelo si no está en memoria
            if model_path:
                if not self.load_model_from_path(model_path):
                    return {
                        "probabilidad_impago": 0.0,
                        "probabilidad_pago": 0.0,
                        "prediccion": "Error",
                        "confidence": 0.0,
                        "recomendacion": "Error cargando modelo",
                    }

            if "impago_cuotas_model" not in self.models:
                return {
                    "probabilidad_impago": 0.0,
                    "probabilidad_pago": 0.0,
                    "prediccion": "Desconocido",
                    "confidence": 0.0,
                    "recomendacion": "Modelo no disponible",
                }

            # Preparar features en el orden correcto
            feature_order = [
                "porcentaje_cuotas_pagadas",
                "promedio_dias_mora",
                "numero_cuotas_atrasadas",
                "numero_cuotas_parciales",
                "tasa_cumplimiento",
                "dias_desde_ultimo_pago",
                "numero_cuotas_restantes",
                "monto_promedio_cuota",
                "ratio_monto_pendiente",
                "tendencia_pagos",
                "cuotas_vencidas_sin_pagar",
                "monto_total_pendiente",
            ]

            features = np.array([[payment_features.get(feature, 0.0) for feature in feature_order]])  # type: ignore[assignment]

            # Escalar features
            if "impago_cuotas_scaler" in self.scalers:
                scaler = self.scalers["impago_cuotas_scaler"]
                features_scaled = scaler.transform(features)
            else:
                features_scaled = features

            # Predecir
            model = self.models["impago_cuotas_model"]
            prediction = model.predict(features_scaled)[0]
            probability = model.predict_proba(features_scaled)[0]

            # Probabilidades
            probabilidad_impago = float(probability[1]) if len(probability) > 1 else 0.0
            probabilidad_pago = float(probability[0])

            # Nivel de riesgo basado en probabilidad
            if probabilidad_impago >= 0.7:
                nivel_riesgo = "Alto"
                recomendacion = "Alta probabilidad de impago. Considerar acciones preventivas."
            elif probabilidad_impago >= 0.4:
                nivel_riesgo = "Medio"
                recomendacion = "Riesgo moderado de impago. Monitorear de cerca."
            else:
                nivel_riesgo = "Bajo"
                recomendacion = "Baja probabilidad de impago. Cliente con buen historial."

            return {
                "probabilidad_impago": probabilidad_impago,
                "probabilidad_pago": probabilidad_pago,
                "prediccion": "No pagará" if prediction == 1 else "Pagará",
                "nivel_riesgo": nivel_riesgo,
                "confidence": max(probabilidad_impago, probabilidad_pago),
                "recomendacion": recomendacion,
                "features_usadas": payment_features,
            }

        except Exception as e:
            logger.error(f"Error prediciendo impago: {e}", exc_info=True)
            return {
                "probabilidad_impago": 0.0,
                "probabilidad_pago": 0.0,
                "prediccion": "Error",
                "confidence": 0.0,
                "recomendacion": f"Error en predicción: {str(e)}",
            }

    def load_model_from_path(self, model_path: str, scaler_path: Optional[str] = None) -> bool:
        """
        Cargar modelo desde una ruta específica

        Args:
            model_path: Ruta al archivo del modelo
            scaler_path: Ruta al archivo del scaler (opcional, se busca automáticamente)

        Returns:
            bool: True si se cargó exitosamente
        """
        try:
            model_file = Path(model_path)
            if not model_file.exists():
                logger.error(f"Modelo no encontrado: {model_path}")
                return False

            with open(model_file, "rb") as f:
                self.models["impago_cuotas_model"] = pickle.load(f)

            # Buscar scaler si no se especifica
            if scaler_path:
                scaler_file = Path(scaler_path)
            else:
                # Intentar encontrar scaler con mismo timestamp
                model_stem = model_file.stem
                if "impago_cuotas_model_" in model_stem:
                    timestamp = model_stem.replace("impago_cuotas_model_", "")
                    scaler_file = self.model_path / f"impago_cuotas_scaler_{timestamp}.pkl"
                else:
                    scaler_file = None

            if scaler_file and scaler_file.exists():
                with open(scaler_file, "rb") as f:
                    self.scalers["impago_cuotas_scaler"] = pickle.load(f)

            logger.info(f"✅ Modelo de impago cargado desde: {model_path}")
            return True

        except Exception as e:
            logger.error(f"Error cargando modelo: {e}", exc_info=True)
            return False
