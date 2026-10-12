with open('/home/gregor/my_projects/cv_automation_pipeline/scratch/test_15pt_full.py') as f:
    text_test = f.read()

with open('/home/gregor/my_projects/cv_automation_pipeline/src/00_manual_generator.py') as f:
    text_00 = f.read()

# Let's check differences in CSS or markdown preprocessing
print("hr margin in test:", "hr { border:" in text_test)
print("hr margin in 00:", "hr { border:" in text_00)
