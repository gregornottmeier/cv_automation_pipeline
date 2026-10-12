with open('/home/gregor/my_projects/cv_automation_pipeline/src/00_manual_generator.py') as f:
    text_00 = f.read()

with open('/home/gregor/my_projects/cv_automation_pipeline/src/02_pipeline_manager.py') as f:
    text_02 = f.read()

print("00 doc-kicker count:", text_00.count(".doc-kicker"))
print("02 doc-kicker count:", text_02.count(".doc-kicker"))
print("00 cv-section count:", text_00.count(".cv-section"))
print("02 cv-section count:", text_02.count(".cv-section"))
