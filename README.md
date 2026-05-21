# Job Scraper - Multi-Source Job Board Scraper

A comprehensive Python web scraper that fetches job listings from multiple job boards including Naukri, Indeed, RemoteOK, and Wellfound (formerly AngelList).

## Features

- **Multi-Source Scraping**: Supports Naukri, Indeed, RemoteOK, Wellfound, and LinkedIn (placeholder)
- **Flexible Filtering**: Filter by keywords, location, job setting, posting date, and company size
- **Multiple Output Formats**: Save results to JSON, CSV, or Google Sheets
- **Duplicate Removal**: Automatically removes duplicate job listings
- **Parallel Processing**: Option to run scrapers in parallel for faster execution
- **Comprehensive Logging**: Detailed logging with timestamps and error handling

## Installation

1. **Clone or download the project files**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage
```bash
python job_scraper.py --keyword "Product Manager" --location "India" --days 7
```

## Daily Agent (Playwright + Feedback Loop)

The agent uses a persistent loop each day:
1. `Plan`: prioritize sources using learned source weights, source health, and recent feedback quality.
2. `Collect`: run Playwright/static collectors with conservative guardrails.
3. `Evaluate`: measure yield, novelty, and score quality by source.
4. `Adapt`: update source/keyword weights and temporarily pause weak sources.

Agent APIs:
- `GET/POST /api/profiles`
- `POST /api/runs/execute`
- `GET /api/jobs?include_explanations=1`
- `POST /api/feedback`
- `GET /api/agent/state`

Profile criteria schema now supports:
- Locations (`location`, `target_locations`)
- Roles (`role_query`, `role_queries`)
- Work setting (`work_settings`: remote/hybrid/onsite)
- Company size range (`company_size_min`, `company_size_max`)
- Company allow/deny lists (`include_companies`, `exclude_companies`)
- Industries (`industries`)
- Recently funded filter (`recently_funded_only`)
- Job types (`job_types`: full-time/part-time/contract)
- Experience range (`experience_min_years`, `experience_max_years`)
- Glassdoor threshold (`min_glassdoor_rating`)
- Salary range (`salary_min`, `salary_max`)

### 1) Install dependencies and browsers
```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 2) Configure environment
Copy `.env.example` and set values for:
- `DATABASE_URL` (PostgreSQL)
- `SMTP_*` and `DIGEST_*` for email digest
- `DAILY_RUN_TIME` (HH:MM)

### 3) Initialize database
```bash
python init_db.py
```

### 4) Start dashboard/API
```bash
python app.py
```
- Legacy search UI: `http://localhost:5000/`
- Agent dashboard: `http://localhost:5000/agent/dashboard`

### 5) Start daily scheduler
```bash
python scheduler_runner.py --time 08:00
```

### Advanced Usage
```bash
python job_scraper.py \
  --keyword "Senior Product Manager" \
  --location "Remote" \
  --days 14 \
  --setting remote \
  --exclude "6-day work week" "startup" \
  --output csv \
  --sources naukri indeed remoteok \
  --filename my_jobs \
  --parallel
```

### Command Line Arguments

| Argument | Required | Description | Example |
|----------|----------|-------------|---------|
| `--keyword` | Yes | Job search keyword | "Product Manager" |
| `--location` | Yes | Job location | "India", "Remote", "Delhi NCR" |
| `--days` | No | Posted within days (default: 7) | 1, 7, 14, 30 |
| `--setting` | No | Job setting preference | remote, hybrid, onsite |
| `--exclude` | No | Keywords to exclude | "6-day work week" "startup" |
| `--company_size` | No | Company size filter | "100-250 employees" |
| `--output` | No | Output format (default: json) | json, csv, gsheet |
| `--sources` | No | Job boards to scrape | naukri indeed remoteok wellfound |
| `--filename` | No | Custom output filename | my_job_search |
| `--parallel` | No | Run scrapers in parallel | (flag, no value) |

## Output Schema

Each job record contains the following fields:

```json
{
  "job_id": "unique-uuid",
  "title": "Senior Product Manager",
  "company_name": "Company ABC",
  "company_id": "",
  "description": "Job description text...",
  "requirements": "Requirements text...",
  "salary_min": 1200000,
  "salary_max": 1800000,
  "location": "Bangalore, India",
  "remote_type": "hybrid",
  "employment_type": "full_time",
  "experience_level": "Senior",
  "industry": "Technology",
  "source": "naukri",
  "source_url": "https://..."
}
```

## Google Sheets Integration

To use Google Sheets output:

1. **Create a Google Cloud Project** and enable the Google Sheets API
2. **Create a service account** and download the JSON credentials file
3. **Save the credentials** as `credentials.json` in the project directory
4. **Run with Google Sheets output:**
   ```bash
   python job_scraper.py --keyword "Developer" --location "Remote" --output gsheet
   ```

## File Structure

```
job-scraper/
├── job_scraper.py          # Main scraper script
├── job_scrapers.py         # Individual scraper functions
├── output_handlers.py      # Output formatting functions
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── job_scraper.log        # Generated log file
└── credentials.json       # Google Sheets credentials (optional)
```

## Supported Job Boards

### Currently Implemented:
- **Naukri.com**: Indian job board with comprehensive job listings
- **Indeed.com**: Global job board with extensive coverage
- **RemoteOK.io**: Focused on remote job opportunities
- **Wellfound**: Startup and tech company job listings

### Placeholder:
- **LinkedIn**: Requires authentication and anti-bot bypass (placeholder implementation)

## Error Handling

The scraper includes comprehensive error handling:
- Network timeouts and connection errors
- HTML parsing failures
- Rate limiting and anti-bot measures
- File I/O errors
- Invalid input validation

All errors are logged to `job_scraper.log` with timestamps.

## Limitations

1. **Rate Limiting**: Some job boards may implement rate limiting
2. **Anti-Bot Measures**: Websites may block automated requests
3. **HTML Structure Changes**: Scrapers may break if websites change their structure
4. **LinkedIn**: Requires complex authentication, only placeholder provided

## Contributing

To add a new job board scraper:

1. **Create a new function** in `job_scrapers.py`:
   ```python
   def scrape_newsite(keyword, location, days, job_setting, exclude_keywords, company_size):
       # Implementation here
       return jobs_list
   ```

2. **Add to the scrapers dictionary** in `job_scraper.py`:
   ```python
   scrapers = {
       'newsite': scrape_newsite,
       # ... existing scrapers
   }
   ```

3. **Update the argument parser** to include the new source in choices

## License

This project is for educational purposes. Please respect the robots.txt and terms of service of the websites you scrape.

## Disclaimer

This tool is intended for educational and personal use. Users are responsible for complying with the terms of service and robots.txt files of the websites they scrape. The authors are not responsible for any misuse of this tool.
