import os
import json
import time
import requests
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from dotenv import load_dotenv

# ==========================================
# KONFIGURATION & API-SETUP
# ==========================================
load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
if not SERPAPI_KEY:
    raise ValueError("SERPAPI_KEY wurde nicht gefunden. Bitte prüfe die .env-Datei.")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "scraped_jobs.json")

# Such-Parameter
TARGET_CITIES = ["München", "Frankfurt", "Zürich", "Paris", "Berlin", "Stuttgart", "Basel", "Freiburg", "Köln", "Düsseldorf"]
JOB_DOMAINS = ["Computer Vision", "VLM", "VLA", "Robotik", "AI Research", "Machine Learning"]
JOB_TYPES = ["Internship", "Praktikum", "Intern"]

# ==========================================
# HILFSFUNKTIONEN
# ==========================================
def fetch_job_description(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            desc_div = soup.find('div', class_='show-more-less-html__markup')
            if desc_div:
                return desc_div.get_text(separator='\n', strip=True)
            else:
                return soup.body.get_text(separator='\n', strip=True)[:3000] 
        else:
            return None
    except Exception as e:
        print(f"Fehler beim Abrufen der URL {url}: {e}")
        return None

def run_google_dork(city, domain):
    query = f'site:linkedin.com/jobs/view ("Internship" OR "Praktikum") "{domain}" "{city}"'
    
    params = {
      "engine": "google",
      "q": query,
      "api_key": SERPAPI_KEY,
      "num": 5, 
      "hl": "en"
    }

    print(f"  -> Suche nach: {query}")
    search = GoogleSearch(params)
    results = search.get_dict()
    
    return results.get("organic_results", [])

# ==========================================
# HAUPT-WORKFLOW
# ==========================================
def main():
    print("Starte Job-Scraper für AI-Praktika...\n")
    all_scraped_jobs = []

    test_cities = TARGET_CITIES[:3]
    test_domains = JOB_DOMAINS[:2]

    for city in test_cities:
        for domain in test_domains:
            search_results = run_google_dork(city, domain)
            
            for result in search_results:
                link = result.get("link")
                title = result.get("title")
                snippet = result.get("snippet", "")
                
                if link and "linkedin.com/jobs/view" in link:
                    print(f"    Gefunden: {title}")
                    
                    job_text = fetch_job_description(link)
                    
                    if not job_text:
                        job_text = snippet
                    
                    job_data = {
                        "url": link,
                        "title": title,
                        "city": city,
                        "domain": domain,
                        "raw_text": job_text
                    }
                    all_scraped_jobs.append(job_data)
                    
            time.sleep(2)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_scraped_jobs, f, ensure_ascii=False, indent=4)
        
    print(f"\nScraping abgeschlossen! {len(all_scraped_jobs)} Jobs wurden in {OUTPUT_FILE} gespeichert.")

if __name__ == "__main__":
    main()