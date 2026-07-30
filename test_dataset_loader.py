"""
ProtonAI - Test Dataset Loader
اختبارات محمّل مجموعات البيانات
"""

import json
import pytest
from dataset_loader import DatasetLoader


def _write_csv(path, text):
    path.write_text(text.strip() + "\n", encoding="utf-8")


@pytest.fixture
def loader():
    return DatasetLoader(feature_columns=["a", "b"], target_column="y")


@pytest.fixture
def csv_file(tmp_path):
    f = tmp_path / "data.csv"
    _write_csv(f, """a,b,y
1,2,0
3,4,1
5,6,0""")
    return f


class TestLoad:
    def test_load_csv(self, loader, csv_file):
        rows = loader.load(csv_file)
        assert len(rows) == 3
        assert rows[0]["a"] == "1"

    def test_load_json(self, loader, tmp_path):
        f = tmp_path / "data.json"
        f.write_text(
            json.dumps([{"a": 1, "b": 2, "y": 0}, {"a": 3, "b": 4, "y": 1}]),
            encoding="utf-8",
        )
        rows = loader.load(f)
        assert len(rows) == 2

    def test_load_missing_file(self, loader, tmp_path):
        with pytest.raises(FileNotFoundError):
            loader.load(tmp_path / "nope.csv")

    def test_unsupported_format(self, loader, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("hi", encoding="utf-8")
        with pytest.raises(ValueError):
            loader.load(f)


class TestExtract:
    def test_extract_shapes(self, loader, csv_file):
        X, y = loader.extract(loader.load(csv_file))
        assert len(X) == 3
        assert all(len(row) == 2 for row in X)
        assert len(y) == 3

    def test_extract_values(self, loader, csv_file):
        X, y = loader.extract(loader.load(csv_file))
        assert X[0] == [1.0, 2.0]
        assert y[1] == 1.0

    def test_drop_missing(self, tmp_path):
        f = tmp_path / "m.csv"
        _write_csv(f, """a,b,y
1,2,0
,4,1
5,6,0""")
        ld = DatasetLoader(["a", "b"], "y", missing_strategy="drop")
        X, y = ld.extract(ld.load(f))
        assert len(X) == 2

    def test_fill_mean(self, tmp_path):
        f = tmp_path / "m.csv"
        _write_csv(f, """a,b,y
1,2,0
3,4,1
,6,0""")
        ld = DatasetLoader(["a", "b"], "y", missing_strategy="fill_mean")
        X, y = ld.extract(ld.load(f))
        assert len(X) == 3
        assert X[2][0] == 2.0

    def test_missing_target_skipped(self, tmp_path):
        f = tmp_path / "t.csv"
        _write_csv(f, """a,b,y
1,2,0
3,4,""")
        ld = DatasetLoader(["a", "b"], "y")
        X, y = ld.extract(ld.load(f))
        assert len(X) == 1


class TestConfig:
    def test_invalid_strategy_raises(self):
        with pytest.raises(ValueError):
            DatasetLoader(["a"], "y", missing_strategy="weird")

    def test_empty_features_raises(self):
        with pytest.raises(ValueError):
            DatasetLoader([], "y")


class TestSummary:
    def test_summary_keys(self, loader, csv_file):
        s = loader.summary(loader.load(csv_file))
        assert s["rows"] == 3
        assert s["feature_columns"] == ["a", "b"]
        assert s["target_column"] == "y"
