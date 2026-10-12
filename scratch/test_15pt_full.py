import pdfkit, fitz, os, re, markdown

with open('/home/gregor/my_projects/cv_automation_pipeline/output/ready_to_send/adago_GmbH_Intern___Working_Student/CV_GregorNottmeier.md', 'r', encoding='utf-8') as f:
    md_text = f.read()

# Current logic in 02_pipeline_manager.py but with 15pt kicker
m_text = re.sub(r'^(?![\-\*]\s)(.+)\n([\-\*]\s)', r'\1\n\n\2', md_text, flags=re.MULTILINE)
raw_html = markdown.markdown(m_text.strip(), extensions=['tables', 'fenced_code', 'attr_list'])

raw_html = re.sub(
    r'<h1>\s*(?:LEBENSLAUF\s*/\s*RESUME|RESUME\s*/\s*LEBENSLAUF|LEBENSLAUF\s*/\s*CV|RESUME\s*/\s*CV|LEBENSLAUF|RESUME|CV)\s*</h1>',
    '<div class="doc-kicker">RESUME</div>',
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

parts = re.split(r'(?=<hr\s*/?>|<h2>)', raw_html)
wrapped_parts = []
for part in parts:
    if not part.strip(): continue
    if re.search(r'<h2>', part, re.IGNORECASE):
        wrapped_parts.append(f'<div class="cv-section">{part}</div>')
    else:
        wrapped_parts.append(part)
content_html = f'<div class="section-lebenslauf">{"".join(wrapped_parts)}</div>'

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* {{ box-sizing: border-box; }}
body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 8.8pt;
    line-height: 1.36;
    color: #1e293b;
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
.section-lebenslauf {{ font-size: 8.8pt; line-height: 1.36; }}
.section-lebenslauf h2 {{
    font-size: 10pt; font-weight: 700; color: #1e3a8a;
    text-transform: uppercase; letter-spacing: 0.5px;
    margin-top: 11px; margin-bottom: 5px; padding-bottom: 2px;
    border-bottom: 1.5px solid #cbd5e1;
}}
.section-lebenslauf h3 {{ font-size: 9.5pt; font-weight: 700; color: #0f172a; margin-top: 8px; margin-bottom: 2px; }}
.section-lebenslauf p {{ margin-top: 0; margin-bottom: 4px; }}
.section-lebenslauf strong, .section-lebenslauf p strong, .section-lebenslauf li strong {{ color: #1e3a8a !important; font-weight: 600; }}
.section-lebenslauf p em {{ color: #475569; font-style: normal; }}
h1 {{ font-size: 16pt; font-weight: 700; color: #0f172a; margin-top: 2px; margin-bottom: 4px; border-bottom: 2px solid #2563eb; }}
ul {{ margin-top: 4px; margin-bottom: 8px; padding-left: 18px; list-style-type: disc; }}
li {{ margin-bottom: 4px; line-height: 1.38; color: #1e293b; display: list-item; }}
hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 8px 0; }}

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
</style>
</head>
<body>
{content_html}
</body>
</html>"""

pdf_path = '/home/gregor/my_projects/cv_automation_pipeline/scratch/test_15pt_full.pdf'
options = {
    'page-size': 'A4', 'margin-top': '12mm', 'margin-bottom': '12mm',
    'margin-left': '14mm', 'margin-right': '14mm', 'encoding': 'UTF-8',
    'no-outline': None, 'enable-local-file-access': None,
    'print-media-type': None, 'javascript-delay': 400
}
pdfkit.from_string(html, pdf_path, options=options)
doc = fitz.open(pdf_path)
print(f"Total pages with 15pt: {len(doc)}")
doc[0].get_pixmap(dpi=150).save('/mnt/c/Users/grego/.gemini/antigravity-ide/brain/78cef00f-edbc-4f72-aa72-abfbbfb2d8a5/test_15pt_p1.png')
doc[1].get_pixmap(dpi=150).save('/mnt/c/Users/grego/.gemini/antigravity-ide/brain/78cef00f-edbc-4f72-aa72-abfbbfb2d8a5/test_15pt_p2.png')
print("Saved test_15pt_p1.png and test_15pt_p2.png")
