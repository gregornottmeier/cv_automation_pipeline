import os, sys
os.environ["GEMINI_API_KEY"] = "test"
import importlib.util
import fitz

pdf_options = {
    'page-size': 'A4',
    'margin-top': '12mm',
    'margin-bottom': '12mm',
    'margin-left': '14mm',
    'margin-right': '14mm',
    'encoding': 'UTF-8',
    'no-outline': None,
    'enable-local-file-access': None,
    'print-media-type': None,
    'javascript-delay': 400
}

spec = importlib.util.spec_from_file_location("m_gen", "/home/gregor/my_projects/cv_automation_pipeline/src/00_manual_generator.py")
m_gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m_gen)

cv_md = "/home/gregor/my_projects/cv_automation_pipeline/output/ready_to_send/adago_GmbH_Intern___Working_Student/CV_GregorNottmeier.md"
cv_pdf = "/home/gregor/my_projects/cv_automation_pipeline/output/ready_to_send/adago_GmbH_Intern___Working_Student/CV_GregorNottmeier.pdf"

m_gen.render_cv_pdf(cv_md, cv_pdf, pdf_options, language="en")

doc = fitz.open(cv_pdf)
print(f"Verified Adago CV Page Count: {len(doc)}")
for i, p in enumerate(doc):
    print(f"Page {i+1}: drawings={len(p.get_drawings())}")
