#!/bin/bash
##############################################################################
# AIJS Platform - Automated Contabo Deployment Script
# 
# This script automates the entire setup process on Contabo VPS
# Tested on: Ubuntu 20.04 LTS, Ubuntu 22.04 LTS
#
# Usage: 
#   curl -sSL https://raw.githubusercontent.com/ravinder024/AIJS-platform/main/deploy.sh | bash
#   OR
#   bash deploy.sh
#
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/var/www/AIJS-platform"
REPO_URL="https://github.com/ravinder024/AIJS-platform.git"
DB_USER="job_agent"
DB_NAME="job_agent"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -base64 32)}"  # Generate random password if not set
LOG_FILE="/var/log/aijs-deployment.log"

# Log function
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

##############################################################################
# Step 1: System Update
##############################################################################
step_system_update() {
    log "Step 1: Updating system packages..."
    apt update -qq || error "Failed to update package list"
    apt upgrade -y -qq || error "Failed to upgrade packages"
    success "System packages updated"
}

##############################################################################
# Step 2: Install Dependencies
##############################################################################
step_install_deps() {
    log "Step 2: Installing required dependencies..."
    
    apt install -y -qq \
        git \
        python3.11 \
        python3-pip \
        python3-venv \
        postgresql \
        postgresql-contrib \
        postgresql-client \
        curl \
        wget \
        nano \
        htop \
        build-essential \
        libssl-dev \
        libffi-dev \
        python3-dev \
        2>&1 | grep -v "^Reading\|^Building" || error "Failed to install dependencies"
    
    success "Dependencies installed"
    
    # Verify versions
    log "Verifying installations..."
    python3 --version
    psql --version
}

##############################################################################
# Step 3: Clone Repository
##############################################################################
step_clone_repo() {
    log "Step 3: Cloning repository..."
    
    mkdir -p $(dirname "$APP_DIR")
    
    if [ -d "$APP_DIR/.git" ]; then
        log "Repository already exists, updating..."
        cd "$APP_DIR"
        git pull origin main || error "Failed to pull from repository"
    else
        git clone "$REPO_URL" "$APP_DIR" || error "Failed to clone repository"
    fi
    
    success "Repository cloned/updated: $APP_DIR"
}

##############################################################################
# Step 4: Setup Python Environment
##############################################################################
step_python_env() {
    log "Step 4: Setting up Python virtual environment..."
    
    cd "$APP_DIR"
    
    python3 -m venv .venv || error "Failed to create virtual environment"
    source .venv/bin/activate || error "Failed to activate virtual environment"
    
    pip install --upgrade pip setuptools wheel -q || error "Failed to upgrade pip"
    
    log "Installing Python dependencies..."
    pip install -r requirements.txt -q || error "Failed to install requirements"
    
    log "Installing Playwright browsers..."
    python -m playwright install chromium -q || error "Failed to install Playwright"
    
    success "Python environment configured"
}

##############################################################################
# Step 5: PostgreSQL Setup
##############################################################################
step_postgres_setup() {
    log "Step 5: Setting up PostgreSQL database..."
    
    # Start PostgreSQL
    systemctl start postgresql || error "Failed to start PostgreSQL"
    systemctl enable postgresql || error "Failed to enable PostgreSQL"
    
    # Create database and user
    sudo -u postgres psql << EOF || error "Failed to create database user"
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
CREATE DATABASE $DB_NAME OWNER $DB_USER;
ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
ALTER ROLE $DB_USER SET default_transaction_deferrable TO on;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF
    
    success "PostgreSQL database configured"
    log "Database: $DB_NAME | User: $DB_USER | Password: (saved in .env)"
}

##############################################################################
# Step 6: Create .env File
##############################################################################
step_create_env() {
    log "Step 6: Creating .env configuration file..."
    
    cd "$APP_DIR"
    
    if [ -f .env ]; then
        log "⚠️  .env file already exists, backing up to .env.backup"
        cp .env .env.backup
    fi
    
    # Generate Flask secret key
    SECRET_KEY=$(python3 -c 'import os; print(os.urandom(32).hex())')
    
    cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql+psycopg2://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME

# API Keys (UPDATE THESE)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_SHEETS_API_KEY=your_google_sheets_key_here

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=0
SECRET_KEY=$SECRET_KEY

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/aijs-platform/app.log

# Feature Flags
ENABLE_SCRAPEGRAPH_AI=true
ENABLE_COMPANY_ENRICHMENT=true
MAX_JOBS_PER_RUN=100
REQUEST_TIMEOUT=30

# Rate Limiting
REQUEST_DELAY_MIN=2
REQUEST_DELAY_MAX=5
EOF
    
    chmod 600 .env
    success ".env file created (update API keys manually)"
}

##############################################################################
# Step 7: Initialize Database Schema
##############################################################################
step_init_db() {
    log "Step 7: Initializing database schema..."
    
    cd "$APP_DIR"
    source .venv/bin/activate
    
    python run_migration.py >> "$LOG_FILE" 2>&1 || error "Failed to run migration"
    
    success "Database schema initialized"
}

##############################################################################
# Step 8: Run Tests
##############################################################################
step_run_tests() {
    log "Step 8: Running test suite..."
    
    cd "$APP_DIR"
    source .venv/bin/activate
    
    python test_enhanced_scrapers.py >> "$LOG_FILE" 2>&1 || error "Tests failed"
    
    success "All tests passed ✅"
}

##############################################################################
# Step 9: Setup Systemd Services
##############################################################################
step_setup_services() {
    log "Step 9: Setting up systemd services..."
    
    # Create logging directory
    mkdir -p /var/log/aijs-platform
    chown www-data:www-data /var/log/aijs-platform
    
    # Create scraper service
    cat > /etc/systemd/system/aijs-scraper.service << 'EOF'
[Unit]
Description=AIJS Platform Job Scraper Service
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/AIJS-platform
Environment="PATH=/var/www/AIJS-platform/.venv/bin"
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/var/www/AIJS-platform/.env
ExecStart=/var/www/AIJS-platform/.venv/bin/python scheduler_runner.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=aijs-scraper

[Install]
WantedBy=multi-user.target
EOF

    # Create web service
    cat > /etc/systemd/system/aijs-web.service << 'EOF'
[Unit]
Description=AIJS Platform Web Interface
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/AIJS-platform
Environment="PATH=/var/www/AIJS-platform/.venv/bin"
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/var/www/AIJS-platform/.env
ExecStart=/var/www/AIJS-platform/.venv/bin/python app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=aijs-web

[Install]
WantedBy=multi-user.target
EOF

    # Create www-data user if it doesn't exist
    id -u www-data >/dev/null 2>&1 || useradd -r -s /bin/bash www-data
    
    # Set permissions
    chown -R www-data:www-data "$APP_DIR"
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable services
    systemctl enable aijs-scraper
    systemctl enable aijs-web
    
    success "Systemd services configured"
}

##############################################################################
# Step 10: Setup Nginx (Optional)
##############################################################################
step_setup_nginx() {
    log "Step 10: Setting up Nginx reverse proxy..."
    
    apt install -y -qq nginx || error "Failed to install Nginx"
    
    cat > /etc/nginx/sites-available/aijs-platform << 'EOF'
upstream aijs_app {
    server 127.0.0.1:5000 fail_timeout=0;
}

server {
    listen 80;
    server_name _;
    client_max_body_size 50M;

    location / {
        proxy_pass http://aijs_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
        proxy_read_timeout 600s;
        proxy_connect_timeout 600s;
    }
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/aijs-platform /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test and restart
    nginx -t || error "Nginx configuration test failed"
    systemctl start nginx
    systemctl enable nginx
    
    success "Nginx configured"
}

##############################################################################
# Step 11: Setup Firewall
##############################################################################
step_setup_firewall() {
    log "Step 11: Configuring firewall..."
    
    # Check if UFW is installed
    if ! command -v ufw &> /dev/null; then
        apt install -y -qq ufw
    fi
    
    ufw --force enable -q
    ufw allow 22/tcp -q      # SSH
    ufw allow 80/tcp -q      # HTTP
    ufw allow 443/tcp -q     # HTTPS
    
    success "Firewall configured"
}

##############################################################################
# Step 12: Final Verification
##############################################################################
step_verification() {
    log "Step 12: Final verification..."
    
    cd "$APP_DIR"
    source .venv/bin/activate
    
    # Test database
    log "Testing database connection..."
    python3 -c "from db import SessionLocal; s = SessionLocal(); print('✅ Database connected')" || error "Database connection failed"
    
    # Test imports
    log "Testing Python imports..."
    python3 -c "from models import Job, Company, Contact; print('✅ Models imported')" || error "Model import failed"
    
    success "All verifications passed ✅"
}

##############################################################################
# Main Function
##############################################################################
main() {
    clear
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  AIJS Platform - Automated Contabo Deployment                 ║"
    echo "║  Status: Production Ready                                     ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then 
        error "This script must be run as root"
    fi
    
    # Create log file
    mkdir -p $(dirname "$LOG_FILE")
    touch "$LOG_FILE"
    
    log "Starting deployment process..."
    log "Log file: $LOG_FILE"
    
    # Run deployment steps
    step_system_update
    step_install_deps
    step_clone_repo
    step_python_env
    step_postgres_setup
    step_create_env
    step_init_db
    step_run_tests
    step_setup_services
    
    # Ask about Nginx setup
    echo -e "${YELLOW}Do you want to setup Nginx reverse proxy? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        step_setup_nginx
    fi
    
    # Setup firewall
    step_setup_firewall
    
    # Final verification
    step_verification
    
    # Print summary
    echo -e "\n${GREEN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  ✅ DEPLOYMENT COMPLETED SUCCESSFULLY                         ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "\n${YELLOW}📋 Important Next Steps:${NC}"
    echo "1. Update .env file with your API keys:"
    echo "   nano $APP_DIR/.env"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - GOOGLE_SHEETS_API_KEY"
    echo ""
    echo "2. Start the services:"
    echo "   sudo systemctl start aijs-web"
    echo "   sudo systemctl start aijs-scraper"
    echo ""
    echo "3. Check service status:"
    echo "   sudo systemctl status aijs-web"
    echo "   sudo journalctl -u aijs-web -f"
    echo ""
    echo "4. Access the web interface:"
    echo "   http://<your_server_ip>"
    echo ""
    echo "5. View logs:"
    echo "   tail -f $LOG_FILE"
    echo ""
    
    echo -e "${BLUE}Database Credentials:${NC}"
    echo "  User: $DB_USER"
    echo "  Password: (in .env file)"
    echo ""
    
    echo -e "${BLUE}Documentation:${NC}"
    echo "  Deployment Guide: $APP_DIR/CONTABO_DEPLOYMENT_GUIDE.md"
    echo "  Quick Reference: $APP_DIR/DEPLOYMENT_QUICK_REFERENCE.md"
    echo ""
    
    log "Deployment completed successfully!"
}

# Run main function
main "$@"
