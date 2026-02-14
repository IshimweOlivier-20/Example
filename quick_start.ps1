# IshemaLink API - Quick Start Testing Script
# Run this in PowerShell after pulling the repository

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "    ISHEMALINK API - FORMATIVE 2 QUICK START   " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python
Write-Host "[1/8] Checking Python installation..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "❌ Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Step 2: Create virtual environment
Write-Host ""
Write-Host "[2/8] Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "✅ Virtual environment already exists" -ForegroundColor Green
} else {
    python -m venv venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}

# Step 3: Activate virtual environment
Write-Host ""
Write-Host "[3/8] Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
Write-Host "✅ Virtual environment activated" -ForegroundColor Green

# Step 4: Install dependencies
Write-Host ""
Write-Host "[4/8] Installing dependencies..." -ForegroundColor Yellow
pip install -q -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Step 5: Generate encryption key
Write-Host ""
Write-Host "[5/8] Generating encryption key..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "✅ .env file already exists (skipping)" -ForegroundColor Green
} else {
    python generate_keys.py
    Write-Host "✅ Encryption key generated" -ForegroundColor Green
}

# Step 6: Run migrations
Write-Host ""
Write-Host "[6/8] Running database migrations..." -ForegroundColor Yellow
python manage.py makemigrations 2>&1 | Out-Null
python manage.py migrate
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Migrations completed" -ForegroundColor Green
} else {
    Write-Host "❌ Migration failed" -ForegroundColor Red
    exit 1
}

# Step 7: Run integration tests
Write-Host ""
Write-Host "[7/8] Running integration tests..." -ForegroundColor Yellow
python test_integration.py

# Step 8: Prompt for next action
Write-Host ""
Write-Host "[8/8] Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "           NEXT STEPS                          " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Option 1: Create superuser" -ForegroundColor Yellow
Write-Host "  python manage.py createsuperuser" -ForegroundColor White
Write-Host ""
Write-Host "Option 2: Start development server" -ForegroundColor Yellow
Write-Host "  python manage.py runserver" -ForegroundColor White
Write-Host ""
Write-Host "Option 3: View API documentation" -ForegroundColor Yellow
Write-Host "  Start server, then visit: http://127.0.0.1:8000/api/docs/" -ForegroundColor White
Write-Host ""
Write-Host "📄 Read INTEGRATION_COMPLETE.md for full testing guide" -ForegroundColor Cyan
Write-Host ""

# Keep shell open
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
