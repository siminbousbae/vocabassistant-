@echo off
echo ==========================================
echo AI Vocabulary Assistant - Windows Setup
echo ==========================================
echo.

REM Upgrade pip
echo [1/3] Upgrading pip...
python -m pip install --upgrade pip

REM Install packages one by one (safer for Windows)
echo [2/3] Installing packages...
echo.

echo Installing fastapi...
pip install fastapi==0.115.0

echo Installing uvicorn...
pip install uvicorn==0.32.0

echo Installing sqlalchemy...
pip install sqlalchemy==2.0.36

echo Installing pydantic...
pip install pydantic==2.9.0

echo Installing pydantic-settings...
pip install pydantic-settings==2.6.0

echo Installing python-dotenv...
pip install python-dotenv==1.0.1

echo Installing httpx...
pip install httpx==0.27.0

echo Installing python-telegram-bot...
pip install python-telegram-bot==21.9

echo Installing tavily...
pip install tavily-python==0.5.0

echo Installing dashscope...
pip install dashscope==1.20.0

echo Installing apscheduler...
pip install APScheduler==3.10.4

echo Installing pytest...
pip install pytest==8.3.0

echo.
echo [3/3] Testing installation...
python -c "import fastapi; import sqlalchemy; import pydantic; print('All packages installed successfully!')"

echo.
echo ==========================================
echo Setup complete! Run: python test_simple.py
echo ==========================================
pause
