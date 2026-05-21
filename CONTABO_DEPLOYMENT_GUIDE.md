# Contabo VPS Deployment Guide

**Project**: AIJS Platform - Enhanced Job Scraper with Anti-Bot & Company Enrichment  
**Target**: Contabo VPS (Ubuntu 20.04/22.04)  
**Date**: May 21, 2026

---

## 📋 Pre-Deployment Checklist

- [ ] Contabo VPS created and SSH key configured
- [ ] Domain name configured (if applicable)
- [ ] SSL certificate ready (recommended)
- [ ] GitHub repo credentials configured
- [ ] PostgreSQL backup strategy planned
- [ ] Monitoring & alerting setup (optional)

---

## 🚀 Quick Start (Step-by-Step)

### Step 1: Initial Server Setup

```bash
# SSH into your server
ssh root@<your_server_ip>

# Update system packages
apt update && apt upgrade -y

# Install essential tools
apt install -y \
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
  python3-dev

# Install Node.js (for web interface if needed)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
apt install -y nodejs

# Verify installations
python3 --version
psql --version
node --version
npm --version
```

### Step 2: Clone Repository

```bash
# Create app directory
mkdir -p /var/www
cd /var/www

# Clone your repository
git clone https://github.com/ravinder024/AIJS-platform.git
cd AIJS-platform

# Verify directory structure
ls -la
```

### Step 3: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install chromium

# Verify installation
python -c "import job_scrapers; print('✅ All imports successful')"
```

### Step 4: Configure PostgreSQL Database

```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE USER job_agent WITH PASSWORD 'your_secure_password';
CREATE DATABASE job_agent OWNER job_agent;
ALTER ROLE job_agent SET client_encoding TO 'utf8';
ALTER ROLE job_agent SET default_transaction_isolation TO 'read committed';
ALTER ROLE job_agent SET default_transaction_deferrable TO on;
ALTER ROLE job_agent SET default_transaction_isolation TO 'read committed';
GRANT ALL PRIVILEGES ON DATABASE job_agent TO job_agent;
EOF

# Verify
sudo -u postgres psql -d job_agent -c "SELECT version();"
```

### Step 5: Configure Application

```bash
# Create .env file
cat > /var/www/AIJS-platform/.env << 'EOF'
# Database
DATABASE_URL=postgresql+psycopg2://job_agent:your_secure_password@localhost:5432/job_agent

# API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_SHEETS_API_KEY=your_google_sheets_key

# Flask
FLASK_ENV=production
FLASK_DEBUG=0
SECRET_KEY=$(python3 -c 'import os; print(os.urandom(32).hex())')

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/aijs-platform/app.log

# Features
ENABLE_SCRAPEGRAPH_AI=true
ENABLE_COMPANY_ENRICHMENT=true
MAX_JOBS_PER_RUN=100
REQUEST_TIMEOUT=30

# Rate limiting
REQUEST_DELAY_MIN=2
REQUEST_DELAY_MAX=5
EOF

# Secure permissions
chmod 600 /var/www/AIJS-platform/.env
```

### Step 6: Initialize Database Schema

```bash
cd /var/www/AIJS-platform
source .venv/bin/activate

# Run migration
python run_migration.py

# Verify schema
python -c "from db import engine; from models import Base; Base.metadata.create_all(bind=engine); print('✅ Database schema initialized')"
```

### Step 7: Test Installation

```bash
cd /var/www/AIJS-platform
source .venv/bin/activate

# Run tests
python test_enhanced_scrapers.py

# Output should show: 6/6 TESTS PASSED ✅
```

---

## 🔧 Running as Systemd Services

### Create Scraper Service

```bash
# Create service file
sudo nano /etc/systemd/system/aijs-scraper.service
```

```ini
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
```

### Create Web Service

```bash
# Create service file
sudo nano /etc/systemd/system/aijs-web.service
```

```ini
[Unit]
Description=AIJS Platform Web Interface
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
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
```

### Enable & Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable aijs-scraper
sudo systemctl enable aijs-web

# Start services
sudo systemctl start aijs-scraper
sudo systemctl start aijs-web

# Check status
sudo systemctl status aijs-scraper
sudo systemctl status aijs-web

# View logs
sudo journalctl -u aijs-scraper -n 50 -f
sudo journalctl -u aijs-web -n 50 -f
```

---

## 🌐 Configure Nginx Reverse Proxy

```bash
# Install Nginx
sudo apt install -y nginx

# Create Nginx config
sudo nano /etc/nginx/sites-available/aijs-platform
```

```nginx
upstream aijs_app {
    server 127.0.0.1:5000 fail_timeout=0;
}

server {
    listen 80;
    server_name your_domain.com;
    client_max_body_size 50M;

    # Redirect HTTP to HTTPS (optional)
    # return 301 https://$server_name$request_uri;

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
        proxy_request_buffering off;
        proxy_read_timeout 600s;
        proxy_connect_timeout 600s;
    }

    location /static {
        alias /var/www/AIJS-platform/templates;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/aijs-platform /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

---

## 🔒 SSL Certificate Setup (Let's Encrypt)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot certonly --nginx -d your_domain.com

# Update Nginx config to use HTTPS
sudo nano /etc/nginx/sites-available/aijs-platform
```

```nginx
server {
    listen 80;
    server_name your_domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your_domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your_domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your_domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    client_max_body_size 50M;

    location / {
        proxy_pass http://aijs_app;
        # ... rest of proxy config
    }
}
```

```bash
# Restart Nginx
sudo systemctl restart nginx

# Set up auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## 📊 Database Backup Strategy

### Manual Backup

```bash
# Create backup directory
mkdir -p /var/backups/aijs-platform
chmod 755 /var/backups/aijs-platform

# Backup database
sudo -u postgres pg_dump job_agent > /var/backups/aijs-platform/job_agent_$(date +%Y%m%d_%H%M%S).sql

# Compress
gzip /var/backups/aijs-platform/job_agent_*.sql
```

### Automated Daily Backup (Cron)

```bash
# Create backup script
sudo nano /usr/local/bin/backup-aijs-db.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/aijs-platform"
DB_NAME="job_agent"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
sudo -u postgres pg_dump $DB_NAME | gzip > $BACKUP_DIR/job_agent_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "job_agent_*.sql.gz" -mtime +30 -delete

echo "✅ Database backup completed: job_agent_$DATE.sql.gz"
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/backup-aijs-db.sh

# Add to crontab
sudo crontab -e
```

```cron
# Daily backup at 2 AM
0 2 * * * /usr/local/bin/backup-aijs-db.sh
```

### Restore from Backup

```bash
# Decompress
gunzip /var/backups/aijs-platform/job_agent_YYYYMMDD_HHMMSS.sql.gz

# Restore
sudo -u postgres psql job_agent < /var/backups/aijs-platform/job_agent_YYYYMMDD_HHMMSS.sql
```

---

## 📈 Monitoring & Logging

### Prometheus Metrics (Optional)

```bash
# Install monitoring
pip install prometheus-client

# Modify app.py to expose metrics
# See: https://github.com/prometheus/client_python
```

### Application Logs

```bash
# Create log directory
sudo mkdir -p /var/log/aijs-platform
sudo chown www-data:www-data /var/log/aijs-platform

# View logs
sudo tail -f /var/log/aijs-platform/app.log

# Rotate logs daily
sudo nano /etc/logrotate.d/aijs-platform
```

```
/var/log/aijs-platform/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        sudo systemctl reload aijs-scraper > /dev/null 2>&1 || true
    endscript
}
```

---

## 🔍 Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection
psql -h localhost -U job_agent -d job_agent -c "SELECT 1;"

# Review logs
sudo tail -f /var/log/postgresql/postgresql.log
```

### Service Won't Start

```bash
# Check service status
sudo systemctl status aijs-web

# View detailed error
sudo journalctl -u aijs-web -n 100

# Manually run to see errors
cd /var/www/AIJS-platform
source .venv/bin/activate
python app.py
```

### High Memory Usage

```bash
# Check resource usage
ps aux | grep python
top

# Adjust Flask config
export WORKERS=2
export THREADS=4
```

### Nginx 502 Bad Gateway

```bash
# Verify Flask is running
curl http://127.0.0.1:5000/

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Restart Nginx
sudo systemctl restart nginx
```

---

## 📝 Production Checklist

- [x] System packages installed
- [x] Python virtual environment created
- [x] PostgreSQL database configured
- [x] Application dependencies installed
- [x] Database schema initialized
- [x] Tests passing (6/6)
- [x] .env file configured
- [x] Services configured as systemd units
- [x] Nginx reverse proxy configured
- [ ] SSL certificate installed
- [ ] Backup strategy implemented
- [ ] Monitoring configured
- [ ] DNS records updated
- [ ] Firewall rules configured (see below)

---

## 🔐 Firewall Configuration

```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow PostgreSQL (only from localhost)
sudo ufw allow from 127.0.0.1 to 127.0.0.1 port 5432/tcp

# View rules
sudo ufw status
```

---

## 🚀 Post-Deployment

### Update Application

```bash
cd /var/www/AIJS-platform
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations if needed
python run_migration.py

# Restart services
sudo systemctl restart aijs-scraper
sudo systemctl restart aijs-web
```

### Monitor Health

```bash
# Check if services are running
sudo systemctl status aijs-scraper aijs-web

# Check database
sudo -u postgres psql job_agent -c "SELECT COUNT(*) FROM jobs;"

# Check application
curl https://your_domain.com/
```

### Schedule Regular Scrapes

```bash
# Edit crontab
sudo crontab -e
```

```cron
# Run scraper every 6 hours
0 */6 * * * cd /var/www/AIJS-platform && source .venv/bin/activate && python job_scraper.py --keyword "Product Manager" --location "Remote" --sources remoteok,indeed,naukri --output json

# Or use the scheduler
0 */6 * * * sudo systemctl restart aijs-scraper
```

---

## 📞 Support & Documentation

- **Project Guide**: See `Docs & resources/Project guide.md`
- **Implementation Report**: See `COMPLETION_REPORT.md`
- **API Documentation**: Check Flask endpoints in `app.py`
- **GitHub Issues**: Open at https://github.com/ravinder024/AIJS-platform/issues

---

## 🎯 Performance Tips

1. **Database Optimization**
   ```sql
   -- Analyze query performance
   EXPLAIN ANALYZE SELECT * FROM jobs WHERE company_id IS NOT NULL;
   
   -- Add indexes for frequent queries
   CREATE INDEX idx_jobs_company_created ON jobs(company_id, created_at DESC);
   ```

2. **Caching**
   - Enable Redis for session caching (optional)
   - Cache company data for 24 hours
   - Cache job listings for 1 hour

3. **Resource Limits**
   - Set ulimits for file descriptors
   - Configure connection pooling
   - Set query timeouts

4. **Monitoring**
   - Set up alerts for error rates >5%
   - Monitor disk space on `/var/www` and `/var/backups`
   - Track API response times

---

## ✅ Verification Steps

After deployment, verify everything works:

```bash
# 1. Test database connection
python -c "from db import SessionLocal; s = SessionLocal(); print('✅ DB Connected')"

# 2. Test API
curl http://localhost:5000/

# 3. Test scraper
python job_scraper.py --keyword "test" --location "Remote" --sources remoteok

# 4. Check services
sudo systemctl status aijs-web aijs-scraper

# 5. View logs
sudo journalctl -u aijs-web -n 20
```

---

**Status**: Production Ready 🚀  
**Created**: May 21, 2026  
**Last Updated**: May 21, 2026
