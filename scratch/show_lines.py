with open('/home/gregor/my_projects/cv_automation_pipeline/src/00_manual_generator.py') as f:
    lines = f.readlines()
for i in range(295, 335):
    print(f"{i+1}: {lines[i]}", end="")
