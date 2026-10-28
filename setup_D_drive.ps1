# Setup script for D: drive - Run in PowerShell
Write-Host "=== Setting up project in D: drive ===" -ForegroundColor Green

# Go to D:
Set-Location D:\
if (!(Test-Path "D:\myproject")) {
    New-Item -ItemType Directory -Path "D:\myproject" | Out-Null
    Write-Host "Created D:\myproject"
}
Set-Location D:\myproject

# 1. Create venv
Write-Host "`n1. Creating venv..." -ForegroundColor Yellow
python -m venv venv

# 2. Activate and install
Write-Host "2. Installing packages (this may take 2-3 mins)..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

# 3. Check tools
Write-Host "`n3. Checking tools..." -ForegroundColor Yellow
git --version
python --version
docker --version
docker compose version
kubectl version --client
node --version

# 4. Start Docker containers
Write-Host "`n4. Starting Postgres and Elasticsearch..." -ForegroundColor Yellow
docker compose up -d
Start-Sleep -Seconds 5
docker ps

Write-Host "`n=== DONE ===" -ForegroundColor Green
Write-Host "Project is in D:\myproject"
Write-Host "To activate again next time, run:"
Write-Host "  Set-Location D:\myproject"
Write-Host "  .\venv\Scripts\Activate.ps1"
Write-Host "  docker compose up -d"
Write-Host "Test Elasticsearch: http://localhost:9200"
