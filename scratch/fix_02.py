with open('/home/gregor/my_projects/cv_automation_pipeline/src/02_pipeline_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_f = """        .doc-kicker {{
            font-size: 17.5pt;
            font-weight: 800;
            color: #1e3a8a;
            text-transform: uppercase;
            letter-spacing: 1.8px;
            margin-top: 0;
            margin-bottom: 2px;
        }}"""

new_f = """        .doc-kicker {{
            font-size: 15pt;
            font-weight: 800;
            color: #1e3a8a;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-top: 0;
            margin-bottom: 2px;
        }}"""

if old_f in content:
    content = content.replace(old_f, new_f)
    print("Replaced old_f in 02_pipeline_manager.py")
else:
    print("old_f not found in 02_pipeline_manager.py")

with open('/home/gregor/my_projects/cv_automation_pipeline/src/02_pipeline_manager.py', 'w', encoding='utf-8') as f:
    f.write(content)
