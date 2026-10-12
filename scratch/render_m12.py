import fitz

doc = fitz.open('/home/gregor/my_projects/cv_automation_pipeline/scratch/test_m12.pdf')
doc[0].get_pixmap(dpi=150).save('/mnt/c/Users/grego/.gemini/antigravity-ide/brain/78cef00f-edbc-4f72-aa72-abfbbfb2d8a5/test_m12_p1.png')
doc[1].get_pixmap(dpi=150).save('/mnt/c/Users/grego/.gemini/antigravity-ide/brain/78cef00f-edbc-4f72-aa72-abfbbfb2d8a5/test_m12_p2.png')
print("Rendered m12 p1 and p2")
