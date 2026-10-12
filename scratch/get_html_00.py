import importlib.util

spec = importlib.util.spec_from_file_location("m_gen", "/home/gregor/my_projects/cv_automation_pipeline/src/00_manual_generator.py")
m_gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m_gen)

with open('/home/gregor/my_projects/cv_automation_pipeline/output/ready_to_send/adago_GmbH_Intern___Working_Student/CV_GregorNottmeier.md') as f:
    md_text = f.read()

html_00 = m_gen.convert_markdown_to_styled_html(md_text, doc_type="cv", language="en")
with open('/home/gregor/my_projects/cv_automation_pipeline/scratch/html_00.html', 'w') as f:
    f.write(html_00)

print("00 HTML length:", len(html_00))
