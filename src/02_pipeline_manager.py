import os
import json
import re
import requests
import markdown
import pdfkit
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from dotenv import load_dotenv

# ==========================================
# KONFIGURATION & API-SETUP
# ==========================================
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY or "dein_" in GEMINI_API_KEY.lower():
    raise ValueError("GEMINI_API_KEY ungültig. Bitte trage deinen echten Key in die .env-Datei ein.")

client = genai.Client(api_key=GEMINI_API_KEY)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSOT_PATH = os.path.join(BASE_DIR, "data", "ssot_profile.json")
SCRAPED_JOBS_PATH = os.path.join(BASE_DIR, "data", "scraped_jobs.json")
EVAL_PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "job_evaluator_prompt.md")
CV_PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "cv_system_prompt.md")
TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "cv_template.md")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "ready_to_send")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return file.read()

def evaluate_job(job_info, ssot_data, eval_prompt):
    print("\n[Phase 1] Analysiere Job-Match...")
    full_prompt = f"{eval_prompt}\n\n---\nSSOT_PROFILE:\n{ssot_data}\n\n---\nTARGET_JOB:\n{job_info.get('full_job_prompt', job_info.get('raw_text', ''))}"
    
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=full_prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    
    try:
        eval_dict = json.loads(response.text)
        if eval_dict.get("extracted_company", "Nicht angegeben") in ["Nicht angegeben", "Unknown_Company"]:
            eval_dict["extracted_company"] = job_info.get("company", "Unknown_Company")
        if eval_dict.get("extracted_role", "Nicht angegeben") in ["Nicht angegeben", "Unknown_Role"]:
            eval_dict["extracted_role"] = job_info.get("role", job_info.get("title", "Unknown_Role"))
        return eval_dict
    except Exception as e:
        print(f"Fehler beim Parsen der API-Antwort: {e}")
        return {"match": False, "fit_score": 0, "reasoning": "JSON Parsing Error"}

def generate_application(job_info, ssot_data, cv_prompt, template):
    print("[Phase 2] Erstelle maßgeschneiderten Lebenslauf und Anschreiben...")
    full_prompt = f"{cv_prompt}\n\nHier ist das Template:\n{template}\n\n---\nSSOT_PROFILE:\n{ssot_data}\n\n---\nTARGET_JOB:\n{job_info.get('full_job_prompt', job_info.get('raw_text', ''))}"
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=full_prompt
    )
    return response.text

def convert_markdown_to_styled_html(markdown_text):
    parts = re.split(r'<!--\s*PAGE_BREAK\s*-->|&lt;!--\s*PAGE_BREAK\s*--&gt;', markdown_text)
    
    html_parts = []
    for index, part in enumerate(parts):
        raw_html = markdown.markdown(part.strip(), extensions=['tables', 'fenced_code', 'attr_list'])
        if index == 0:
            raw_html = re.sub(r'<h1>\s*ANSCHREIBEN\s*</h1>', '', raw_html, flags=re.IGNORECASE)
            html_parts.append(f'<div class="section-anschreiben">{raw_html}</div>')
        else:
            raw_html = re.sub(r'<h1>\s*LEBENSLAUF\s*</h1>', '', raw_html, flags=re.IGNORECASE)
            html_parts.append(f'<div class="section-lebenslauf">{raw_html}</div>')
            
    content_html = '<div class="page-break"></div>'.join(html_parts)
    
    styled_html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <title>Bewerbungsunterlagen - Gregor Nottmeier</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 8.8pt;
            line-height: 1.36;
            color: #1e293b;
            background-color: #ffffff;
            margin: 0; padding: 0;
        }}
        .page-break {{ page-break-before: always; page-break-after: always; clear: both; display: block; height: 0; }}
        .section-anschreiben {{ font-size: 9.2pt; line-height: 1.45; }}
        .section-lebenslauf {{ font-size: 8.8pt; line-height: 1.35; }}
        h1 {{ font-size: 15pt; font-weight: 700; color: #0f172a; margin-top: 0; margin-bottom: 4px; border-bottom: 2px solid #2563eb; }}
        h2 {{ font-size: 10pt; font-weight: 600; color: #1e3a8a; text-transform: uppercase; margin-top: 10px; margin-bottom: 4px; border-bottom: 1px solid #cbd5e1; }}
        h3 {{ font-size: 9.2pt; font-weight: 600; color: #0f172a; margin-top: 6px; margin-bottom: 2px; }}
        p {{ margin-top: 0; margin-bottom: 5px; }}
        ul {{ margin-top: 2px; margin-bottom: 6px; padding-left: 14px; }}
        li {{ margin-bottom: 2px; }}
        strong {{ color: #0f172a; font-weight: 600; }}
        hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 8px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 4px; margin-bottom: 8px; }}
        th {{ background-color: #f1f5f9; color: #0f172a; padding: 4px 6px; border-bottom: 2px solid #cbd5e1; font-size: 8.5pt; }}
        td {{ padding: 4px 6px; border-bottom: 1px solid #e2e8f0; font-size: 8.5pt; }}
        code {{ background-color: #eff6ff; color: #1d4ed8; padding: 1px 5px; border-radius: 3px; font-size: 8.2pt; font-family: 'Inter', sans-serif; font-weight: 500; border: 1px solid #bfdbfe; }}
    </style>
</head>
<body>
    {content_html}
</body>
</html>"""
    return styled_html

def main():
    try:
        ssot_data = read_file(SSOT_PATH)
        eval_prompt = read_file(EVAL_PROMPT_PATH)
        cv_prompt = read_file(CV_PROMPT_PATH)
        cv_template = read_file(TEMPLATE_PATH)
    except FileNotFoundError as e:
        print(f"Fehler: Datei nicht gefunden. {e}")
        return

    if not os.path.exists(SCRAPED_JOBS_PATH):
        print(f"Keine gescrapten Jobs gefunden unter {SCRAPED_JOBS_PATH}. Führe zuerst 01_job_scraper.py aus.")
        return

    with open(SCRAPED_JOBS_PATH, 'r', encoding='utf-8') as f:
        scraped_jobs = json.load(f)

    print(f"{len(scraped_jobs)} Jobs geladen. Starte Evaluierung...\n")

    for index, job in enumerate(scraped_jobs, start=1):
        job_text = job.get("raw_text", "")
        title = job.get("title", "Unknown Title")
        print(f"\n--- Verarbeite Job {index}/{len(scraped_jobs)}: {title} ---")
        
        if not job_text:
            print("Kein Text vorhanden. Überspringe...")
            continue

        evaluation_result = evaluate_job(job, ssot_data, eval_prompt)
        company = evaluation_result.get("extracted_company", "Unknown_Company")
        is_match = evaluation_result.get("match", False)
        score = evaluation_result.get("fit_score", 0)
        reasoning = evaluation_result.get("reasoning", "")
        
        print(f"Unternehmen: {company}")
        print(f"Match: {is_match} | Fit-Score: {score}/100")
        print(f"Begründung: {reasoning}")
        
        if is_match and score >= 75:
            print("--> Match erfolgreich! Starte Dokumentengenerierung...")
            final_document = generate_application(job, ssot_data, cv_prompt, cv_template)
            
            clean_company = re.sub(r'[^\w\-]', '_', company).strip('_')
            clean_title = re.sub(r'[^\w\-]', '_', title).strip('_')
            base_filename = f"{clean_company}_{clean_title}"
            
            md_file_path = os.path.join(OUTPUT_DIR, f"{base_filename}.md")
            pdf_file_path = os.path.join(OUTPUT_DIR, f"{base_filename}.pdf")
            
            with open(md_file_path, 'w', encoding='utf-8') as out_f:
                out_f.write(final_document)
                
            styled_html = convert_markdown_to_styled_html(final_document)
            
            pdf_options = {
                'page-size': 'A4',
                'margin-top': '10mm',
                'margin-bottom': '10mm',
                'margin-left': '14mm',
                'margin-right': '14mm',
                'encoding': 'UTF-8',
                'enable-local-file-access': None,
                'quiet': ''
            }
            pdfkit.from_string(styled_html, pdf_file_path, options=pdf_options)
            
            print(f"Erfolg! Bewerbungsmappe gespeichert unter:")
            print(f" - Markdown: {md_file_path}")
            print(f" - PDF:      {pdf_file_path}")
        else:
            print("--> Stelle abgelehnt. Überspringe.")

if __name__ == "__main__":
    main()