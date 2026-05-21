# 🚀 Deployment Quick Reference

**Status**: ✅ Codebase uploaded to GitHub  
**Repo**: https://github.com/ravinder024/AIJS-platform.git

---

## 📦 What Was Uploaded

**Total Files**: 45  
**Commit**: Initial commit (89698a9)  
**Size**: 248.27 KiB

### Core Application Files
- ✅ Job scraping system (remoteok, indeed, naukri, wellfound, linkedin)
- ✅ Anti-bot evasion layer (multi-layer defense)
- ✅ ScrapeGraphAI LLM fallback
- ✅ Company enrichment scrapers
- ✅ Database models and migrations
- ✅ Flask web API and dashboard
- ✅ APScheduler for automated runs

### Infrastructure Files
- ✅ requirements.txt (all dependencies)
- ✅ .env.example (configuration template)
- ✅ .gitignore (proper exclusions)
- ✅ Database schema and migration scripts
- ✅ Test suites (6/6 passing)

### Documentation
- ✅ CONTABO_DEPLOYMENT_GUIDE.md (full setup instructions)
- ✅ COMPLETION_REPORT.md (validation summary)
- ✅ IMPLEMENTATION_COMPLETE.md (architecture overview)
- ✅ README.md (project overview)

---

## ⚡ Contabo Server Setup (Quick Summary)

### **Estimated Time**: 15-30 minutes

### **1. System Setup** (3 min)
```bash
ssh root@<your_server_ip>
apt update && apt upgrade -y
apt install -y git python3.11 python3-pip python3-venv postgresql postgresql-contrib curl wget build-essential
```

### **2. Clone & Install** (5 min)
```bash
cd /var/www
git clone https://github.com/ravinder024/AIJS-platform.git
cd AIJS-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

### **3. Database Setup** (3 min)
```bash
sudo systemctl start postgresql
sudo -u postgres psql << 'EOF'
CREATE USER job_agent WITH PASSWORD 'your_secure_password';
CREATE DATABASE job_agent OWNER job_agent;
GRANT ALL PRIVILEGES ON DATABASE job_agent TO job_agent;
EOF
```

### **4. Configure & Initialize** (2 min)
```bash
# Copy and edit .env file
cp .env.example .env
nano .env  # Update DATABASE_URL and API keys

# Initialize database
python run_migration.py
```

### **5. Run Services** (2 min)
```bash
# As systemd services (see full guide for setup)
sudo systemctl start aijs-web
sudo systemctl start aijs-scraper

# Or manually for testing
python app.py  # Web at http://localhost:5000
python scheduler_runner.py  # Background scheduler
```

### **6. Configure Nginx** (Optional, 5 min)
```bash
# Install and configure reverse proxy
apt install -y nginx
# See CONTABO_DEPLOYMENT_GUIDE.md for config
sudo systemctl start nginx
```

---

## 🔐 Security Configuration

### Environment Variables (.env)
```bash
DATABASE_URL=postgresql+psycopg2://job_agent:PASSWORD@localhost:5432/job_agent
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_SHEETS_API_KEY=your_key
FLASK_ENV=production
SECRET_KEY=generate_random_key
```

### Database User
```sql
-- Secure postgresql user
CREATE USER job_agent WITH ENCRYPTED PASSWORD 'your_secure_password';
ALTER USER job_agent WITH CONNECTION LIMIT 10;
```

### Firewall Rules
```bash
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw deny 5000/tcp     # Block Flask direct access
```

---

## 📊 Verify Installation

```bash
# Test 1: Database
psql -h localhost -U job_agent -d job_agent -c "SELECT 1;"
# Expected: 1 (success)

# Test 2: Python Imports
python -c "import job_scrapers; from models import Job; print('✅ OK')"

# Test 3: Run Tests
python test_enhanced_scrapers.py
# Expected: 6/6 TESTS PASSED ✅

# Test 4: Start Web Service
python app.py
# Expected: Running on http://127.0.0.1:5000
```

---

## 🔄 Daily Operations

### Manual Scrape
```bash
source /var/www/AIJS-platform/.venv/bin/activate
python job_scraper.py \
  --keyword "Product Manager" \
  --location "Remote" \
  --sources remoteok,indeed,naukri \
  --output json
```

### View Recent Jobs
```bash
python -c "
from db import SessionLocal
from models import Job
session = SessionLocal()
jobs = session.query(Job).order_by(Job.collected_at.desc()).limit(10).all()
for j in jobs:
    print(f'{j.title} @ {j.company_name}')
"
```

### Database Backup
```bash
sudo -u postgres pg_dump job_agent | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Check Service Status
```bash
sudo systemctl status aijs-web
sudo systemctl status aijs-scraper
sudo journalctl -u aijs-web -n 50 -f
```

---

## 📈 Scaling & Performance

### For High Load (>1000 jobs/day)

1. **Database Optimization**
   ```sql
   CREATE INDEX idx_jobs_company_created ON jobs(company_id, created_at DESC);
   VACUUM ANALYZE;
   ```

2. **Add PostgreSQL Connection Pooling**
   ```bash
   apt install -y pgbouncer
   # Configure in /etc/pgbouncer/pgbouncer.ini
   ```

3. **Enable Caching**
   ```bash
   apt install -y redis-server
   # Configure in app.py for session caching
   ```

4. **Horizontal Scaling**
   - Run multiple scraper instances
   - Load balance with Nginx
   - Separate read/write databases (optional)

---

## ❌ Troubleshooting

| Issue | Solution |
|-------|----------|
| **403 Forbidden on Indeed** | Increase delays in anti_bot_config.yaml: `aggressive_delay: 15.0` |
| **Database Connection Failed** | Verify .env DATABASE_URL, check PostgreSQL: `sudo systemctl status postgresql` |
| **Services Won't Start** | Check logs: `sudo journalctl -u aijs-web -n 100` |
| **High Memory Usage** | Reduce worker count: `WORKERS=1` in environment |
| **Nginx 502 Bad Gateway** | Verify Flask running: `curl http://127.0.0.1:5000/` |
| **SSL Certificate Issues** | Renew: `sudo certbot renew`, view logs: `sudo tail -f /var/log/letsencrypt/letsencrypt.log` |

---

## 📞 Support Resources

| Resource | Location |
|----------|----------|
| Full Setup Guide | CONTABO_DEPLOYMENT_GUIDE.md |
| Architecture Overview | IMPLEMENTATION_COMPLETE.md |
| Validation Report | COMPLETION_REPORT.md |
| API Documentation | app.py (Flask routes) |
| Project Guide | Docs & resources/Project guide.md |

---

## ✅ Post-Deployment Checklist

- [ ] SSH access verified
- [ ] Git repository cloned
- [ ] Python dependencies installed
- [ ] PostgreSQL initialized
- [ ] Database schema created
- [ ] .env file configured
- [ ] Tests passing (6/6)
- [ ] Web service running
- [ ] Jobs scraping successfully
- [ ] Company enrichment working
- [ ] Nginx configured (if needed)
- [ ] SSL certificate installed
- [ ] Backup strategy implemented
- [ ] Monitoring configured
- [ ] DNS updated (if needed)

---

## 🎯 Next Steps

1. **Immediate** (Today)
   - [ ] SSH into Contabo server
   - [ ] Run through Quick Setup section
   - [ ] Verify all tests passing

2. **Short-term** (This week)
   - [ ] Set up Nginx reverse proxy
   - [ ] Configure SSL certificate
   - [ ] Implement automated backups
   - [ ] Set up monitoring/alerting

3. **Long-term** (This month)
   - [ ] Optimize database queries
   - [ ] Implement caching layer
   - [ ] Add advanced analytics
   - [ ] Scale for production load

---

## 📊 System Requirements

### Minimum (Development)
- **CPU**: 1 core
- **RAM**: 2 GB
- **Disk**: 20 GB
- **OS**: Ubuntu 20.04+

### Recommended (Production)
- **CPU**: 2-4 cores
- **RAM**: 4-8 GB
- **Disk**: 50+ GB (SSD)
- **OS**: Ubuntu 22.04 LTS

### Contabo Plans
- **VPS S** (2 cores, 4 GB RAM, 40 GB SSD): ✅ Sufficient
- **VPS M** (4 cores, 8 GB RAM, 80 GB SSD): ✅ Recommended
- **VPS L** (6 cores, 16 GB RAM, 160 GB SSD): ✅ Optimal

---

**Status**: 🟢 Ready for Deployment  
**GitHub**: https://github.com/ravinder024/AIJS-platform.git  
**Created**: May 21, 2026
