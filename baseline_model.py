"""
ProtonAI - Baseline Model
النموذج الأساسي للتنبؤ بجرعة العلاج بالبروتون
يربط جميع الوحدات السابقة في خط معالجة متكامل
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger("ProtonAI.BaselineModel")


class BaselineModel:
    """
    النموذج الأساسي لمنصة ProtonAI.
    يستخدم خوارزمية بسيطة (Linear Regression من الصفر) للتنبؤ بالجرعة.
    """

    def __init__(
        self,
        learning_rate: float = 0.01,
        epochs: int = 1000,
        random_seed: int = 42
    ):
        """
        تهيئة النموذج الأساسي.
        
        Args:
            learning_rate: معدل التعلم
            epochs: عدد دورات التدريب
            random_seed: البذرة العشوائية
        """
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.random_seed = random_seed
        self.weights: Optional[List[float]] = None
        self.bias: float = 0.0
        self.is_trained = False
        self.training_history: List[Dict[str, float]] = []
        
        logger.info(f"تم تهيئة النموذج الأساسي: lr={learning_rate}, epochs={epochs}")

    def _initialize_weights(self, n_features: int) -> None:
        """تهيئة الأوزان بشكل عشوائي"""
        import random
        random.seed(self.random_seed)
        self.weights = [random.uniform(-0.1, 0.1) for _ in range(n_features)]
        self.bias = 0.0

    def _predict_single(self, features: List[float]) -> float:
        """التنبؤ بقيمة واحدة"""
        if not self.weights:
            raise RuntimeError("النموذج لم يتم تدريبه بعد")
        
        prediction = self.bias
        for w, x in zip(self.weights, features):
            prediction += w * x
        return prediction

    def predict(self, data: List[Dict[str, Any]], feature_keys: List[str]) -> List[float]:
        """
        التنبؤ بمجموعة من البيانات.
        
        Args:
            data: قائمة القواميس
            feature_keys: المفاتيح المستخدمة كميزات
            
        Returns:
            List[float]: التوقعات
        """
        if not self.is_trained:
            raise RuntimeError("يجب تدريب النموذج أولاً")
        
        predictions = []
        for row in data:
            features = [float(row.get(key, 0.0)) for key in feature_keys]
            pred = self._predict_single(features)
            predictions.append(pred)
        
        logger.info(f"تم التنبؤ بـ {len(predictions)} قيمة")
        return predictions

    def _calculate_mse(self, predictions: List[float], targets: List[float]) -> float:
        """حساب متوسط مربع الخطأ (MSE)"""
        if len(predictions) != len(targets):
            raise ValueError("عدد التوقعات يجب أن يساوي عدد الأهداف")
        
        n = len(predictions)
        mse = sum((p - t) ** 2 for p, t in zip(predictions, targets)) / n
        return mse

    def _calculate_mae(self, predictions: List[float], targets: List[float]) -> float:
        """حساب متوسط الخطأ المطلق (MAE)"""
        n = len(predictions)
        mae = sum(abs(p - t) for p, t in zip(predictions, targets)) / n
        return mae

    def fit(
        self,
        train_data: List[Dict[str, Any]],
        feature_keys: List[str],
        target_key: str
    ) -> Dict[str, Any]:
        """
        تدريب النموذج باستخدام Gradient Descent.
        
        Args:
            train_data: بيانات التدريب
            feature_keys: المفاتيح المستخدمة كميزات
            target_key: المفتاح المستهدف للتنبؤ
            
        Returns:
            Dict[str, Any]: تاريخ التدريب
        """
        if not train_data:
            raise ValueError("بيانات التدريب فارغة")
        
        # تهيئة الأوزان
        self._initialize_weights(len(feature_keys))
        self.training_history = []
        
        # استخراج الميزات والأهداف
        X = []
        y = []
        for row in train_data:
            features = [float(row.get(key, 0.0)) for key in feature_keys]
            target = float(row.get(target_key, 0.0))
            X.append(features)
            y.append(target)
        
        # تدريب النموذج
        for epoch in range(self.epochs):
            # التنبؤ
            predictions = [self._predict_single(x) for x in X]
            
            # حساب الخطأ
            mse = self._calculate_mse(predictions, y)
            mae = self._calculate_mae(predictions, y)
            
            # حساب التدرجات (Gradients)
            n = len(X)
            dw = [0.0] * len(feature_keys)
            db = 0.0
            
            for i in range(n):
                error = predictions[i] - y[i]
                for j in range(len(feature_keys)):
                    dw[j] += error * X[i][j]
                db += error
            
            # تحديث الأوزان
            for j in range(len(feature_keys)):
                self.weights[j] -= self.learning_rate * (dw[j] / n)
            self.bias -= self.learning_rate * (db / n)
            
            # تسجيل التاريخ كل 100 دورة
            if epoch % 100 == 0:
                self.training_history.append({
                    "epoch": epoch,
                    "mse": mse,
                    "mae": mae
                })
        
        self.is_trained = True
        
        # التقييم النهائي
        final_predictions = [self._predict_single(x) for x in X]
        final_mse = self._calculate_mse(final_predictions, y)
        final_mae = self._calculate_mae(final_predictions, y)
        
        logger.info(f"تم تدريب النموذج: MSE={final_mse:.4f}, MAE={final_mae:.4f}")
        
        return {
            "final_mse": final_mse,
            "final_mae": final_mae,
            "epochs_completed": self.epochs,
            "training_samples": len(train_data)
        }

    def evaluate(
        self,
        test_data: List[Dict[str, Any]],
        feature_keys: List[str],
        target_key: str
    ) -> Dict[str, float]:
        """
        تقييم النموذج على بيانات الاختبار.
        
        Args:
            test_data: بيانات الاختبار
            feature_keys: المفاتيح المستخدمة كميزات
            target_key: المفتاح المستهدف
            
        Returns:
            Dict[str, float]: مقاييس التقييم
        """
        if not self.is_trained:
            raise RuntimeError("يجب تدريب النموذج أولاً")
        
        # التنبؤ
        predictions = self.predict(test_data, feature_keys)
        
        # استخراج الأهداف الحقيقية
        targets = [float(row.get(target_key, 0.0)) for row in test_data]
        
        # حساب المقاييس
        mse = self._calculate_mse(predictions, targets)
        mae = self._calculate_mae(predictions, targets)
        
        # حساب R² (معامل التحديد)
        mean_target = sum(targets) / len(targets)
        ss_tot = sum((t - mean_target) ** 2 for t in targets)
        ss_res = sum((t - p) ** 2 for t, p in zip(targets, predictions))
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        metrics = {
            "mse": mse,
            "mae": mae,
            "r2_score": r2,
            "test_samples": len(test_data)
        }
        
        logger.info(f"تقييم النموذج: MSE={mse:.4f}, MAE={mae:.4f}, R²={r2:.4f}")
        
        return metrics

    def save_model(self, model_path: str | Path) -> None:
        """حفظ النموذج في ملف JSON"""
        model_path = Path(model_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            "weights": self.weights,
            "bias": self.bias,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "random_seed": self.random_seed,
            "is_trained": self.is_trained,
            "training_history": self.training_history,
            "saved_at": datetime.now().isoformat()
        }
        
        with open(model_path, 'w', encoding='utf-8') as f:
            json.dump(model_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"تم حفظ النموذج في: {model_path}")

    def load_model(self, model_path: str | Path) -> None:
        """تحميل النموذج من ملف JSON"""
        model_path = Path(model_path)
        
        if not model_path.exists():
            raise FileNotFoundError(f"ملف النموذج غير موجود: {model_path}")
        
        with open(model_path, 'r', encoding='utf-8') as f:
            model_data = json.load(f)
        
        self.weights = model_data["weights"]
        self.bias = model_data["bias"]
        self.learning_rate = model_data["learning_rate"]
        self.epochs = model_data["epochs"]
        self.random_seed = model_data["random_seed"]
        self.is_trained = model_data["is_trained"]
        self.training_history = model_data.get("training_history", [])
        
        logger.info(f"تم تحميل النموذج من: {model_path}")

    def get_model_info(self) -> Dict[str, Any]:
        """الحصول على معلومات النموذج"""
        return {
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "random_seed": self.random_seed,
            "is_trained": self.is_trained,
            "weights_count": len(self.weights) if self.weights else 0,
            "bias": self.bias,
            "training_history_length": len(self.training_history)
      }
