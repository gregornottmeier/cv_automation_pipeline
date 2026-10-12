import re, markdown

with open("/home/gregor/my_projects/cv_automation_pipeline/output/ready_to_send/adago_GmbH_Intern___Working_Student/CV_GregorNottmeier.md", "r") as f:
    md_text = f.read()

raw_html = markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'attr_list'])
parts = re.split(r'(?=<hr\s*/?>|<h2>)', raw_html)
print(f"Total parts: {len(parts)}")
for i, p in enumerate(parts):
    print(f"--- Part {i} (len={len(p)}, h2={'<h2>' in p}, hr={'<hr' in p}) ---")
    print(repr(p[:80]))
