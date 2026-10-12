for file_path in ['/home/gregor/my_projects/cv_automation_pipeline/src/00_manual_generator.py', '/home/gregor/my_projects/cv_automation_pipeline/src/02_pipeline_manager.py']:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update margin-top for .section-lebenslauf h2
    content = content.replace('margin-top: 11px;', 'margin-top: 12px;')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated {file_path}")
