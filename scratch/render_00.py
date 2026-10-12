import pdfkit, fitz

with open('/home/gregor/my_projects/cv_automation_pipeline/scratch/html_00.html') as f:
    html_00 = f.read()

pdf_path = '/home/gregor/my_projects/cv_automation_pipeline/scratch/test_00.pdf'
options = {
    'page-size': 'A4', 'margin-top': '12mm', 'margin-bottom': '12mm',
    'margin-left': '14mm', 'margin-right': '14mm', 'encoding': 'UTF-8',
    'no-outline': None, 'enable-local-file-access': None,
    'print-media-type': None, 'javascript-delay': 400
}
pdfkit.from_string(html_00, pdf_path, options=options)
doc = fitz.open(pdf_path)
print("Page count for 00 HTML:", len(doc))
