#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup

def debug_remoteok():
    print("Debugging RemoteOK HTML structure...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    search_url = "https://remoteok.io/remote-jobs?search=Developer"
    
    try:
        resp = requests.get(search_url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Look for different job containers
        print(f"Page title: {soup.title.get_text() if soup.title else 'No title'}")
        
        # Try different selectors
        selectors_to_try = [
            ('tr.job', 'Table rows with class job'),
            ('tr[data-url]', 'Table rows with data-url'),
            ('div.job', 'Div with class job'),
            ('.job-board tr', 'Job board table rows'),
            ('table tr', 'All table rows'),
            ('.job-list .job', 'Job list items')
        ]
        
        for selector, description in selectors_to_try:
            elements = soup.select(selector)
            print(f"\n{description}: Found {len(elements)} elements")
            
            if elements and len(elements) > 0:
                first_element = elements[0]
                print(f"First element HTML (truncated):")
                print(str(first_element)[:500])
                
                # Look for text content
                text_content = first_element.get_text(strip=True)
                if text_content:
                    print(f"Text content: {text_content[:200]}")
                
                break
        
        # Also check if it's a SPA (Single Page Application)
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and ('jobs' in script.string.lower() or 'job' in script.string.lower()):
                print(f"\nFound potential job data in script tag:")
                print(script.string[:300])
                break
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_remoteok()