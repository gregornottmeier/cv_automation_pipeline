import pdfkit, fitz

for m_top in [11, 12, 13, 14]:
    with open('/home/gregor/my_projects/cv_automation_pipeline/scratch/html_00.html') as f:
        html = f.read()
    
    # adjust h2 margin-top
    html = html.replace('margin-top: 11px;', f'margin-top: {m_top}px;')
    pdf_path = f'/home/gregor/my_projects/cv_automation_pipeline/scratch/test_m{m_top}.pdf'
    options = {
        'page-size': 'A4', 'margin-top': '12mm', 'margin-bottom': '12mm',
        'margin-left': '14mm', 'margin-right': '14mm', 'encoding': 'UTF-8',
        'no-outline': None, 'enable-local-file-access': None,
        'print-media-type': None, 'javascript-delay': 400
    }
    pdfkit.from_string(html, pdf_path, options=options)
    doc = fitz.open(pdf_path)
    d1 = len(doc[0].get_drawings())
    d2 = len(doc[1].get_drawings()) if len(doc) > 1 else 0
    print(f"margin-top {m_top}px: total pages={len(doc)}, p1_drawings={d1}, p2_drawings={d2}")
