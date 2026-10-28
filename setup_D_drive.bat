@echo off
echo === Setting up project in D: drive ===
D:
cd \
if not exist D:\myproject mkdir D:\myproject
cd D:\myproject

echo 1. Creating venv...
python -m venv venv

echo 2. Installing packages...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

echo 3. Checking tools...
git --version
python --version
docker --version
docker compose version
kubectl version --client
node --version

echo 4. Starting Postgres and Elasticsearch...
docker compose up -d
timeout /t 5
docker ps

echo === DONE ===
echo Project is in D:\myproject
pause
