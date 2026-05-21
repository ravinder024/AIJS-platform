import json
import csv
import os
from typing import List, Dict, Any
from datetime import datetime

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    print("Warning: gspread not available. Google Sheets functionality will be disabled.")

def save_to_json(jobs: List[Dict[str, Any]], filename: str = None) -> str:
    """Save job listings to JSON file."""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"job_listings_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(jobs)} jobs to {filename}")
        return filename
    except Exception as e:
        print(f"❌ Error saving to JSON: {e}")
        return ""

def save_to_csv(jobs: List[Dict[str, Any]], filename: str = None) -> str:
    """Save job listings to CSV file."""
    if not jobs:
        print("No jobs to save to CSV")
        return ""
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"job_listings_{timestamp}.csv"
    
    try:
        fieldnames = jobs[0].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(jobs)
        print(f"✅ Saved {len(jobs)} jobs to {filename}")
        return filename
    except Exception as e:
        print(f"❌ Error saving to CSV: {e}")
        return ""

def save_to_google_sheets(jobs: List[Dict[str, Any]], sheet_name: str = None, credentials_path: str = "credentials.json") -> bool:
    """Save job listings to Google Sheets."""
    if not GSPREAD_AVAILABLE:
        print("❌ gspread library not available. Install with: pip install gspread oauth2client")
        return False
    
    if not os.path.exists(credentials_path):
        print(f"❌ Google Sheets credentials file not found at {credentials_path}")
        print("Please download your service account credentials from Google Cloud Console")
        return False
    
    if not jobs:
        print("No jobs to save to Google Sheets")
        return False
    
    try:
        # Setup Google Sheets API
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        gc = gspread.authorize(credentials)
        
        # Create or open spreadsheet
        if not sheet_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sheet_name = f"Job_Listings_{timestamp}"
        
        try:
            # Try to open existing spreadsheet
            spreadsheet = gc.open(sheet_name)
            worksheet = spreadsheet.sheet1
        except gspread.SpreadsheetNotFound:
            # Create new spreadsheet
            spreadsheet = gc.create(sheet_name)
            worksheet = spreadsheet.sheet1
        
        # Clear existing data
        worksheet.clear()
        
        # Prepare data for Google Sheets
        if jobs:
            headers = list(jobs[0].keys())
            rows = [headers]
            
            for job in jobs:
                row = []
                for header in headers:
                    value = job.get(header, "")
                    # Convert None to empty string and ensure all values are strings
                    if value is None:
                        value = ""
                    elif not isinstance(value, str):
                        value = str(value)
                    row.append(value)
                rows.append(row)
            
            # Update the worksheet
            worksheet.update('A1', rows)
            
            print(f"✅ Saved {len(jobs)} jobs to Google Sheet: {sheet_name}")
            print(f"📊 Sheet URL: {spreadsheet.url}")
            return True
        
    except Exception as e:
        print(f"❌ Error saving to Google Sheets: {e}")
        return False

def save_jobs(jobs: List[Dict[str, Any]], output_format: str, filename: str = None) -> str:
    """Main function to save jobs based on specified format."""
    if not jobs:
        print("No jobs to save")
        return ""
    
    print(f"\n📊 Saving {len(jobs)} jobs in {output_format.upper()} format...")
    
    if output_format.lower() == 'json':
        return save_to_json(jobs, filename)
    elif output_format.lower() == 'csv':
        return save_to_csv(jobs, filename)
    elif output_format.lower() in ['gsheet', 'google_sheets', 'sheets']:
        success = save_to_google_sheets(jobs, filename)
        return "Google Sheets" if success else ""
    else:
        print(f"❌ Unknown output format: {output_format}")
        return ""

def print_job_summary(jobs: List[Dict[str, Any]]) -> None:
    """Print a summary of scraped jobs."""
    if not jobs:
        print("No jobs found")
        return
    
    print(f"\n📋 Job Scraping Summary:")
    print(f"Total jobs found: {len(jobs)}")
    
    # Group by source
    sources = {}
    for job in jobs:
        source = job.get('source', 'unknown')
        sources[source] = sources.get(source, 0) + 1
    
    print("\nJobs by source:")
    for source, count in sources.items():
        print(f"  {source.title()}: {count}")
    
    # Group by remote type
    remote_types = {}
    for job in jobs:
        remote_type = job.get('remote_type', 'unknown')
        remote_types[remote_type] = remote_types.get(remote_type, 0) + 1
    
    print("\nJobs by type:")
    for remote_type, count in remote_types.items():
        print(f"  {remote_type.title()}: {count}")
    
    # Show sample jobs
    print(f"\nSample jobs:")
    for i, job in enumerate(jobs[:3]):
        print(f"  {i+1}. {job.get('title', 'N/A')} at {job.get('company_name', 'N/A')} ({job.get('source', 'N/A')})")