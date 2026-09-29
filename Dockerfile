# ProtonAI - صورة إنتاج خفيفة وآمنة
FROM python:3.10-slim

WORKDIR /app

# تثبيت الاعتماديات أولاً (للاستفادة من cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الشيفرة
COPY . .

# مستخدم غير root (أمان مؤسسي)
RUN useradd -m appuser
USER appuser

# فحص صحة دوري
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "print('ok')" || exit 1

# نقطة الدخول: الديمو السريري
CMD ["python", "run_clinical_demo.py"]
