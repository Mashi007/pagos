# Instalación de scikit-learn

## ✅ Estado Actual

**scikit-learn 1.6.1** está instalado y funcionando correctamente.

## 📋 Información de Instalación

### Versión Instalada
- **scikit-learn:** 1.6.1
- **Dependencias instaladas:**
  - numpy (ya estaba instalado)
  - scipy 1.16.3
  - joblib 1.5.2
  - threadpoolctl 3.6.0

### Ubicación en Requirements
- **Archivo:** `backend/requirements/base.txt`
- **Línea 55:** `scikit-learn==1.6.1`

## 🔧 Cómo Instalar

### Opción 1: Instalación Directa
```bash
pip install scikit-learn==1.6.1
```

### Opción 2: Desde Requirements
```bash
cd backend
pip install -r requirements/base.txt
```

### Opción 3: Instalar Todas las Dependencias
```bash
cd backend
pip install -r requirements.txt
```

## ✅ Verificación

### Verificar Instalación
```bash
python -c "import sklearn; print(f'scikit-learn {sklearn.__version__} instalado')"
```

### Verificar con Script
```bash
python verificar_ml_simple.py
```

Debería mostrar:
```
[4] Verificando scikit-learn...
    OK - scikit-learn 1.6.1 instalado
```

## 🎯 Uso en el Proyecto

scikit-learn se usa en:

1. **MLService** (`backend/app/services/ml_service.py`)
   - Modelos de riesgo crediticio
   - Random Forest, XGBoost, Logistic Regression

2. **MLImpagoCuotasService** (`backend/app/services/ml_impago_cuotas_service.py`)
   - Modelos de predicción de impago de cuotas
   - Random Forest, Gradient Boosting

## 📦 Dependencias de scikit-learn

scikit-learn requiere:
- **numpy** >= 1.19.5 ✅ (instalado)
- **scipy** >= 1.6.0 ✅ (instalado 1.16.3)
- **joblib** >= 1.2.0 ✅ (instalado 1.5.2)
- **threadpoolctl** >= 3.1.0 ✅ (instalado 3.6.0)

## ⚠️ Notas Importantes

1. **Versión Específica:** Se usa `scikit-learn==1.6.1` para garantizar compatibilidad
2. **En Producción:** Se instala automáticamente desde `requirements.txt`
3. **Tamaño:** scikit-learn es una librería grande (~11 MB), puede tardar en instalar

## 🔍 Solución de Problemas

### Error: "No module named 'sklearn'"
```bash
pip install scikit-learn==1.6.1
```

### Error: "numpy not found"
```bash
pip install numpy
pip install scikit-learn==1.6.1
```

### Error en Windows: "Microsoft Visual C++ 14.0 is required"
- Instala "Microsoft C++ Build Tools" desde: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- O usa la versión precompilada: `pip install scikit-learn==1.6.1`

## 📚 Documentación

- **scikit-learn oficial:** https://scikit-learn.org/stable/
- **Versión 1.6.1:** https://scikit-learn.org/1.6/whats_new/v1.6.html

