# Repository Guidelines

## Project Structure & Module Organization
Core Python code lives at the repository root.
- `job_scraper.py`: CLI entry point that parses args, runs scrapers, filters, deduplicates, and writes output.
- `job_scrapers.py`: source-specific scraping functions (`scrape_remoteok`, `scrape_indeed`, etc.).
- `output_handlers.py`: JSON/CSV/Google Sheets output helpers.
- `app.py`: Flask web UI/API (`/`, `/search`, `/export/<format>`).
- `templates/index.html`: frontend for the web interface.
- `test_scraper.py`, `test_all_scrapers.py`: executable test scripts.
- Generated artifacts: `job_listings_*.json`, `job_scraper.log`, `__pycache__/`.

## Build, Test, and Development Commands
- `python -m venv .venv` then `.\.venv\Scripts\Activate.ps1`: create and activate local virtual env (Windows PowerShell).
- `pip install -r requirements.txt`: install runtime dependencies.
- `python job_scraper.py --keyword "Product Manager" --location "Remote" --sources remoteok --output json`: run CLI scraper.
- `python app.py`: start Flask app at `http://localhost:5000`.
- `python test_scraper.py`: smoke test the RemoteOK scraper.
- `python test_all_scrapers.py`: run all scraper checks and print a summary.

## Coding Style & Naming Conventions
Use Python conventions already present in the codebase:
- 4-space indentation, `snake_case` for functions/variables, `UPPER_CASE` for constants (for example, `SCRAPERS`).
- Keep scraper functions focused and side-effect light; return normalized job dictionaries.
- Prefer type hints for new/updated public functions.
- Follow existing logging style (`logging` with informative `INFO`/`ERROR` messages).

## Testing Guidelines
Tests are script-based integration checks against live/partially blocked sources.
- Name new test files `test_*.py`.
- Run targeted tests first (`python test_scraper.py`) before `python test_all_scrapers.py`.
- Validate: non-empty result sets where expected, valid `source_url` format, and stable key fields (`title`, `company_name`, `location`).

## Commit & Pull Request Guidelines
Git history is not available in this workspace snapshot, so use this convention going forward:
- Commit format: `type(scope): imperative summary` (example: `feat(scrapers): add fallback for blocked endpoint`).
- Keep commits focused and include why behavior changed.
- PRs should include: change summary, test commands executed, sample output (CLI snippet or UI screenshot), and linked issue/task if applicable.

## Security & Configuration Tips
- Never commit secrets (for example, Google Sheets `credentials.json`).
- Avoid committing generated outputs/logs unless required for reproducible debugging.
