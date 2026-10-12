with open('/home/gregor/my_projects/cv_automation_pipeline/src/00_manual_generator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace duplicate .doc-kicker and set 15pt
dup = """        .doc-kicker {
            font-size: 17.5pt;
            font-weight: 800;
            color: #1e3a8a;
            text-transform: uppercase;
            letter-spacing: 1.8px;
            margin-top: 0;
            margin-bottom: 2px;
        }
        
        .doc-kicker {
            font-size: 17.5pt;
            font-weight: 800;
            color: #1e3a8a;
            text-transform: uppercase;
            letter-spacing: 1.8px;
            margin-top: 0;
            margin-bottom: 2px;
        }"""

single = """        .doc-kicker {
            font-size: 15pt;
            font-weight: 800;
            color: #1e3a8a;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-top: 0;
            margin-bottom: 2px;
        }"""

# Note double curly braces in python f-string
dup_f = """        .doc-kicker {{
            font-size: 17.5pt;
            font-weight: 800;
            color: #1e3a8a;
            text-transform: uppercase;
            letter-spacing: 1.8px;
            margin-top: 0;
            margin-bottom: 2px;
        }}
        
        .doc-kicker {{
            font-size: 17.5pt;
            font-weight: 800;
            color: #1e3a8a;
            text-transform: uppercase;
            letter-spacing: 1.8px;
            margin-top: 0;
            margin-bottom: 2px;
        }}"""

single_f = """        .doc-kicker {{
            font-size: 15pt;
            font-weight: 800;
            color: #1e3a8a;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-top: 0;
            margin-bottom: 2px;
        }}"""

if dup_f in content:
    content = content.replace(dup_f, single_f)
    print("Replaced dup_f in 00_manual_generator.py")
else:
    print("dup_f not found in 00_manual_generator.py")

with open('/home/gregor/my_projects/cv_automation_pipeline/src/00_manual_generator.py', 'w', encoding='utf-8') as f:
    f.write(content)
