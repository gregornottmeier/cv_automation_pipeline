import os
import json
import re
import time
from datetime import datetime
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
CL_PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "cover_letter_system_prompt.md")
CV_TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "cv_template.md")
CL_TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "cover_letter_template.md")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "ready_to_send")

os.makedirs(OUTPUT_DIR, exist_ok=True)

CANDIDATE_MODELS = [
    'gemini-3.5-flash',
    'gemini-3.6-flash',
    'gemini-flash-latest',
    'gemini-3-flash-preview'
]

def generate_content_with_retry_and_fallback(contents, config=None):
    last_exception = None
    for model in CANDIDATE_MODELS:
        for attempt in range(3):
            try:
                if config:
                    response = client.models.generate_content(model=model, contents=contents, config=config)
                else:
                    response = client.models.generate_content(model=model, contents=contents)
                return response.text
            except Exception as e:
                last_exception = e
                err_msg = str(e)
                if "503" in err_msg or "high demand" in err_msg.lower() or "unavailable" in err_msg.lower() or "429" in err_msg:
                    time.sleep(2)
                elif "404" in err_msg or "not_found" in err_msg.lower():
                    break
                else:
                    time.sleep(1)
    raise RuntimeError(f"Alle Gemini-Modelle fehlgeschlagen. Letzter Fehler: {last_exception}")

def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return file.read()

def clean_and_parse_json(raw_text):
    text = raw_text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    codeblock_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if codeblock_match:
        try:
            return json.loads(codeblock_match.group(1))
        except Exception:
            pass
    json_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if json_match:
        potential_json = json_match.group(1).strip()
        brace_count = 0
        end_idx = -1
        for i, char in enumerate(potential_json):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
        if end_idx != -1:
            try:
                return json.loads(potential_json[:end_idx])
            except Exception:
                pass
        try:
            return json.loads(potential_json)
        except Exception:
            pass
    raise ValueError("Konnte kein gültiges JSON im LLM-Output finden.")

def evaluate_job(job_info, ssot_data, eval_prompt):
    print("\n[Phase 1] Analysiere Job-Match...")
    full_prompt = f"{eval_prompt}\n\n---\nSSOT_PROFILE:\n{ssot_data}\n\n---\nTARGET_JOB:\n{job_info.get('full_job_prompt', job_info.get('raw_text', ''))}"
    
    try:
        res_text = generate_content_with_retry_and_fallback(
            full_prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        eval_dict = clean_and_parse_json(res_text)
        if eval_dict.get("extracted_company", "Nicht angegeben") in ["Nicht angegeben", "Unknown_Company"]:
            eval_dict["extracted_company"] = job_info.get("company", "Unknown_Company")
        if eval_dict.get("extracted_role", "Nicht angegeben") in ["Nicht angegeben", "Unknown_Role"]:
            eval_dict["extracted_role"] = job_info.get("role", job_info.get("title", "Unknown_Role"))
        if "detected_language" not in eval_dict or eval_dict["detected_language"] not in ["de", "en"]:
            eval_dict["detected_language"] = "de"
        return eval_dict
    except Exception as e:
        print(f"Fehler beim Parsen der API-Antwort: {e}")
        return {"match": False, "fit_score": 0, "reasoning": f"JSON Parsing Error: {e}", "detected_language": "de"}

def get_current_date_str(language="de"):
    today = datetime.now()
    de_months = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
    en_months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    if language == "en":
        return f"{today.day} {en_months[today.month - 1]} {today.year}"
    else:
        return f"{today.day}. {de_months[today.month - 1]} {today.year}"

def generate_cv(job_info, ssot_data, cv_prompt, template, language="de"):
    print(f"[Phase 2a] Erstelle maßgeschneiderten Lebenslauf (Sprache: {language.upper()})...")
    current_date = get_current_date_str(language)
    lang_instruction = f"WICHTIGE SPRACHVORGABE: Generiere den Lebenslauf strikt auf {'Englisch' if language == 'en' else 'Deutsch'}!"
    date_instruction = f"AKTUELLES DATUM (CURRENT_DATE): {current_date}"
    title_instruction = (
        "WICHTIGE TITELVORGABE: Für die deutsche Version muss das Dokument zwingend mit '# LEBENSLAUF' beginnen. "
        "Für die englische Version muss das Dokument zwingend mit '# RESUME' beginnen. "
        "Verwende NIEMALS kombinierte Titel wie 'LEBENSLAUF / RESUME', 'CV / RESUME' oder 'RESUME / CV'!"
    )
    structure_instruction = "STRUKTUR-VORGABE: Nutze das folgende Template ausschließlich als Struktur- und Formatierungsvorlage (Markdown-Hierarchie, Abschnitte). Alle inhaltlichen Fakten, Kontaktdaten, Skills, Projekte, Erfahrungen und Ausbildungsdaten stammen strikt aus SSOT_PROFILE!"
    
    lang_section = "ENGLISH" if language == "en" else "GERMAN"
    template_section = template
    pattern = rf"##\s*{lang_section}.*?(?=(?:\n##\s+[A-Z]+|\Z))"
    match = re.search(pattern, template, flags=re.DOTALL | re.IGNORECASE)
    if match:
        template_section = match.group(0).strip()

    full_prompt = f"{cv_prompt}\n\n{lang_instruction}\n{date_instruction}\n{title_instruction}\n{structure_instruction}\n\nHier ist die Struktur-Vorlage (Template):\n{template_section}\n\n---\nSSOT_PROFILE:\n{ssot_data}\n\n---\nTARGET_JOB:\n{job_info.get('full_job_prompt', job_info.get('raw_text', ''))}"
    return generate_content_with_retry_and_fallback(full_prompt)

def generate_cover_letter(job_info, ssot_data, cv_text, cl_prompt, template, language="de"):
    print(f"[Phase 2b] Erstelle passgenaues Anschreiben (Sprache: {language.upper()})...")
    current_date = get_current_date_str(language)
    lang_instruction = f"WICHTIGE SPRACHVORGABE: Generiere das Anschreiben strikt auf {'Englisch' if language == 'en' else 'Deutsch'}!"
    date_instruction = f"AKTUELLES DATUM (CURRENT_DATE): {current_date}"
    structure_instruction = "STRUKTUR-VORGABE: Nutze das folgende Template ausschließlich als Struktur- und Formatierungsvorlage für das Anschreiben. Alle Kontaktdaten und inhaltlichen Details stammen strikt aus SSOT_PROFILE und dem generierten Lebenslauf (GENERATED_CV)!"
    
    lang_section = "ENGLISH" if language == "en" else "GERMAN"
    template_section = template
    pattern = rf"##\s*{lang_section}.*?(?=(?:\n##\s+[A-Z]+|\Z))"
    match = re.search(pattern, template, flags=re.DOTALL | re.IGNORECASE)
    if match:
        template_section = match.group(0).strip()

    full_prompt = f"{cl_prompt}\n\n{lang_instruction}\n{date_instruction}\n{structure_instruction}\n\nHier ist die Anschreiben-Strukturvorlage (Template):\n{template_section}\n\n---\nSSOT_PROFILE:\n{ssot_data}\n\n---\nGENERATED_CV:\n{cv_text}\n\n---\nTARGET_JOB:\n{job_info.get('full_job_prompt', job_info.get('raw_text', ''))}"
    return generate_content_with_retry_and_fallback(full_prompt)

def convert_markdown_to_styled_html(markdown_text, doc_type="cover_letter", language="de"):
    if doc_type == "cover_letter":
        # Remove any accidental backticks so frameworks/packages in cover letter prose render as normal text
        markdown_text = re.sub(r'`([^`]+)`', r'\1', markdown_text)
        raw_html = markdown.markdown(markdown_text.strip(), extensions=['tables', 'fenced_code', 'attr_list'])
        raw_html = re.sub(r'<h1>\s*(ANSCHREIBEN|COVER LETTER)\s*</h1>', '', raw_html, flags=re.IGNORECASE)
        content_html = f'<div class="section-anschreiben">{raw_html}</div>'
    else:
        # ERZWINGE LEERZEILE VOR LISTEN (Verhindert, dass der Markdown-Parser Listen ignoriert)
        # Sucht nach Zeilen, die nicht mit einem Bullet Point starten, gefolgt von einem \n und einem Bullet Point
        markdown_text = re.sub(r'^(?![\-\*]\s)(.+)\n([\-\*]\s)', r'\1\n\n\2', markdown_text, flags=re.MULTILINE)
        
        raw_html = markdown.markdown(markdown_text.strip(), extensions=['tables', 'fenced_code', 'attr_list'])
        kicker_title = "RESUME" if language == "en" else "LEBENSLAUF"
        raw_html = re.sub(
            r'<h1>\s*(?:LEBENSLAUF\s*/\s*RESUME|RESUME\s*/\s*LEBENSLAUF|LEBENSLAUF\s*/\s*CV|RESUME\s*/\s*CV|LEBENSLAUF|RESUME|CV)\s*</h1>',
            f'<div class="doc-kicker">{kicker_title}</div>',
            raw_html,
            flags=re.IGNORECASE,
            count=1
        )
        raw_html = re.sub(
            r'<h1>\s*(?:LEBENSLAUF\s*/\s*RESUME|RESUME\s*/\s*LEBENSLAUF|LEBENSLAUF\s*/\s*CV|RESUME\s*/\s*CV|LEBENSLAUF|RESUME|CV)\s*</h1>',
            '',
            raw_html,
            flags=re.IGNORECASE
        )
        # Wrap sections (split by <hr /> or before <h2>) in <div class="cv-section"> to prevent pagebreaks within a section
        parts = re.split(r'(?=<hr\s*/?>|<h2>)', raw_html)
        wrapped_parts = []
        for part in parts:
            if not part.strip():
                continue
            if re.search(r'<h2>', part, re.IGNORECASE):
                wrapped_parts.append(f'<div class="cv-section">{part}</div>')
            else:
                wrapped_parts.append(part)
        wrapped_html = "".join(wrapped_parts)
        content_html = f'<div class="section-lebenslauf">{wrapped_html}</div>'
        
    styled_html = f"""<!DOCTYPE html>
<html lang="{language}">
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
        .doc-kicker {{
            font-size: 15pt;
            font-weight: 800;
            color: #1e3a8a;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-top: 0;
            margin-bottom: 2px;
        }}
        .section-anschreiben {{ font-size: 9.2pt; line-height: 1.45; }}
        .section-anschreiben code {{
            background-color: transparent !important;
            color: inherit !important;
            padding: 0 !important;
            border-radius: 0 !important;
            font-size: inherit !important;
            font-family: inherit !important;
            border: none !important;
        }}
        .section-lebenslauf {{ font-size: 8.8pt; line-height: 1.36; }}
        .section-lebenslauf h2 {{
            font-size: 10pt;
            font-weight: 700;
            color: #1e3a8a;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 12px;
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
        .section-lebenslauf p {{ margin-top: 0; margin-bottom: 4px; }}
        .section-lebenslauf strong,
        .section-lebenslauf p strong,
        .section-lebenslauf li strong {{ color: #1e3a8a !important; font-weight: 600; }}
        .section-lebenslauf p em {{ color: #475569; font-style: normal; }}
        h1 {{ font-size: 16pt; font-weight: 700; color: #0f172a; margin-top: 2px; margin-bottom: 4px; border-bottom: 2px solid #2563eb; }}
        h2 {{ font-size: 10pt; font-weight: 600; color: #1e3a8a; text-transform: uppercase; margin-top: 10px; margin-bottom: 4px; border-bottom: 1px solid #cbd5e1; }}
        h3 {{ font-size: 9.2pt; font-weight: 600; color: #0f172a; margin-top: 6px; margin-bottom: 2px; }}
        p {{ margin-top: 0; margin-bottom: 5px; }}
        
        /* KORRIGIERTE LISTEN-STYLES FÜR DAS GESAMTE DOKUMENT */
        ul {{ margin-top: 4px; margin-bottom: 8px; padding-left: 18px; list-style-type: disc; }}
        li {{ margin-bottom: 4px; line-height: 1.38; color: #1e293b; display: list-item; }}
        
        strong {{ color: #1e3a8a; font-weight: 600; }}
        hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 8px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 4px; margin-bottom: 8px; }}
        th {{ background-color: #f1f5f9; color: #0f172a; padding: 4px 6px; border-bottom: 2px solid #cbd5e1; font-size: 8.5pt; }}
        td {{ padding: 4px 6px; border-bottom: 1px solid #e2e8f0; font-size: 8.5pt; }}
        code {{ background-color: #f1f5f9; color: #1e3a8a; padding: 1px 4px; border-radius: 3px; font-size: 8pt; font-family: 'Inter', sans-serif; font-weight: 500; border: 1px solid #cbd5e1; }}
    
        .cv-section {{
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}
        .cv-section h2, .cv-section h3 {{
            page-break-after: avoid !important;
            break-after: avoid !important;
        }}
        .section-lebenslauf h2, .section-lebenslauf h3 {{
            page-break-after: avoid !important;
            break-after: avoid !important;
        }}
        .section-lebenslauf ul, .section-lebenslauf p {{
            orphans: 3;
            widows: 3;
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

def render_cv_pdf(cv_md_path, cv_pdf_path, pdf_options, language="en"):
    with open(cv_md_path, 'r', encoding='utf-8') as f:
        cv_md = f.read()

    cv_html = convert_markdown_to_styled_html(cv_md, doc_type="cv", language=language)
    pdfkit.from_string(cv_html, cv_pdf_path, options=pdf_options)

    try:
        import fitz
        doc = fitz.open(cv_pdf_path)
        page_count = len(doc)
        doc.close()
        print(f"[CV RENDER] Initial CV PDF page count: {page_count}")
    except Exception as e:
        print(f"[PAGE CHECK] Could not check PDF page count: {e}")
        return

    while page_count > 2:
        print(f"[AUTO-PAGE-FIT] CV PDF is {page_count} pages (exceeds 2 page limit). Trimming least important entry from Professional Experience...")
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

# Backwards compatibility alias
render_cv_pdf_with_page_limit = render_cv_pdf


def main():
    try:
        ssot_data = read_file(SSOT_PATH)
        eval_prompt = read_file(EVAL_PROMPT_PATH)
        cv_prompt = read_file(CV_PROMPT_PATH)
        cl_prompt = read_file(CL_PROMPT_PATH)
        cv_template = read_file(CV_TEMPLATE_PATH)
        cl_template = read_file(CL_TEMPLATE_PATH)
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
        role = evaluation_result.get("extracted_role", title)
        is_match = evaluation_result.get("match", False)
        score = evaluation_result.get("fit_score", 0)
        reasoning = evaluation_result.get("reasoning", "")
        language = evaluation_result.get("detected_language", "de")
        
        print(f"Unternehmen: {company}")
        print(f"Match: {is_match} | Fit-Score: {score}/100 | Sprache: {language.upper()}")
        print(f"Begründung: {reasoning}")
        
        if is_match and score >= 75:
            print("--> Match erfolgreich! Starte Dokumentengenerierung...")
            
            # Extract and filter projects
            selected_ids = evaluation_result.get("selected_project_ids", [])
            filtered_ssot_str = ssot_data
            if selected_ids:
                try:
                    ssot_json = json.loads(ssot_data)
                    all_projects = ssot_json.get("basics", {}).get("projects", [])
                    filtered_projects = [p for p in all_projects if p.get("id") in selected_ids]
                    if filtered_projects:
                        ssot_json["basics"]["projects"] = filtered_projects
                        filtered_ssot_str = json.dumps(ssot_json, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"Fehler beim Filtern der Projekte: {e}")

            cv_md = generate_cv(job, filtered_ssot_str, cv_prompt, cv_template, language=language)
            cover_letter_md = generate_cover_letter(job, filtered_ssot_str, cv_md, cl_prompt, cl_template, language=language)
            
            clean_company = re.sub(r'[^\w\-]', '_', company).strip('_')
            clean_title = re.sub(r'[^\w\-]', '_', role).strip('_')
            folder_name = f"{clean_company}_{clean_title}"
            job_output_dir = os.path.join(OUTPUT_DIR, folder_name)
            os.makedirs(job_output_dir, exist_ok=True)
            
            candidate_name = "GregorNottmeier"
            try:
                ssot_obj = json.loads(ssot_data) if isinstance(ssot_data, str) else ssot_data
                raw_name = ssot_obj.get("basics", {}).get("name", "")
                if raw_name:
                    candidate_name = re.sub(r'[^\w]', '', raw_name)
            except Exception:
                pass

            cl_base_name = f"CoverLetter_{candidate_name}"
            cv_base_name = f"CV_{candidate_name}"

            cl_md_path = os.path.join(job_output_dir, f"{cl_base_name}.md")
            cl_pdf_path = os.path.join(job_output_dir, f"{cl_base_name}.pdf")
            cv_md_path = os.path.join(job_output_dir, f"{cv_base_name}.md")
            cv_pdf_path = os.path.join(job_output_dir, f"{cv_base_name}.pdf")
            
            with open(cl_md_path, 'w', encoding='utf-8') as out_f:
                out_f.write(cover_letter_md)
            with open(cv_md_path, 'w', encoding='utf-8') as out_f:
                out_f.write(cv_md)
                
            cl_html = convert_markdown_to_styled_html(cover_letter_md, doc_type="cover_letter", language=language)
            
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
            pdfkit.from_string(cl_html, cl_pdf_path, options=pdf_options)
            
            # Render CV PDF
            render_cv_pdf(cv_md_path, cv_pdf_path, pdf_options, language=language)
            
            print(f"Erfolg! Bewerbungsunterlagen gespeichert in:")
            print(f" Ordner: {job_output_dir}")
            print(f"  - Cover Letter MD:  {os.path.basename(cl_md_path)}")
            print(f"  - Cover Letter PDF: {os.path.basename(cl_pdf_path)}")
            print(f"  - CV MD:           {os.path.basename(cv_md_path)}")
            print(f"  - CV PDF:          {os.path.basename(cv_pdf_path)}")
        else:
            print("--> Stelle abgelehnt. Überspringe.")

if __name__ == "__main__":
    main()