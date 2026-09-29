#!/usr/bin/env bash
# P6-S4: fresh-environment bootstrap (documented, reproducible)
set -euo pipefail
pip install --no-cache-dir numpy pydicom scipy scikit-learn pytest
pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
pip install --no-cache-dir onnx onnxruntime onnxscript
echo "environment ready"
