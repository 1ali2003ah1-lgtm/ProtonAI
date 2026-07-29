"""
ProtonAI - Baseline Model
النموذج الأساسي للتنبؤ بجرعة العلاج بالبروتون
مع تطبيع تلقائي وحماية من Overflow
"""

import logging
import json
import statistics
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from copy import deepcopy

logger = logging.getLogger("ProtonAI.BaselineModel")


class BaselineModel:
    """
    النموذج الأساسي لمنصة ProtonAI.
    يستخدم Linear Regression مع Gradient Descent + تطبيع تلقائي.
    """

    def __init__(
        self,
        learning_rate: float = 0.0001,
        epochs: int = 100,
        random_seed: int = 42
    ):
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.random_seed = random_seed
        self.weights: Optional[List[float]] = None
        self.bias: float = 0.0
        self.is_trained = False
        self.training_history: List[Dict[str, float]] = []
        
        # للتطبيع التلقائي
        self.feature_means: Dict[str, float] = {}
        self.feature_stds: Dict[str, float] = {}
        self.target_mean: float = 0.0
        self.target_std: float = 1.0
        
        logger.info(f"تم تهيئة النموذج: lr={learning_rate}, epochs={epochs}")

    def _normalize_features(self, data: List[Dict[str, Any]], feature_keys: List[str]) -> List[Dict[str, Any]]:
        """تطبيع الميزات باستخدام Z-Score"""
        normalized = deepcopy(data)
        
        for key in feature_keys:
            values = [float(row[key]) for row in data if key in row]
            if not values:
                continue
            
            mean = statistics.mean(values)
            std = statistics.pstdev(values) if len(values) > 1 else 1.0
            if std == 0:
                std = 1.0
            
            self.feature_means[key] = mean
            self.feature_stds[key] = std
            
            for row in normalized:
                if key in row:
                    row[key] = (float(row[key]) - mean) / std
        
        return normalized

    def _normalize_target(self, data: List[Dict[str, Any]], target_key: str) -> List[Dict[str, Any]]:
        """تطبيع الهدف"""
        normalized = deepcopy(data)
        values = [float(row[target_key]) for row in data if target_key in row]
        
        self.target_mean = statistics.mean(values)
        self.target_std = statistics.pstdev(values) if len(values) > 1 else 1.0
        if self.target_std == 0:
            self.target_std = 1.0
        
        for row in normalized:
            if target_key in row:
                row[target_key] = (float(row[target_key]) - self.target_mean) / self.target_std
        
        return normalized

    def _denormalize_prediction(self, normalized_pred: float) -> float:
        """إعادة التنبؤ للقيمة الأصلية"""
        return normalized_pred * self.target_std + self.target_mean

    def _initialize_weights(self, n_features: int) -> None:
        """تهيئة الأوزان بشكل عشوائي صغير"""
        import random
        random.seed(self.random_seed)
        self.weights = [random.uniform(-0.01, 0.01) for _ in range(n_features)]
        self.bias = 0.0

    def _predict_single(self, features: List[float]) -> float:
        """التنبؤ بقيمة واحدة"""
        if not self.weights:
            raise RuntimeError("النموذج لم يتم تدريبه بعد")
        
        prediction = self.bias
        for w, x in zip(self.weights, features):
            prediction += w * x
        
        # حماية من Overflow
        if abs(prediction) > 1e10:
            prediction = 1e10 if prediction > 0 else -1e10
        
        return prediction

    def predict(self, data: List[Dict[str, Any]], feature_keys: List[str]) -> List[float]:
        """التنبؤ بمجموعة من البيانات"""
        if not self.is_trained:
            raise RuntimeError("يجب تدريب النموذج أولاً")
        
        # تطبيع البيانات المدخلة
        normalized_data = self._normalize_features(data, feature_keys)
        
        predictions = []
        for row in normalized_data:
            features = [float(row.get(key, 0.0)) for key in feature_keys]
            normalized_pred = self._predict_single(features)
            # إعادة للقيمة الأصلية
            pred = self._denormalize_prediction(normalized_pred)
            predictions.append(pred)
        
        logger.info(f"تم التنبؤ بـ {len(predictions)} قيمة")
        return predictions

    def _calculate_mse(self, predictions: List[float], targets: List[float]) -> float:
        """حساب متوسط مربع الخطأ (MSE) مع حماية من Overflow"""
        if len(predictions) != len(targets):
            raise ValueError("عدد التوقعات يجب أن يساوي عدد الأهداف")
        
        n = len(predictions)
        total_error = 0.0
        
        for p, t in zip(predictions, targets):
            error = p - t
            # حماية من Overflow
            if abs(error) > 1e6:
                error = 1e6 if error > 0 else -1e6
            total_error += error ** 2
        
        mse = total_error / n
        return mse

    def _calculate_mae(self, predictions: List[float], targets: List[float]) -> float:
        """حساب متوسط الخطأ المطلق (MAE)"""
        n = len(predictions)
        total_error = 0.0
        
        for p, t in zip(predictions, targets):
            error = abs(p - t)
            if error > 1e6:
                error = 1e6
            total_error += error
        
        return total_error / n

    def fit(
        self,
        train_data: List[Dict[str, Any]],
        feature_keys: List[str],
        target_key: str
    ) -> Dict[str, Any]:
        """تدريب النموذج مع تطبيع تلقائي"""
        if not train_data:
            raise ValueError("بيانات التدريب فارغة")
        
        # تطبيع البيانات
        normalized_data = self._normalize_features(train_data, feature_keys)
        normalized_data = self._normalize_target(normalized_data, target_key)
        
        # تهيئة الأوزان
        self._initialize_weights(len(feature_keys))
        self.training_history = []
        
        # استخراج الميزات والأهداف (المُطبّعة)
        X = []
        y = []
        for row in normalized_data:
            features = [float(row.get(key, 0.0)) for key in feature_keys]
            target = float(row.get(target_key, 0.0))
            X.append(features)
            y.append(target)
        
        # تدريب النموذج
        for epoch in range(self.epochs):
            predictions = [self._predict_single(x) for x in X]
            
            mse = self._calculate_mse(predictions, y)
            mae = self._calculate_mae(predictions, y)
            
            # حساب التدرجات
            n = len(X)
            dw = [0.0] * len(feature_keys)
            db = 0.0
            
            for i in range(n):
                error = predictions[i] - y[i]
                # حماية من Overflow في التدرجات
                if abs(error) > 1e6:
                    error = 1e6 if error > 0 else -1e6
                
                for j in range(len(feature_keys)):
                    dw[j] += error * X[i][j]
                db += error
            
            # تحديث الأوزان مع Clipping
            for j in range(len(feature_keys)):
                gradient = dw[j] / n
                if abs(gradient) > 1.0:
                    gradient = 1.0 if gradient > 0 else -1.0
                self.weights[j] -= self.learning_rate * gradient
            
            db_grad = db / n
            if abs(db_grad) > 1.0:
                db_grad = 1.0 if db_grad > 0 else -1.0
            self.bias -= self.learning_rate * db_grad
            
            # تسجيل التاريخ كل 10 دورات
            if epoch % 10 == 0:
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
        
        logger.info(f"تم التدريب: MSE={final_mse:.6f}, MAE={final_mae:.6f}")
        
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
        """تقييم النموذج"""
        if not self.is_trained:
            raise RuntimeError("يجب تدريب النموذج أولاً")
        
        predictions = self.predict(test_data, feature_keys)
        targets = [float(row.get(target_key, 0.0)) for row in test_data]
        
        mse = self._calculate_mse(predictions, targets)
        mae = self._calculate_mae(predictions, targets)
        
        # حساب R²
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
        
        logger.info(f"التقييم: MSE={mse:.4f}, MAE={mae:.4f}, R²={r2:.4f}")
        return metrics

    def save_model(self, model_path: str | Path) -> None:
        """حفظ النموذج"""
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
            "feature_means": self.feature_means,
            "feature_stds": self.feature_stds,
            "target_mean": self.target_mean,
            "target_std": self.target_std,
            "saved_at": datetime.now().isoformat()
        }
        
        with open(model_path, 'w', encoding='utf-8') as f:
            json.dump(model_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"تم حفظ النموذج في: {model_path}")

    def load_model(self, model_path: str | Path) -> None:
        """تحميل النموذج"""
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
        self.feature_means = model_data.get("feature_means", {})
        self.feature_stds = model_data.get("feature_stds", {})
        self.target_mean = model_data.get("target_mean", 0.0)
        self.target_std = model_data.get("target_std", 1.0)
        
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
