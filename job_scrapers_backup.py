import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from uuid import uuid4
import re

def scrape_naukri(keyword: str, location: str, days: int, job_setting: Optional[str], exclude_keywords: List[str], company_size: Optional[str]) -> List[Dict[str, Any]]:
    """Scrape Naukri.com for job listings."""
    jobs = []
    base_url = "https://www.naukri.com/"
    params = {
        'k': keyword,
        'l': location,
        'jobAge': days,
    }
    # Naukri URL pattern
    search_url = f"{base_url}{keyword.replace(' ', '-')}-jobs-in-{location.replace(' ', '-')}"
    try:
        resp = requests.get(search_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        job_cards = soup.find_all('article', {'class': 'jobTuple'})
        for card in job_cards:
            title = card.find('a', {'class': 'title'}).get_text(strip=True) if card.find('a', {'class': 'title'}) else ''
            company = card.find('a', {'class': 'subTitle'}).get_text(strip=True) if card.find('a', {'class': 'subTitle'}) else ''
            desc = card.find('div', {'class': 'job-description'}).get_text(strip=True) if card.find('div', {'class': 'job-description'}) else ''
            location_ = card.find('li', {'class': 'location'}).get_text(strip=True) if card.find('li', {'class': 'location'}) else ''
            salary = card.find('li', {'class': 'salary'}).get_text(strip=True) if card.find('li', {'class': 'salary'}) else ''
            exp = card.find('li', {'class': 'experience'}).get_text(strip=True) if card.find('li', {'class': 'experience'}) else ''
            url = card.find('a', {'class': 'title'})['href'] if card.find('a', {'class': 'title'}) else ''
            # Exclude keywords
            if any(kw.lower() in desc.lower() for kw in exclude_keywords):
                continue
            # Parse salary
            salary_min, salary_max = None, None
            if salary:
                match = re.findall(r'\d+', salary.replace(',', ''))
                if match:
                    salary_min = int(match[0]) if len(match) > 0 else None
                    salary_max = int(match[1]) if len(match) > 1 else None
            job = {
                "job_id": str(uuid4()),
                "title": title,
                "company_name": company,
                "company_id": "",
                "description": desc,
                "requirements": "",
                "salary_min": salary_min,
                "salary_max": salary_max,
                "location": location_,
                "remote_type": job_setting or '',
                "employment_type": '',
                "experience_level": exp,
                "industry": '',
                "source": 'naukri',
                "source_url": url
            }
            jobs.append(job)
    except Exception as e:
        print(f"[Naukri] Error: {e}")
    return jobs

def scrape_indeed(keyword: str, location: str, days: int, job_setting: Optional[str], exclude_keywords: List[str], company_size: Optional[str]) -> List[Dict[str, Any]]:
    """Scrape Indeed.com for job listings with better anti-bot measures."""
    jobs = []
    
    try:
        # Multiple Indeed domains to try
        indeed_domains = [
            "https://in.indeed.com/jobs",  # India
            "https://www.indeed.com/jobs",  # US
            "https://ca.indeed.com/jobs",   # Canada
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': 'https://www.google.com/',
            'Upgrade-Insecure-Requests': '1',
        }
        
        for base_url in indeed_domains:
            try:
                print(f"[Indeed] Trying {base_url}")
                
                # Try multiple pages for more results
                for page in range(0, 5):  # 5 pages = ~150 jobs
                    params = {
                        'q': keyword,
                        'l': location,
                        'fromage': days,
                        'start': page * 10  # Indeed shows 10 jobs per page by default
                    }
                    
                    # Add remote filter if specified
                    if job_setting == 'remote':
                        params['remotejob'] = '032b3046-06a3-4876-8dfd-474eb5e7ed11'
                    
                    import time
                    time.sleep(1)  # Rate limiting
        resp = requests.get(base_url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Indeed job cards have different class names - using multiple selectors
        job_cards = soup.find_all('div', {'class': 'job_seen_beacon'}) or soup.find_all('div', {'data-jk': True})
        
        for card in job_cards[:20]:  # Limit to first 20 results
            try:
                # Extract job title
                title_elem = card.find('h2', {'class': 'jobTitle'}) or card.find('a', {'data-jk': True})
                title = title_elem.get_text(strip=True) if title_elem else ''
                
                # Extract company name
                company_elem = card.find('span', {'class': 'companyName'}) or card.find('a', {'data-testid': 'company-name'})
                company = company_elem.get_text(strip=True) if company_elem else ''
                
                # Extract location
                location_elem = card.find('div', {'data-testid': 'job-location'}) or card.find('div', {'class': 'companyLocation'})
                job_location = location_elem.get_text(strip=True) if location_elem else ''
                
                # Extract job summary/description
                summary_elem = card.find('div', {'class': 'summary'}) or card.find('div', {'data-testid': 'job-snippet'})
                description = summary_elem.get_text(strip=True) if summary_elem else ''
                
                # Extract salary if available
                salary_elem = card.find('span', {'class': 'salary-snippet'}) or card.find('div', {'data-testid': 'attribute_snippet_testid'})
                salary_text = salary_elem.get_text(strip=True) if salary_elem else ''
                
                # Extract job URL
                link_elem = title_elem.find('a') if title_elem else None
                job_url = f"https://www.indeed.com{link_elem['href']}" if link_elem and link_elem.get('href') else ''
                
                # Skip if exclude keywords found
                if any(kw.lower() in description.lower() or kw.lower() in title.lower() for kw in exclude_keywords):
                    continue
                
                # Parse salary
                salary_min, salary_max = None, None
                if salary_text:
                    # Extract numbers from salary text
                    numbers = re.findall(r'\d+(?:,\d+)*', salary_text.replace('$', '').replace('₹', ''))
                    if numbers:
                        try:
                            salary_min = int(numbers[0].replace(',', ''))
                            salary_max = int(numbers[1].replace(',', '')) if len(numbers) > 1 else None
                        except ValueError:
                            pass
                
                # Determine remote type from job location or title
                remote_type = job_setting or ''
                if not remote_type:
                    if any(term in job_location.lower() for term in ['remote', 'work from home']):
                        remote_type = 'remote'
                    elif 'hybrid' in job_location.lower():
                        remote_type = 'hybrid'
                    else:
                        remote_type = 'onsite'
                
                job = {
                    "job_id": str(uuid4()),
                    "title": title,
                    "company_name": company,
                    "company_id": "",
                    "description": description,
                    "requirements": "",
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "location": job_location,
                    "remote_type": remote_type,
                    "employment_type": "full_time",  # Indeed doesn't always specify, defaulting
                    "experience_level": "",
                    "industry": "",
                    "source": "indeed",
                    "source_url": job_url
                }
                jobs.append(job)
                
            except Exception as e:
                print(f"[Indeed] Error parsing job card: {e}")
                continue
                
    except Exception as e:
        print(f"[Indeed] Error fetching jobs: {e}")
    
    return jobs
def scrape_remoteok(keyword: str, location: str, days: int, job_setting: Optional[str], exclude_keywords: List[str], company_size: Optional[str]) -> List[Dict[str, Any]]:
    """Scrape RemoteOK.io for remote job listings using JSON API."""
    jobs = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Try RemoteOK JSON API
        api_url = "https://remoteok.io/api"
        print(f"[RemoteOK] Fetching jobs from API...")
        
        resp = requests.get(api_url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        data = resp.json()
        print(f"[RemoteOK] API returned {len(data)} items")
        
        if isinstance(data, list) and len(data) > 1:
            # Skip first item (usually metadata), process jobs
            job_count = 0
            for item in data[1:]:  # Skip metadata
                try:
                    if not isinstance(item, dict):
                        continue
                    
                    # Extract job data
                    title = item.get('position', '') or item.get('title', '')
                    company = item.get('company', '')
                    description = item.get('description', '') or item.get('tags', '')
                    job_url = item.get('url', '')
                    salary_min = item.get('salary_min')
                    salary_max = item.get('salary_max')
                    
                    # Convert tags array to string if needed
                    if isinstance(description, list):
                        description = ' '.join(description)
                    
                    # Filter by keyword
                    if keyword.lower() not in title.lower() and keyword.lower() not in str(description).lower():
                        continue
                    
                    # Skip if exclude keywords found
                    text_to_check = f"{title} {description}".lower()
                    if any(kw.lower() in text_to_check for kw in exclude_keywords):
                        continue
                    
                    # Ensure we have basic data
                    if not title or not company:
                        continue
                    
                    # Add full URL if relative
                    if job_url and not job_url.startswith('http'):
                        job_url = f"https://remoteok.io{job_url}"
                    
                    # Extract experience level from description/tags
                    experience_level = ''
                    desc_lower = str(description).lower()
                    if any(term in desc_lower for term in ['senior', 'sr.', 'lead', 'principal']):
                        experience_level = 'Senior'
                    elif any(term in desc_lower for term in ['junior', 'jr.', 'entry', 'graduate']):
                        experience_level = 'Junior'
                    elif any(term in desc_lower for term in ['mid', 'intermediate']):
                        experience_level = 'Mid-Level'
                    
                    job = {
                        "job_id": item.get('id', str(uuid4())),
                        "title": title,
                        "company_name": company,
                        "company_id": "",
                        "description": str(description),
                        "requirements": "",
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "location": "Remote",
                        "remote_type": "remote",
                        "employment_type": "full_time",
                        "experience_level": experience_level,
                        "industry": "",
                        "source": "remoteok",
                        "source_url": job_url or f"https://remoteok.io"
                    }
                    jobs.append(job)
                    job_count += 1
                    
                    # Limit to reasonable number for performance
                    if job_count >= 100:
                        break
                        
                except Exception as e:
                    print(f"[RemoteOK] Error parsing job item: {e}")
                    continue
        
        print(f"[RemoteOK] Successfully parsed {len(jobs)} jobs matching '{keyword}'")
        
    except Exception as e:
        print(f"[RemoteOK] Error fetching jobs: {e}")
    
    return jobs
def scrape_wellfound(keyword: str, location: str, days: int, job_setting: Optional[str], exclude_keywords: List[str], company_size: Optional[str]) -> List[Dict[str, Any]]:
    """Scrape Wellfound (formerly AngelList) for startup job listings."""
    jobs = []
    base_url = "https://wellfound.com/jobs"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Wellfound search parameters
        params = {
            'role': keyword,
            'location': location if location.lower() != 'remote' else '',
            'remote': 'true' if location.lower() == 'remote' or job_setting == 'remote' else 'false'
        }
        
        resp = requests.get(base_url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Wellfound job cards - they use various class names
        job_cards = soup.find_all('div', {'data-testid': 'JobCard'}) or soup.find_all('div', class_=re.compile(r'job.*card|card.*job', re.I))
        
        for card in job_cards[:15]:  # Limit to first 15 results
            try:
                # Extract job title
                title_elem = (card.find('h2') or 
                             card.find('a', class_=re.compile(r'job.*title|title.*job', re.I)) or
                             card.find('div', class_=re.compile(r'job.*title|title.*job', re.I)))
                title = title_elem.get_text(strip=True) if title_elem else ''
                
                # Extract company name
                company_elem = (card.find('h3') or 
                               card.find('div', class_=re.compile(r'company.*name|startup.*name', re.I)) or
                               card.find('a', class_=re.compile(r'company.*link', re.I)))
                company = company_elem.get_text(strip=True) if company_elem else ''
                
                # Extract location
                location_elem = card.find('div', class_=re.compile(r'location', re.I)) or card.find('span', class_=re.compile(r'location', re.I))
                job_location = location_elem.get_text(strip=True) if location_elem else location
                
                # Extract job description/summary
                desc_elem = (card.find('div', class_=re.compile(r'description|summary', re.I)) or
                            card.find('p', class_=re.compile(r'description|summary', re.I)))
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                # Extract salary if available
                salary_elem = card.find('div', class_=re.compile(r'salary|compensation', re.I))
                salary_text = salary_elem.get_text(strip=True) if salary_elem else ''
                
                # Extract experience level
                exp_elem = card.find('div', class_=re.compile(r'experience|level', re.I))
                experience = exp_elem.get_text(strip=True) if exp_elem else ''
                
                # Extract job URL
                link_elem = card.find('a')
                job_url = ''
                if link_elem and link_elem.get('href'):
                    href = link_elem['href']
                    job_url = href if href.startswith('http') else f"https://wellfound.com{href}"
                
                # Skip if exclude keywords found
                if any(kw.lower() in description.lower() or kw.lower() in title.lower() for kw in exclude_keywords):
                    continue
                
                # Parse salary
                salary_min, salary_max = None, None
                if salary_text:
                    # Wellfound often shows equity ranges or salary ranges
                    numbers = re.findall(r'\d+(?:,\d+)*', salary_text.replace('$', '').replace('k', '000'))
                    if numbers:
                        try:
                            if 'k' in salary_text.lower():
                                salary_min = int(numbers[0].replace(',', '')) * 1000 if numbers else None
                                salary_max = int(numbers[1].replace(',', '')) * 1000 if len(numbers) > 1 else None
                            else:
                                salary_min = int(numbers[0].replace(',', ''))
                                salary_max = int(numbers[1].replace(',', '')) if len(numbers) > 1 else None
                        except ValueError:
                            pass
                
                # Determine remote type
                remote_type = job_setting or ''
                if not remote_type:
                    if any(term in job_location.lower() for term in ['remote', 'anywhere']):
                        remote_type = 'remote'
                    elif 'hybrid' in job_location.lower():
                        remote_type = 'hybrid'
                    else:
                        remote_type = 'onsite'
                
                # Parse experience level
                experience_level = ''
                if experience:
                    if any(term in experience.lower() for term in ['senior', 'sr', 'lead']):
                        experience_level = 'Senior'
                    elif any(term in experience.lower() for term in ['junior', 'jr', 'entry']):
                        experience_level = 'Junior'
                    elif any(term in experience.lower() for term in ['mid', 'intermediate']):
                        experience_level = 'Mid-Level'
                
                job = {
                    "job_id": str(uuid4()),
                    "title": title,
                    "company_name": company,
                    "company_id": "",
                    "description": description,
                    "requirements": "",
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "location": job_location,
                    "remote_type": remote_type,
                    "employment_type": "full_time",
                    "experience_level": experience_level,
                    "industry": "Technology/Startup",  # Wellfound focuses on startups
                    "source": "wellfound",
                    "source_url": job_url
                }
                jobs.append(job)
                
            except Exception as e:
                print(f"[Wellfound] Error parsing job card: {e}")
                continue
                
    except Exception as e:
        print(f"[Wellfound] Error fetching jobs: {e}")
    
    return jobs
def scrape_linkedin(*args, **kwargs):
    print("LinkedIn scraping is not implemented due to authentication/anti-bot requirements.")
    return []
