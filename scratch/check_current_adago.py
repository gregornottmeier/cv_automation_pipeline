import fitz
doc = fitz.open('/home/gregor/my_projects/cv_automation_pipeline/output/ready_to_send/adago_GmbH_Intern___Working_Student/CV_GregorNottmeier.pdf')
print("Current adago CV page count:", len(doc))
