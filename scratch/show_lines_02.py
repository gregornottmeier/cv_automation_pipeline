with open('/home/gregor/my_projects/cv_automation_pipeline/src/02_pipeline_manager.py') as f:
    lines = f.readlines()
for i in range(195, 215):
    print(f"{i+1}: {lines[i]}", end="")
