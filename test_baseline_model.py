"""
ProtonAI - Test Baseline Model (Fixed Version)
"""

import pytest
import tempfile
from pathlib import Path
from baseline_model import BaselineModel


@pytest.fixture
def sample_training_data():
    return [
        {"age": 40, "tumor_volume": 100, "dose_gy": 60.0},
        {"age": 50, "tumor_volume": 150, "dose_gy": 65.0},
        {"age": 60, "tumor_volume": 200, "dose_gy": 70.0},
        {"age": 70, "tumor_volume": 250, "dose_gy": 75.0},
        {"age": 80, "tumor_volume": 300, "dose_gy": 80.0},
    ]


@pytest.fixture
def sample_test_data():
    return [
        {"age": 45, "tumor_volume": 120, "dose_gy": 62.0},
        {"age": 55, "tumor_volume": 180, "dose_gy": 68.0},
    ]


@pytest.fixture
def trained_model(sample_training_data):
    model = BaselineModel(learning_rate=0.001, epochs=100, random_seed=42)
    model.fit(
        train_data=sample_training_data,
        feature_keys=["age", "tumor_volume"],
        target_key="dose_gy"
    )
    return model


class TestBaselineModel:
    def test_initialization(self):
        model = BaselineModel(learning_rate=0.001, epochs=100, random_seed=42)
        assert model.learning_rate == 0.001
        assert model.epochs == 100
        assert model.is_trained is False

    def test_fit_trains_model(self, sample_training_data):
        model = BaselineModel(learning_rate=0.001, epochs=100)
        result = model.fit(
            train_data=sample_training_data,
            feature_keys=["age", "tumor_volume"],
            target_key="dose_gy"
        )
        
        assert model.is_trained is True
        assert model.weights is not None
        assert len(model.weights) == 2
        assert "final_mse" in result

    def test_fit_empty_data_raises_error(self):
        model = BaselineModel()
        with pytest.raises(ValueError):
            model.fit(train_data=[], feature_keys=["age"], target_key="dose_gy")

    def test_predict_before_training_raises_error(self, sample_training_data):
        model = BaselineModel()
        with pytest.raises(RuntimeError):
            model.predict(sample_training_data, ["age"])

    def test_predict_returns_correct_length(self, trained_model, sample_test_data):
        predictions = trained_model.predict(
            sample_test_data, 
            feature_keys=["age", "tumor_volume"]
        )
        assert len(predictions) == len(sample_test_data)

    def test_predict_returns_floats(self, trained_model, sample_test_data):
        predictions = trained_model.predict(
            sample_test_data, 
            feature_keys=["age", "tumor_volume"]
        )
        for pred in predictions:
            assert isinstance(pred, float)

    def test_evaluate_returns_metrics(self, trained_model, sample_test_data):
        metrics = trained_model.evaluate(
            test_data=sample_test_data,
            feature_keys=["age", "tumor_volume"],
            target_key="dose_gy"
        )
        
        assert "mse" in metrics
        assert "mae" in metrics
        assert "r2_score" in metrics
        assert metrics["test_samples"] == 2

    def test_evaluate_before_training_raises_error(self, sample_test_data):
        model = BaselineModel()
        with pytest.raises(RuntimeError):
            model.evaluate(
                test_data=sample_test_data,
                feature_keys=["age"],
                target_key="dose_gy"
            )

    def test_save_and_load_model(self, trained_model):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            trained_model.save_model(temp_path)
            assert temp_path.exists()
            
            new_model = BaselineModel()
            new_model.load_model(temp_path)
            
            assert new_model.is_trained is True
            assert new_model.weights == trained_model.weights
        finally:
            temp_path.unlink()

    def test_load_nonexistent_file_raises_error(self):
        model = BaselineModel()
        with pytest.raises(FileNotFoundError):
            model.load_model("nonexistent_model.json")

    def test_training_history_recorded(self, sample_training_data):
        model = BaselineModel(learning_rate=0.001, epochs=100)
        model.fit(
            train_data=sample_training_data,
            feature_keys=["age", "tumor_volume"],
            target_key="dose_gy"
        )
        
        assert len(model.training_history) > 0
        assert "epoch" in model.training_history[0]

    def test_get_model_info(self, trained_model):
        info = trained_model.get_model_info()
        
        assert "learning_rate" in info
        assert "is_trained" in info
        assert info["is_trained"] is True
        assert info["weights_count"] == 2

    def test_different_learning_rates(self, sample_training_data):
        model_slow = BaselineModel(learning_rate=0.0001, epochs=50)
        model_fast = BaselineModel(learning_rate=0.001, epochs=50)
        
        model_slow.fit(sample_training_data, ["age", "tumor_volume"], "dose_gy")
        model_fast.fit(sample_training_data, ["age", "tumor_volume"], "dose_gy")
        
        assert model_slow.is_trained is True
        assert model_fast.is_trained is True

    def test_predict_consistency(self, trained_model, sample_test_data):
        pred1 = trained_model.predict(sample_test_data, ["age", "tumor_volume"])
        pred2 = trained_model.predict(sample_test_data, ["age", "tumor_volume"])
        
        assert pred1 == pred2
