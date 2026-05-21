#!/bin/bash
##############################################################################
# AIJS Platform - Automated Contabo Deployment Script (UPDATED)
# Uses manual database: aijs_platform with user rvd024
# Fixes: Playwright install, OpenRouter API, .env setup
#
##############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

APP_DIR="/root/AIJS-platform"
REPO_URL="https://github.com/ravinder024/AIJS-platform.git"
DB_USER="rvd024"
DB_NAME="aijs_platform"
LOG_FILE="/var/log/aijs-deployment.log"

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$LOG_FILE"
}

# System Update
log "Step 1: Updating system packages..."
apt update -qq || error "Failed to update package list"
apt upgrade -y -qq || error "Failed to upgrade packages"
success "System packages updated"

# Install Dependencies
log "Step 2: Installing required dependencies..."
apt install -y -qq \
    git python3 python3-pip python3-venv postgresql postgresql-contrib \
    postgresql-client curl wget nano build-essential libssl-dev libffi-dev \
    python3-dev 2>&1 | grep -v "^Reading\|^Building" || true
success "Dependencies installed"
python3 --version
psql --version

# Clone Repository
log "Step 3: Cloning repository..."
mkdir -p "$APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
    log "Repository already exists, updating..."
    cd "$APP_DIR"
    git pull origin main || error "Failed to pull from repository"
else
    git clone "$REPO_URL" "$APP_DIR" || error "Failed to clone repository"
fi
success "Repository cloned/updated: $APP_DIR"

# Setup Python Environment
log "Step 4: Setting up Python virtual environment..."
cd "$APP_DIR"
python3 -m venv .venv || error "Failed to create virtual environment"
source .venv/bin/activate || error "Failed to activate virtual environment"
pip install --upgrade pip setuptools wheel -q || error "Failed to upgrade pip"

log "Installing Python dependencies..."
pip install -r requirements.txt -q || error "Failed to install requirements"

log "Installing Playwright browsers..."
python -m playwright install chromium || error "Failed to install Playwright"
success "Python environment configured"

# PostgreSQL Verification
log "Step 5: Verifying PostgreSQL database..."
systemctl start postgresql || error "Failed to start PostgreSQL"
systemctl enable postgresql || error "Failed to enable PostgreSQL"

if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    log "⚠️  Database $DB_NAME not found. Creating it now..."
    sudo -u postgres psql << EOF || error "Failed to create database"
CREATE USER IF NOT EXISTS $DB_USER WITH PASSWORD 'temp_password';
CREATE DATABASE $DB_NAME OWNER $DB_USER;
ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF
else
    success "Database $DB_NAME already exists"
fi

# Create .env File
log "Step 6: Creating .env configuration file..."
cd "$APP_DIR"

# Only create .env if it doesn't already have real credentials
if [ -f .env ] && ! grep -q 'YOUR_DB_PASSWORD_HERE' .env && ! grep -q 'YOUR_OPENROUTER_KEY_HERE' .env; then
    log ".env already has real credentials, skipping overwrite"
    success ".env file already configured"
else
    [ -f .env ] && cp .env .env.backup && log "⚠️  Backed up existing .env to .env.backup"

    cat > .env << 'ENVEOF'
APP_ENV=production

# Database Configuration -- UPDATE WITH REAL PASSWORD
DATABASE_URL=postgresql+psycopg2://rvd024:YOUR_DB_PASSWORD_HERE@localhost:5432/aijs_platform

# OpenRouter API -- UPDATE WITH REAL KEY
OPENROUTER_API_KEY=YOUR_OPENROUTER_KEY_HERE
OPENROUTER_MODEL=openrouter/free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Scheduler
DAILY_RUN_TIME=08:00
TZ=UTC

# Production scale
MAX_JOBS_PER_RUN=500
MAX_COMPANIES_PER_RUN=200
MAX_CONTACTS_PER_COMPANY=10

# Feature Flags
ENABLE_SCRAPEGRAPH_AI=true
ENABLE_COMPANY_ENRICHMENT=true
ENVEOF

    chmod 600 .env
    success ".env template created"
    log "⚠️  IMPORTANT: Run 'nano $APP_DIR/.env' and fill in DATABASE_URL password and OPENROUTER_API_KEY!"
    log "Then re-run: bash deploy.sh"
    exit 0
fi

# Initialize Database Schema
log "Step 7: Initializing database schema..."
source .venv/bin/activate
python init_db.py >> "$LOG_FILE" 2>&1 || error "Failed to initialize database"
success "Database schema initialized"

# Run Tests
log "Step 8: Running test suite..."
python test_enhanced_scrapers.py >> "$LOG_FILE" 2>&1 || log "⚠️  Some tests failed but continuing..."
success "Test suite completed"

# Setup Systemd Services
log "Step 9: Setting up systemd services..."
mkdir -p /var/log/aijs-platform
chmod 755 /var/log/aijs-platform

cat > /etc/systemd/system/aijs-scraper.service << 'SERVICEEOF'
[Unit]
Description=AIJS Platform Scraper
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/AIJS-platform
Environment="PATH=/root/AIJS-platform/.venv/bin"
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/root/AIJS-platform/.env
ExecStart=/root/AIJS-platform/.venv/bin/python scheduler_runner.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

cat > /etc/systemd/system/aijs-web.service << 'SERVICEEOF'
[Unit]
Description=AIJS Platform Web
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/AIJS-platform
Environment="PATH=/root/AIJS-platform/.venv/bin"
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/root/AIJS-platform/.env
ExecStart=/root/AIJS-platform/.venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload
systemctl enable aijs-scraper aijs-web || true
success "Systemd services configured"

# Final Verification
log "Step 10: Final verification..."
source .venv/bin/activate
python3 -c "from db import DATABASE_URL; print('✅ DB URL:', DATABASE_URL)" || error "Failed"
python3 -c "from models import Job, Company, Contact; print('✅ Models loaded')" || error "Failed"
success "All verifications passed ✅"

echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ DEPLOYMENT COMPLETED!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env with your rvd024 password:"
echo "   nano /root/AIJS-platform/.env"
echo ""
echo "2. Start services:"
echo "   systemctl start aijs-scraper"
echo "   systemctl start aijs-web"
echo ""
echo "3. Check status:"
echo "   systemctl status aijs-scraper"
echo "   systemctl status aijs-web"