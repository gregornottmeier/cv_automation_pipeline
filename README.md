# CV & Cover Letter Automation Pipeline

An automated, AI-driven Python pipeline designed to streamline the job application process. This project scrapes job postings, evaluates them against a personal profile, and dynamically generates tailored Markdown and PDF documents for CVs and Cover Letters.

## Features

* **Job Scraping**: Automated extraction of job descriptions using `01_job_scraper.py`.
* **AI Evaluation & Orchestration**: Utilizes `job_evaluator_prompt.md` and `cv_system_prompt.md` to intelligently compare scraped job requirements against your qualifications.
* **Automatic Language Adaptation (DE/EN)**: Detects whether the job advertisement is in German or English and automatically generates both the Cover Letter and CV/Resume strictly in the corresponding language.
* **Separate PDF Outputs & Job Folders**: Organizes output documents into dedicated folders per job inside `output/ready_to_send/{Company}_{Role}/`. Generates separate, executive-styled PDFs and Markdown files for the Cover Letter (`Anschreiben.pdf` / `CoverLetter.pdf`) and CV (`CV.pdf`).
* **Single Source of Truth (SSOT)**: Centralizes all your skills, experiences, and educational background in a single `ssot_profile.json` file to ensure consistency across all generated documents.
* **Manual Override**: Includes `00_manual_generator.py` for instances where manual document generation or adjustments from a specific URL are required.

## Repository Structure

* `data/`: Contains the core `ssot_profile.json` detailing your professional background and `scraped_jobs.json`.
* `prompts/`: Stores the LLM system prompts (`cv_system_prompt.md`, `job_evaluator_prompt.md`, `master_agent_prompt.md`) responsible for reasoning and text generation.
* `src/`: Contains the core Python pipeline logic (`00_manual_generator.py`, `01_job_scraper.py`, `02_pipeline_manager.py`).
* `templates/`: Holds base Markdown structures (`cv_template.md`, `cover_letter_template.md`) for CV and cover letter generation in German and English.
* `output/ready_to_send/`: Contains generated per-job folders with separate Markdown and PDF files ready to submit.

## Tech Stack

* Python (genai / Gemini 3.6 Flash, markdown, pdfkit / wkhtmltopdf, BeautifulSoup4, requests)
* Prompt Engineering & AI Agents
* Web Scraping