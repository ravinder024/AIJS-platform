from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS
import csv
import io
import json
import logging
from datetime import datetime

from agent_service import (
    create_profile,
    get_agent_state,
    get_jobs_for_api,
    get_profile,
    init_db,
    list_profiles,
    list_runs,
    run_daily_search,
    submit_feedback,
)
from job_scrapers import scrape_naukri, scrape_indeed, scrape_remoteok, scrape_wellfound, scrape_linkedin

# Setup logging for web app
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
try:
    init_db()
except Exception as exc:
    logger.warning("Database initialization skipped at startup: %s", exc)

# Job scraper functions mapping
SCRAPERS = {
    'naukri': scrape_naukri,
    'indeed': scrape_indeed,
    'remoteok': scrape_remoteok,
    'wellfound': scrape_wellfound,
    'linkedin': scrape_linkedin
}

def run_scraper(scraper_func, source_name, **kwargs):
    """Run a scraper function with error handling."""
    try:
        logger.info(f"Starting {source_name} scraper...")
        jobs = scraper_func(**kwargs)
        logger.info(f"{source_name} scraper completed - Found {len(jobs)} jobs")
        return jobs
    except Exception as e:
        logger.error(f"Error in {source_name} scraper: {e}")
        return []

def scrape_all_sources(keyword, location, days, job_setting, exclude_keywords, company_size, sources):
    """Scrape jobs from multiple sources."""
    all_jobs = []
    
    scraper_args = {
        'keyword': keyword,
        'location': location,
        'days': days,
        'job_setting': job_setting,
        'exclude_keywords': exclude_keywords,
        'company_size': company_size
    }
    
    for source in sources:
        if source in SCRAPERS:
            jobs = run_scraper(SCRAPERS[source], source, **scraper_args)
            all_jobs.extend(jobs)
    
    return all_jobs

def deduplicate_jobs(jobs):
    """Remove duplicate jobs based on title and company with improved logic."""
    seen = set()
    unique_jobs = []
    
    for job in jobs:
        # Create a key from title and company name (normalized)
        title = job.get('title', '').strip().lower()
        company = job.get('company_name', '').strip().lower()
        
        # Skip completely empty jobs
        if not title and not company:
            continue
            
        # Use job URL as fallback for unique identification
        job_url = job.get('source_url', '')
        key = f"{title}|{company}|{job_url}"
        
        # More lenient duplicate detection - only skip if exact match
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
    
    return unique_jobs

def apply_filters(jobs, exclude_keywords):
    """Apply additional filters to job listings."""
    if not exclude_keywords:
        return jobs
    
    filtered_jobs = []
    for job in jobs:
        description = job.get('description', '').lower()
        title = job.get('title', '').lower()
        
        # Check if any exclude keyword is in title or description
        exclude = False
        for keyword in exclude_keywords:
            if keyword.lower() in description or keyword.lower() in title:
                exclude = True
                break
        
        if not exclude:
            filtered_jobs.append(job)
    
    return filtered_jobs

@app.route('/')
def index():
    """Main page with job search form."""
    return render_template('index.html')


@app.route('/agent/dashboard')
def agent_dashboard():
    """Dashboard page for profile, run, and feedback workflows."""
    return render_template('agent_dashboard.html')

@app.route('/search', methods=['POST'])
def search_jobs():
    """Handle job search request."""
    try:
        # Get form data
        keyword = request.form.get('keyword', '').strip()
        location = request.form.get('location', '').strip()
        days = int(request.form.get('days', 7))
        job_setting = request.form.get('job_setting', '')
        exclude_keywords = request.form.get('exclude_keywords', '').strip()
        company_size = request.form.get('company_size', '').strip()
        sources = request.form.getlist('sources')
        
        # Parse exclude keywords
        exclude_list = [kw.strip() for kw in exclude_keywords.split(',') if kw.strip()] if exclude_keywords else []
        
        # Validate required fields
        if not keyword or not location:
            return jsonify({'error': 'Keyword and location are required'}), 400
        
        # Scrape jobs from selected sources
        logger.info(f"Searching for: {keyword} in {location}")
        all_jobs = scrape_all_sources(
            keyword=keyword,
            location=location,
            days=days,
            job_setting=job_setting if job_setting else None,
            exclude_keywords=exclude_list,
            company_size=company_size if company_size else None,
            sources=sources
        )
        
        # Apply filters and deduplication
        filtered_jobs = apply_filters(all_jobs, exclude_list)
        unique_jobs = deduplicate_jobs(filtered_jobs)
        
        logger.info(f"Found {len(unique_jobs)} unique jobs after filtering")
        
        # Limit results for display (show first 20)
        display_jobs = unique_jobs[:20]
        
        return jsonify({
            'success': True,
            'total_jobs': len(unique_jobs),
            'displayed_jobs': len(display_jobs),
            'jobs': display_jobs,
            'search_params': {
                'keyword': keyword,
                'location': location,
                'days': days,
                'job_setting': job_setting,
                'exclude_keywords': exclude_list,
                'sources': sources
            }
        })
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

@app.route('/export/<format>')
def export_jobs(format):
    """Export jobs to JSON or CSV format."""
    try:
        # Get jobs from session or re-run search
        # For simplicity, we'll expect the jobs data to be passed via query params
        jobs_json = request.args.get('jobs')
        if not jobs_json:
            return jsonify({'error': 'No jobs data to export'}), 400
        
        jobs = json.loads(jobs_json)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format.lower() == 'json':
            # Create JSON file
            filename = f'job_search_results_{timestamp}.json'
            
            # Create in-memory file
            output = io.StringIO()
            json.dump(jobs, output, indent=2)
            output.seek(0)
            
            # Convert to bytes
            mem_file = io.BytesIO()
            mem_file.write(output.getvalue().encode('utf-8'))
            mem_file.seek(0)
            
            return send_file(
                mem_file,
                as_attachment=True,
                download_name=filename,
                mimetype='application/json'
            )
            
        elif format.lower() == 'csv':
            # Create CSV file
            filename = f'job_search_results_{timestamp}.csv'
            
            # Create CSV in memory
            output = io.StringIO()
            if jobs:
                writer = csv.DictWriter(output, fieldnames=jobs[0].keys())
                writer.writeheader()
                writer.writerows(jobs)
            
            output.seek(0)
            
            # Convert to bytes
            mem_file = io.BytesIO()
            mem_file.write(output.getvalue().encode('utf-8'))
            mem_file.seek(0)
            
            return send_file(
                mem_file,
                as_attachment=True,
                download_name=filename,
                mimetype='text/csv'
            )
        
        else:
            return jsonify({'error': 'Invalid export format. Use json or csv'}), 400
            
    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({'error': f'Export failed: {str(e)}'}), 500


def _parse_str_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    return []


def _parse_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


@app.route('/api/profiles', methods=['GET', 'POST'])
def profiles_api():
    if request.method == 'GET':
        profiles = list_profiles()
        return jsonify(
            {
                "profiles": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "role_query": p.role_query,
                        "location": p.location,
                        "target_locations": p.target_locations,
                        "role_queries": p.role_queries,
                        "work_settings": p.work_settings,
                        "company_size_min": p.company_size_min,
                        "company_size_max": p.company_size_max,
                        "include_companies": p.include_companies,
                        "exclude_companies": p.exclude_companies,
                        "industries": p.industries,
                        "recently_funded_only": p.recently_funded_only,
                        "job_types": p.job_types,
                        "experience_min_years": p.experience_min_years,
                        "experience_max_years": p.experience_max_years,
                        "min_glassdoor_rating": p.min_glassdoor_rating,
                        "salary_min": p.salary_min,
                        "salary_max": p.salary_max,
                        "include_keywords": p.include_keywords,
                        "exclude_keywords": p.exclude_keywords,
                        "sources": p.sources,
                        "is_active": p.is_active,
                        "created_at": p.created_at.isoformat(),
                    }
                    for p in profiles
                ]
            }
        )

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    role_query = (payload.get("role_query") or "").strip()
    location = (payload.get("location") or "Remote").strip()

    if not name or not role_query:
        return jsonify({"error": "name and role_query are required"}), 400

    try:
        profile = create_profile(
            {
                "name": name,
                "role_query": role_query,
                "location": location,
                "target_locations": _parse_str_list(payload.get("target_locations")),
                "role_queries": _parse_str_list(payload.get("role_queries")),
                "work_settings": _parse_str_list(payload.get("work_settings")),
                "company_size_min": _parse_int(payload.get("company_size_min")),
                "company_size_max": _parse_int(payload.get("company_size_max")),
                "include_companies": _parse_str_list(payload.get("include_companies")),
                "exclude_companies": _parse_str_list(payload.get("exclude_companies")),
                "industries": _parse_str_list(payload.get("industries")),
                "recently_funded_only": _parse_bool(payload.get("recently_funded_only")),
                "job_types": _parse_str_list(payload.get("job_types")),
                "experience_min_years": _parse_float(payload.get("experience_min_years")),
                "experience_max_years": _parse_float(payload.get("experience_max_years")),
                "min_glassdoor_rating": _parse_float(payload.get("min_glassdoor_rating")),
                "salary_min": _parse_float(payload.get("salary_min")),
                "salary_max": _parse_float(payload.get("salary_max")),
                "include_keywords": _parse_str_list(payload.get("include_keywords")),
                "exclude_keywords": _parse_str_list(payload.get("exclude_keywords")),
                "sources": payload.get("sources"),
                "is_active": bool(payload.get("is_active", True)),
            }
        )
        return jsonify({"profile_id": profile.id, "message": "Profile created"}), 201
    except Exception as exc:
        logger.exception("Profile creation failed: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route('/api/profiles/<int:profile_id>', methods=['GET'])
def profile_detail_api(profile_id):
    profile = get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    return jsonify(
        {
            "id": profile.id,
            "name": profile.name,
            "role_query": profile.role_query,
            "location": profile.location,
            "target_locations": profile.target_locations,
            "role_queries": profile.role_queries,
            "work_settings": profile.work_settings,
            "company_size_min": profile.company_size_min,
            "company_size_max": profile.company_size_max,
            "include_companies": profile.include_companies,
            "exclude_companies": profile.exclude_companies,
            "industries": profile.industries,
            "recently_funded_only": profile.recently_funded_only,
            "job_types": profile.job_types,
            "experience_min_years": profile.experience_min_years,
            "experience_max_years": profile.experience_max_years,
            "min_glassdoor_rating": profile.min_glassdoor_rating,
            "salary_min": profile.salary_min,
            "salary_max": profile.salary_max,
            "include_keywords": profile.include_keywords,
            "exclude_keywords": profile.exclude_keywords,
            "sources": profile.sources,
            "is_active": profile.is_active,
        }
    )


@app.route('/api/runs/execute', methods=['POST'])
def execute_run_api():
    payload = request.get_json(silent=True) or {}
    profile_id = payload.get("profile_id")
    if not profile_id:
        return jsonify({"error": "profile_id is required"}), 400

    try:
        result = run_daily_search(int(profile_id))
        return jsonify(result)
    except Exception as exc:
        logger.exception("Run execution failed: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route('/api/profiles/<int:profile_id>/runs', methods=['GET'])
def list_runs_api(profile_id):
    runs = list_runs(profile_id)
    return jsonify(
        {
            "runs": [
                {
                    "id": r.id,
                    "profile_id": r.profile_id,
                    "status": r.status,
                    "started_at": r.started_at.isoformat(),
                    "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                    "total_collected": r.total_collected,
                    "total_new": r.total_new,
                    "notes": r.notes,
                }
                for r in runs
            ]
        }
    )


@app.route('/api/feedback', methods=['POST'])
def submit_feedback_api():
    payload = request.get_json(silent=True) or {}
    missing = [k for k in ["job_id", "profile_id", "vote"] if k not in payload]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    vote = str(payload.get("vote", "")).lower().strip()
    if vote not in {"like", "dislike"}:
        return jsonify({"error": "vote must be 'like' or 'dislike'"}), 400

    try:
        feedback = submit_feedback(
            {
                "job_id": int(payload["job_id"]),
                "profile_id": int(payload["profile_id"]),
                "vote": vote,
                "reason_tags": _parse_str_list(payload.get("reason_tags")),
                "note": payload.get("note", ""),
            }
        )
        return jsonify({"feedback_id": feedback.id, "message": "Feedback saved"}), 201
    except Exception as exc:
        logger.exception("Feedback submission failed: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route('/api/jobs', methods=['GET'])
def jobs_api():
    profile_id = request.args.get("profile_id", type=int)
    if not profile_id:
        return jsonify({"error": "profile_id is required"}), 400

    run_id = request.args.get("run_id", type=int)
    min_score = request.args.get("min_score", default=0.0, type=float)
    limit = request.args.get("limit", default=100, type=int)
    include_explanations = bool(request.args.get("include_explanations", default=0, type=int))

    jobs = get_jobs_for_api(
        profile_id=profile_id,
        run_id=run_id,
        min_score=min_score,
        limit=limit,
        include_explanations=include_explanations,
    )
    return jsonify({"jobs": jobs})


@app.route('/api/agent/state', methods=['GET'])
def agent_state_api():
    profile_id = request.args.get("profile_id", type=int)
    if not profile_id:
        return jsonify({"error": "profile_id is required"}), 400

    try:
        return jsonify(get_agent_state(profile_id))
    except Exception as exc:
        logger.exception("Failed to fetch agent state: %s", exc)
        return jsonify({"error": str(exc)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
