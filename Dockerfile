# P6-S1: hardened CPU inference image (ADR-008)
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir numpy pydicom scipy scikit-learn \
    && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir onnxruntime
RUN useradd --create-home app && chown -R app /app
USER app
HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import onnxruntime" || exit 1
CMD ["python", "-c", "print('ProtonAI inference image ready')"]
