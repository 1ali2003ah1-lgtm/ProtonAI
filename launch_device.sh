#!/usr/bin/env bash
# ProtonAI - مشغّل الجهاز (Mac/Linux): ثبّت وشغّل بأمر واحد
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "🔧 إنشاء بيئة افتراضية..."
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "📦 تثبيت التبعيات (يشمل torch وStreamlit)..."
pip install -r requirements-device.txt

echo "🏃 تشغيل كل المنصة بتقرير واحد..."
python run_device_all.py

echo "📊 فتح لوحة Streamlit الحية بالمتصفح..."
streamlit run streamlit_dashboard.py
