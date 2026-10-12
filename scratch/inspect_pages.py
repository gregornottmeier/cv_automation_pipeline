import fitz
doc = fitz.open('/home/gregor/my_projects/cv_automation_pipeline/output/ready_to_send/adago_GmbH_Intern___Working_Student/CV_GregorNottmeier.pdf')
for i, page in enumerate(doc):
    print(f'Page {i+1}: rect={page.rect}, drawings={len(page.get_drawings())}, text length={len(page.get_text())}')
    pix = page.get_pixmap()
    print(f'Pixmap: {pix.width}x{pix.height}')
