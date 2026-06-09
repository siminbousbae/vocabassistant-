# Windows Setup Guide

## Problem
Some Python packages (like pydantic-core) require C++ compilation on Windows, which needs Visual Studio Build Tools.

## Solution 1: Install Pre-built Wheels (Easiest)

```bash
# 1. Upgrade pip first
python -m pip install --upgrade pip

# 2. Install pre-built wheels (no compilation needed)
pip install fastapi uvicorn sqlalchemy pydantic==2.9.0 pydantic-settings python-dotenv
pip install python-telegram-bot httpx tavily-python dashscope apscheduler pytest
```

## Solution 2: Install Visual Studio Build Tools (If above fails)

1. Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Install "Desktop development with C++" workload
3. Retry: `pip install -r requirements.txt`

## Solution 3: Use WSL (Windows Subsystem for Linux)

```bash
# In WSL terminal
sudo apt update
sudo apt install python3-pip
pip install -r requirements.txt
```

## Solution 4: Use Conda (Recommended for Windows)

```bash
# Install conda first: https://docs.conda.io/en/latest/miniconda.html

# Create environment
conda create -n vocab python=3.11
conda activate vocab

# Install packages (conda handles compiled dependencies)
conda install -c conda-forge fastapi uvicorn sqlalchemy pydantic
pip install python-telegram-bot tavily-python dashscope apscheduler
```

## Quick Test After Installation

```bash
python test_simple.py
```

## If Still Having Issues

Try installing one by one:
```bash
pip install fastapi
pip install uvicorn
pip install sqlalchemy
pip install pydantic==2.9.0
pip install pydantic-settings
pip install python-dotenv
pip install python-telegram-bot
pip install tavily-python
pip install dashscope
pip install apscheduler
```

## Verify Installation

```python
python -c "import fastapi; import sqlalchemy; import pydantic; print('All OK!')"
```
