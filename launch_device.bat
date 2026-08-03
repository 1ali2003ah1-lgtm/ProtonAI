@echo off
REM ProtonAI - مشغّل الجهاز (Windows): ثبّت وشغّل بأمر واحد
cd /d %~dp0

if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat

echo Installing dependencies (includes torch and Streamlit)...
pip install -r requirements-device.txt

echo Running all demos...
python run_device_all.py

echo Opening Streamlit dashboard...
streamlit run streamlit_dashboard.py
