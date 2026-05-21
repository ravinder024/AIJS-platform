# 🎯 Your Deployment Checklist - ACTION ITEMS

**GitHub Repository**: https://github.com/ravinder024/AIJS-platform.git  
**Status**: ✅ Ready for Deployment  
**Date Created**: May 21, 2026

---

## 📋 BEFORE You Deploy to Contabo

### 1. **Gather Required Information**
- [ ] Contabo server IP address or hostname
- [ ] SSH credentials (username/password or key)
- [ ] Anthropic API Key (for ScrapeGraphAI)
- [ ] Google Sheets API Key (optional)
- [ ] Domain name (optional, for SSL/DNS)

### 2. **Verify GitHub Access**
- [ ] Test SSH/HTTPS access to repository
- [ ] Verify you can pull from GitHub
```bash
git clone https://github.com/ravinder024/AIJS-platform.git
```

---

## 🚀 DEPLOYMENT STEPS (Choose One)

### **OPTION A: FASTEST (Automated - Recommended)** ⏱️ ~15 minutes

```bash
# 1. SSH into Contabo server
ssh root@<your_server_ip>

# 2. Run one command to deploy everything
curl -sSL https://raw.githubusercontent.com/ravinder024/AIJS-platform/main/deploy.sh | bash

# 3. Update API keys
nano /var/www/AIJS-platform/.env
# ⬆️ Update ANTHROPIC_API_KEY and GOOGLE_SHEETS_API_KEY

# 4. Start services
sudo systemctl start aijs-web aijs-scraper

# 5. Verify
sudo systemctl status aijs-web aijs-scraper

# 6. Access
# Open browser: http://<your_server_ip>:5000
# or http://<your_domain> if Nginx is configured
```

✨ **That's it!** Everything is automatically installed and configured.

---

### **OPTION B: GUIDED (Step-by-Step)** ⏱️ ~30 minutes

Follow this document in your repository:
```
📄 /CONTABO_DEPLOYMENT_GUIDE.md
```

- Detailed step-by-step instructions
- Explanations for each command
- Troubleshooting section
- Best practices included

---

### **OPTION C: REFERENCE (Quick Commands)** ⏱️ Custom pace

Use this as a reference:
```
📄 /DEPLOYMENT_QUICK_REFERENCE.md
```

- Common commands
- Essential operations
- Verification steps

---

## ✅ POST-DEPLOYMENT CHECKLIST

After deployment (whether automatic or manual):

- [ ] **Update Environment**
  ```bash
  nano /var/www/AIJS-platform/.env
  # Update API keys and verify DATABASE_URL
  ```

- [ ] **Verify Services Running**
  ```bash
  sudo systemctl status aijs-web
  sudo systemctl status aijs-scraper
  ```

- [ ] **Test Database Connection**
  ```bash
  psql -h localhost -U job_agent -d job_agent -c "SELECT 1;"
  ```

- [ ] **Access Web Interface**
  ```
  http://your_server_ip:5000
  ```

- [ ] **Run First Scrape**
  ```bash
  cd /var/www/AIJS-platform
  source .venv/bin/activate
  python job_scraper.py --keyword "test" --location "Remote" --sources remoteok
  ```

- [ ] **Verify Jobs in Database**
  ```bash
  psql -h localhost -U job_agent -d job_agent -c "SELECT COUNT(*) FROM jobs;"
  ```

- [ ] **Check Logs**
  ```bash
  sudo journalctl -u aijs-web -n 20 -f
  ```

---

## 🔑 Key Files You'll Need

| File | Purpose | Action |
|------|---------|--------|
| **deploy.sh** | Automated setup | Run on Contabo |
| **CONTABO_DEPLOYMENT_GUIDE.md** | Full instructions | Reference during setup |
| **DEPLOYMENT_QUICK_REFERENCE.md** | Quick commands | Keep handy |
| **.env** | Configuration | Update with your keys |
| **app.py** | Web interface | Check logs: `systemctl status aijs-web` |
| **scheduler_runner.py** | Job scraper | Check logs: `systemctl status aijs-scraper` |

---

## 🎯 What Gets Deployed

### Services
- ✅ **aijs-web**: Flask web interface (port 5000)
- ✅ **aijs-scraper**: APScheduler job scraper

### Database
- ✅ **PostgreSQL**: Main database
- ✅ **Tables**: jobs, companies, contacts, runs, search_profiles, etc.

### Dependencies
- ✅ Python 3.11 with virtual environment
- ✅ Playwright for browser automation
- ✅ ScrapeGraphAI for LLM fallback
- ✅ Flask, SQLAlchemy, psycopg2, etc.

### Features
- ✅ Anti-bot multi-layer defense
- ✅ 5 job sources (RemoteOK, Indeed, Naukri, Wellfound, LinkedIn)
- ✅ Company enrichment
- ✅ Contact scraping
- ✅ Web dashboard
- ✅ REST API

---

## 🆘 If Something Goes Wrong

### **Service won't start**
```bash
sudo journalctl -u aijs-web -n 50
# or
sudo journalctl -u aijs-scraper -n 50
```

### **Database connection error**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check your .env file
cat /var/www/AIJS-platform/.env | grep DATABASE_URL

# Test connection
psql -h localhost -U job_agent -d job_agent -c "SELECT 1;"
```

### **Port already in use**
```bash
# Check what's using port 5000
sudo lsof -i :5000

# Or change port in app.py
nano /var/www/AIJS-platform/app.py
# Change: app.run(port=5000) → app.run(port=8000)
```

### **Need help?**
See: **CONTABO_DEPLOYMENT_GUIDE.md** → Troubleshooting section

---

## 📞 Emergency Commands

### Stop all services
```bash
sudo systemctl stop aijs-web aijs-scraper
```

### Restart all services
```bash
sudo systemctl restart aijs-web aijs-scraper
```

### View all logs
```bash
sudo journalctl -u aijs-web -u aijs-scraper -n 100 -f
```

### SSH into server and activate environment
```bash
ssh root@your_server_ip
cd /var/www/AIJS-platform
source .venv/bin/activate
python app.py  # Run manually for debugging
```

---

## 🎯 Next: Optional Configuration

After basic deployment works, consider:

### 1. **Setup Nginx Reverse Proxy**
```bash
# Run deploy.sh again with Nginx option
# OR follow: CONTABO_DEPLOYMENT_GUIDE.md → Configure Nginx Reverse Proxy
```

### 2. **Configure SSL Certificate**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d your_domain.com
```

### 3. **Setup Automated Backups**
```bash
# Add to crontab
sudo crontab -e
# Add line: 0 2 * * * /usr/local/bin/backup-aijs-db.sh
```

### 4. **Configure Firewall**
```bash
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### 5. **Setup Monitoring** (Optional)
```bash
# Monitor disk space, memory, services
htop
df -h
```

---

## 📊 Verify Everything Works

```bash
# 1. Web interface
curl http://localhost:5000/
# Expected: HTML response

# 2. Database
psql -h localhost -U job_agent -d job_agent -c "SELECT version();"
# Expected: PostgreSQL version info

# 3. Python environment
python -c "import job_scrapers; print('✅ All imports OK')"
# Expected: ✅ All imports OK

# 4. Run tests (optional)
python test_enhanced_scrapers.py
# Expected: 6/6 TESTS PASSED ✅
```

---

## 🎯 Your First Scrape

Once everything is running:

```bash
cd /var/www/AIJS-platform
source .venv/bin/activate

# Scrape jobs
python job_scraper.py \
  --keyword "Product Manager" \
  --location "Remote" \
  --sources remoteok,indeed,naukri \
  --output json

# View results
ls -la job_listings_*.json

# Check database
psql -h localhost -U job_agent -d job_agent \
  -c "SELECT title, company_name, source, created_at FROM jobs LIMIT 5;"
```

---

## 📝 Important Notes

1. **API Keys Required**
   - ⚠️ You MUST update `.env` with Anthropic API key
   - Without it, ScrapeGraphAI fallback won't work
   - Basic scraping still works without it

2. **Database Credentials**
   - Username: `job_agent`
   - Password: Auto-generated during deployment
   - Stored in `.env` file (keep secure!)

3. **Services Auto-Start**
   - Services are configured to auto-start on reboot
   - Check with: `sudo systemctl list-unit-files | grep aijs`

4. **Log Files**
   - Web logs: `sudo journalctl -u aijs-web -f`
   - Scraper logs: `sudo journalctl -u aijs-scraper -f`
   - Combined logs: `/var/log/aijs-platform/app.log`

5. **Backup Your Data**
   - Database backups recommended daily
   - See guide for automated backup setup

---

## 🚀 Ready?

### **Start Here:**
```bash
ssh root@your_contabo_server_ip
curl -sSL https://raw.githubusercontent.com/ravinder024/AIJS-platform/main/deploy.sh | bash
```

### **Then:**
1. Update `.env` with API keys
2. Start services
3. Access web interface
4. Run first scrape

---

## 📚 Documentation Links

| Document | Link |
|----------|------|
| **Full Deployment Guide** | CONTABO_DEPLOYMENT_GUIDE.md |
| **Quick Reference** | DEPLOYMENT_QUICK_REFERENCE.md |
| **Deployment Summary** | DEPLOYMENT_SUMMARY.md |
| **Project Overview** | README.md |
| **Architecture** | IMPLEMENTATION_COMPLETE.md |
| **Validation Report** | COMPLETION_REPORT.md |

---

## 🎉 You're All Set!

Everything is ready to deploy. The codebase is on GitHub, documentation is complete, and the automated deployment script will handle most of the work.

**Next step**: SSH into your Contabo server and run the deployment script!

```bash
ssh root@your_server_ip
curl -sSL https://raw.githubusercontent.com/ravinder024/AIJS-platform/main/deploy.sh | bash
```

Good luck! 🚀

---

**Created**: May 21, 2026  
**Status**: Production Ready  
**Repository**: https://github.com/ravinder024/AIJS-platform.git
