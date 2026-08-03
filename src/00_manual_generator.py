import os
import sys
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
EVAL_PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "job_evaluator_prompt.md")
CV_PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "cv_system_prompt.md")
TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "cv_template.md")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "ready_to_send")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================================
# HILFSFUNKTIONEN & EXTRAKTION
# ==========================================
def fetch_job_description(url):
    print(f"\n[1] Lade und analysiere Job-Daten von URL: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Fehler: Webseite gab Status Code {response.status_code} zurück.")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Unternehmensname
        company = None
        comp_elem = soup.find('a', class_='topcard__org-name-link') or soup.find('a', class_='sub-nav-cta__optional-url')
        if comp_elem:
            company = comp_elem.get_text(strip=True)
        elif soup.title:
            title_text = soup.title.get_text()
            if " hiring " in title_text:
                company = title_text.split(" hiring ")[0].strip()
            elif " bei " in title_text:
                company = title_text.split(" bei ")[1].split("|")[0].strip()

        # 2. Stellenbezeichnung (Role)
        role = None
        role_elem = soup.find('h1', class_='top-card-layout__title') or soup.find('h3', class_='sub-nav-cta__header')
        if role_elem:
            role = role_elem.get_text(strip=True)
        elif soup.title:
            title_text = soup.title.get_text()
            if " hiring " in title_text:
                role = title_text.split(" hiring ")[1].split(" in ")[0].split("|")[0].strip()

        # 3. Standort (Location)
        location = None
        loc_elem = soup.find('span', class_='topcard__flavor--bullet') or soup.find('span', class_='sub-nav-cta__meta-text')
        if loc_elem:
            location = loc_elem.get_text(strip=True)

        # 4. Haupt-Stellenbeschreibung
        desc_text = ""
        desc_div = soup.find('div', class_='show-more-less-html__markup')
        if desc_div:
            desc_text = desc_div.get_text(separator='\n', strip=True)
        else:
            desc_text = soup.body.get_text(separator='\n', strip=True)[:3000]

        # 5. Ansprechperson suchen (falls im Text erwähnt)
        contact = "Nicht angegeben"
        contact_match = re.search(r'(?:Ansprechpartner|Ansprechperson|Recruiter|Contact|Hiring Manager)\s*:\s*([A-Za-zÄöüß\s\.\-]+)', desc_text, re.IGNORECASE)
        if contact_match:
            contact = contact_match.group(1).strip()

        metadata_block = f"""METADATEN DER STELLENANZEIGE:
- Unternehmen (Company): {company or 'Nicht angegeben'}
- Stellenbezeichnung (Role): {role or 'Nicht angegeben'}
- Standort (Location): {location or 'Nicht angegeben'}
- Ansprechperson (Contact): {contact}

STELLENBESCHREIBUNG:
{desc_text}"""

        return {
            "company": company or "Nicht angegeben",
            "role": role or "Nicht angegeben",
            "location": location or "Nicht angegeben",
            "contact": contact,
            "raw_text": desc_text,
            "full_job_prompt": metadata_block
        }

    except Exception as e:
        print(f"Fehler beim Abrufen der URL: {e}")
        return None

def evaluate_job(job_info, ssot_data, eval_prompt):
    print("[2] Evaluiere Job-Match mit deinem Profil...")
    full_prompt = f"{eval_prompt}\n\n---\nSSOT_PROFILE:\n{ssot_data}\n\n---\nTARGET_JOB:\n{job_info['full_job_prompt']}"
    
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=full_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    try:
        eval_dict = json.loads(response.text)
        if eval_dict.get("extracted_company", "Nicht angegeben") in ["Nicht angegeben", "Unknown_Company"]:
            eval_dict["extracted_company"] = job_info["company"]
        if eval_dict.get("extracted_role", "Nicht angegeben") in ["Nicht angegeben", "Unknown_Role"]:
            eval_dict["extracted_role"] = job_info["role"]
        if "extracted_location" not in eval_dict or eval_dict["extracted_location"] == "Nicht angegeben":
            eval_dict["extracted_location"] = job_info["location"]
        if "extracted_contact" not in eval_dict:
            eval_dict["extracted_contact"] = job_info["contact"]
        if "detected_language" not in eval_dict or eval_dict["detected_language"] not in ["de", "en"]:
            eval_dict["detected_language"] = "de"
        return eval_dict
    except Exception as e:
        print(f"JSON Parsing Error bei Evaluierung: {e}")
        return {
            "match": False,
            "fit_score": 0,
            "reasoning": f"JSON Parsing Error: {e}",
            "detected_language": "de",
            "extracted_company": job_info["company"],
            "extracted_role": job_info["role"],
            "extracted_location": job_info["location"],
            "extracted_contact": job_info["contact"]
        }

def generate_application(job_info, ssot_data, cv_prompt, template, language="de"):
    print(f"[3] Erstelle maßgeschneiderten Lebenslauf und Anschreiben (Sprache: {language.upper()})...")
    lang_instruction = f"WICHTIGE SPRACHVORGABE: Generiere BEIDE Dokumente (Anschreiben & Lebenslauf) strikt auf {'Englisch' if language == 'en' else 'Deutsch'}!"
    full_prompt = f"{cv_prompt}\n\n{lang_instruction}\n\nHier ist das Template / Referenz:\n{template}\n\n---\nSSOT_PROFILE:\n{ssot_data}\n\n---\nTARGET_JOB:\n{job_info['full_job_prompt']}"
    
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=full_prompt
    )
    return response.text

def convert_markdown_to_styled_html(markdown_text, doc_type="cover_letter", language="de"):
    if doc_type == "cover_letter":
        # Remove any accidental backticks so frameworks/packages in cover letter prose render as normal text
        markdown_text = re.sub(r'`([^`]+)`', r'\1', markdown_text)
        raw_html = markdown.markdown(markdown_text.strip(), extensions=['tables', 'fenced_code', 'attr_list'])
        raw_html = re.sub(r'<h1>\s*(ANSCHREIBEN|COVER LETTER)\s*</h1>', '', raw_html, flags=re.IGNORECASE)
        content_html = f'<div class="section-anschreiben">{raw_html}</div>'
    else:
        # 1. Strip list bullet markers (- or *) from project and experience category headers
        markdown_text = re.sub(r'^\s*[\*\-]\s+(\*\*(?:Technical Implementation|Impact & Results|Impact|Technical Realization|Core Responsibilities & Impact)\:?\*\*)', r'\1', markdown_text, flags=re.MULTILINE | re.IGNORECASE)
        # 2. Standardize bold section category labels and remove any accidental asterisks surrounding category headers
        markdown_text = re.sub(r'\*+(Technical Implementation|Impact & Results|Impact|Technical Realization|Core Responsibilities & Impact)\:?\*+', r'**\1:**', markdown_text, flags=re.IGNORECASE)
        raw_html = markdown.markdown(markdown_text.strip(), extensions=['tables', 'fenced_code', 'attr_list'])
        raw_html = re.sub(r'<h1>\s*(LEBENSLAUF|CV|RESUME)\s*</h1>', '', raw_html, flags=re.IGNORECASE)
        content_html = f'<div class="section-lebenslauf">{raw_html}</div>'
        
    styled_html = f"""<!DOCTYPE html>
<html lang="{language}">
<head>
    <meta charset="utf-8">
    <title>Bewerbungsunterlagen - Gregor Nottmeier</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {{
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            font-size: 8.8pt;
            line-height: 1.36;
            color: #1e293b;
            background-color: #ffffff;
            margin: 0;
            padding: 0;
        }}
        
        .section-anschreiben {{
            font-size: 9.2pt;
            line-height: 1.45;
        }}

        .section-anschreiben code {{
            background-color: transparent !important;
            color: inherit !important;
            padding: 0 !important;
            border-radius: 0 !important;
            font-size: inherit !important;
            font-family: inherit !important;
            border: none !important;
        }}
        
        .section-lebenslauf {{
            font-size: 8.8pt;
            line-height: 1.36;
        }}

        .section-lebenslauf h2 {{
            font-size: 10pt;
            font-weight: 700;
            color: #1e3a8a;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 11px;
            margin-bottom: 5px;
            padding-bottom: 2px;
            border-bottom: 1.5px solid #cbd5e1;
        }}
        
        .section-lebenslauf h3 {{
            font-size: 9.5pt;
            font-weight: 700;
            color: #0f172a;
            margin-top: 8px;
            margin-bottom: 2px;
        }}

        .section-lebenslauf p {{
            margin-top: 0;
            margin-bottom: 4px;
        }}

        .section-lebenslauf strong,
        .section-lebenslauf p strong,
        .section-lebenslauf li strong {{
            color: #1e3a8a !important;
            font-weight: 600;
        }}

        .section-lebenslauf p em {{
            color: #475569;
            font-style: normal;
        }}

        .section-lebenslauf ul {{
            margin-top: 2px;
            margin-bottom: 6px;
            padding-left: 0 !important;
            list-style-type: none !important;
        }}
        
        .section-lebenslauf li {{
            margin-bottom: 3px;
            line-height: 1.38;
            color: #1e293b;
            list-style-type: none !important;
            padding-left: 0 !important;
        }}
        
        /* Headings Styling */
        h1 {{
            font-size: 15pt;
            font-weight: 700;
            color: #0f172a;
            letter-spacing: -0.3px;
            margin-top: 0;
            margin-bottom: 4px;
            padding-bottom: 3px;
            border-bottom: 2px solid #2563eb;
        }}
        
        h2 {{
            font-size: 10pt;
            font-weight: 600;
            color: #1e3a8a;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            margin-top: 10px;
            margin-bottom: 4px;
            padding-bottom: 2px;
            border-bottom: 1px solid #cbd5e1;
        }}
        
        h3 {{
            font-size: 9.2pt;
            font-weight: 600;
            color: #0f172a;
            margin-top: 6px;
            margin-bottom: 2px;
        }}
        
        p {{
            margin-top: 0;
            margin-bottom: 5px;
        }}
        
        ul {{
            margin-top: 2px;
            margin-bottom: 6px;
            padding-left: 0;
            list-style-type: none;
        }}
        
        li {{
            margin-bottom: 3px;
            line-height: 1.38;
            color: #1e293b;
            list-style-type: none;
        }}
        
        strong {{
            color: #1e3a8a;
            font-weight: 600;
        }}
        
        em {{
            color: #475569;
        }}

        hr {{
            border: none;
            border-top: 1px solid #e2e8f0;
            margin: 8px 0;
        }}

        /* Table Styling */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 4px;
            margin-bottom: 8px;
        }}
        
        th {{
            background-color: #f1f5f9;
            color: #0f172a;
            font-weight: 600;
            text-align: left;
            padding: 4px 6px;
            border-bottom: 2px solid #cbd5e1;
            font-size: 8.5pt;
        }}
        
        td {{
            padding: 4px 6px;
            border-bottom: 1px solid #e2e8f0;
            font-size: 8.5pt;
            vertical-align: top;
        }}

        /* Code & Badge formatting */
        code {{
            background-color: #f1f5f9;
            color: #1e3a8a;
            padding: 1px 4px;
            border-radius: 3px;
            font-size: 8pt;
            font-family: 'Inter', sans-serif;
            font-weight: 500;
            border: 1px solid #cbd5e1;
        }}
    </style>
</head>
<body>
    {content_html}
</body>
</html>"""
    return styled_html

def trim_least_important_experience(md_text):
    pattern = r'(##\s*(?:PROFESSIONAL EXPERIENCE|BERUFSERFAHRUNG|WORK EXPERIENCE).*?)(?=\n##\s+|\Z)'
    match = re.search(pattern, md_text, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        return md_text, False

    section_text = match.group(1)
    entries = re.split(r'(\n###\s+)', section_text)
    
    if len(entries) <= 3:
        return md_text, False
        
    trimmed_section = "".join(entries[:-2]).strip()
    new_md_text = md_text[:match.start(1)] + trimmed_section + "\n\n" + md_text[match.end(1):]
    return new_md_text, True

def render_cv_pdf_with_page_limit(cv_md_path, cv_pdf_path, pdf_options, language="en"):
    with open(cv_md_path, 'r', encoding='utf-8') as f:
        cv_md = f.read()

    cv_html = convert_markdown_to_styled_html(cv_md, doc_type="cv", language=language)
    pdfkit.from_string(cv_html, cv_pdf_path, options=pdf_options)

    try:
        import fitz
        doc = fitz.open(cv_pdf_path)
        page_count = len(doc)
        doc.close()
    except Exception as e:
        print(f"[PAGE CHECK] Could not check PDF page count: {e}")
        return

    while page_count > 1:
        print(f"[AUTO-PAGE-FIT] CV PDF is {page_count} pages (exceeds 1 page limit). Trimming least important entry from Professional Experience...")
        new_cv_md, trimmed = trim_least_important_experience(cv_md)
        if not trimmed:
            print("[AUTO-PAGE-FIT] Reached minimum entries in Professional Experience, cannot trim further.")
            break
        
        cv_md = new_cv_md
        with open(cv_md_path, 'w', encoding='utf-8') as f:
            f.write(cv_md)
            
        cv_html = convert_markdown_to_styled_html(cv_md, doc_type="cv", language=language)
        pdfkit.from_string(cv_html, cv_pdf_path, options=pdf_options)

        doc = fitz.open(cv_pdf_path)
        page_count = len(doc)
        doc.close()
        print(f"[AUTO-PAGE-FIT] New CV PDF page count: {page_count}")

# ==========================================
# HAUPT-WORKFLOW
# ==========================================
def main():
    if len(sys.argv) < 2:
        print("Fehler: Du musst einen LinkedIn-Link angeben!")
        print("Nutzung: python src/00_manual_generator.py 'DEIN_LINK_HIER'")
        sys.exit(1)

    url = sys.argv[1]

    try:
        with open(SSOT_PATH, 'r', encoding='utf-8') as f: ssot_data = f.read()
        with open(EVAL_PROMPT_PATH, 'r', encoding='utf-8') as f: eval_prompt = f.read()
        with open(CV_PROMPT_PATH, 'r', encoding='utf-8') as f: cv_prompt = f.read()
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f: cv_template = f.read()
    except FileNotFoundError as e:
        print(f"Fehler: Datei nicht gefunden. {e}")
        return

    job_info = fetch_job_description(url)
    if not job_info:
        print("Abbruch: Konnte keinen Text extrahieren.")
        return

    evaluation_result = evaluate_job(job_info, ssot_data, eval_prompt)
    company = evaluation_result.get("extracted_company", job_info["company"])
    role = evaluation_result.get("extracted_role", job_info["role"])
    is_match = evaluation_result.get("match", False)
    score = evaluation_result.get("fit_score", 0)
    language = evaluation_result.get("detected_language", "de")
    
    print(f"\nErgebnis für {company} - {role}:")
    print(f"Match: {is_match} | Score: {score}/100 | Sprache: {language.upper()}")
    print(f"Begründung: {evaluation_result.get('reasoning', '')}\n")

    if is_match and score >= 75:
        print("--> Super Match! Generierung läuft...")
        final_document = generate_application(job_info, ssot_data, cv_prompt, cv_template, language=language)
        
        # 1. Dokumententrennung (Cover Letter vs CV)
        parts = re.split(r'<!--\s*(?:DOCUMENT_SPLIT|PAGE_BREAK)\s*-->|&lt;!--\s*(?:DOCUMENT_SPLIT|PAGE_BREAK)\s*--&gt;', final_document)
        cover_letter_md = parts[0].strip() if len(parts) > 0 else ""
        cv_md = parts[1].strip() if len(parts) > 1 else (parts[0].strip() if len(parts) == 1 else "")
        
        # 2. Ordner & Dateinamen definieren
        clean_company = re.sub(r'[^\w\-]', '_', company).strip('_')
        clean_role = re.sub(r'[^\w\-]', '_', role).strip('_')
        folder_name = f"{clean_company}_{clean_role}"
        job_output_dir = os.path.join(OUTPUT_DIR, folder_name)
        os.makedirs(job_output_dir, exist_ok=True)
        
        cl_suffix = "CoverLetter" if language == "en" else "Anschreiben"
        base_prefix = f"{clean_company}_{clean_role}"
        
        cl_md_path = os.path.join(job_output_dir, f"{base_prefix}_{cl_suffix}.md")
        cl_pdf_path = os.path.join(job_output_dir, f"{base_prefix}_{cl_suffix}.pdf")
        cv_md_path = os.path.join(job_output_dir, f"{base_prefix}_CV.md")
        cv_pdf_path = os.path.join(job_output_dir, f"{base_prefix}_CV.pdf")
        
        # 3. Markdown-Dateien speichern
        with open(cl_md_path, 'w', encoding='utf-8') as out_f:
            out_f.write(cover_letter_md)
        with open(cv_md_path, 'w', encoding='utf-8') as out_f:
            out_f.write(cv_md)
            
        # 4. HTML Konvertierung & PDFs rendern
        print("[4] Rendere Anschreiben- & CV-PDFs im eigenen Job-Ordner...")
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
        
        cl_html = convert_markdown_to_styled_html(cover_letter_md, doc_type="cover_letter", language=language)
        pdfkit.from_string(cl_html, cl_pdf_path, options=pdf_options)
        
        # Enforce 1 page max limit for CV
        render_cv_pdf_with_page_limit(cv_md_path, cv_pdf_path, pdf_options, language=language)
            
        print(f"\n[ERFOLG] Alle Dokumente wurden im Job-Ordner gespeichert:")
        print(f" Ordner: {job_output_dir}")
        print(f"  - Anschreiben MD:  {os.path.basename(cl_md_path)}")
        print(f"  - Anschreiben PDF: {os.path.basename(cl_pdf_path)}")
        print(f"  - CV MD:           {os.path.basename(cv_md_path)}")
        print(f"  - CV PDF:          {os.path.basename(cv_pdf_path)}")
    else:
        print("--> Der Evaluator rät von dieser Stelle ab. Keine Dokumente generiert.")

if __name__ == "__main__":
    main()