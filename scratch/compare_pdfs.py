import fitz

doc_updated = fitz.open('/mnt/c/Users/grego/.gemini/antigravity-ide/brain/78cef00f-edbc-4f72-aa72-abfbbfb2d8a5/test_cv_final_combo.pdf')
print("test_cv_final_combo pages:", len(doc_updated))

doc_adago = fitz.open('/home/gregor/my_projects/cv_automation_pipeline/output/ready_to_send/adago_GmbH_Intern___Working_Student/CV_GregorNottmeier.pdf')
print("output adago CV pages:", len(doc_adago))
