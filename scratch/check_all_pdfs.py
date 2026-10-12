import fitz, os

base_dir = "/home/gregor/my_projects/cv_automation_pipeline/output/ready_to_send"
for folder in sorted(os.listdir(base_dir)):
    folder_path = os.path.join(base_dir, folder)
    if os.path.isdir(folder_path):
        for f in os.listdir(folder_path):
            if f.endswith(".pdf"):
                p = os.path.join(folder_path, f)
                doc = fitz.open(p)
                print(f"{folder}/{f}: {len(doc)} pages")
