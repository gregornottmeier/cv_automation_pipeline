# CV & Cover Letter Automation Pipeline

An automated, AI-driven Python pipeline designed to streamline the job application process. This project scrapes job postings, evaluates them against a personal profile, and dynamically generates tailored Markdown CVs and cover letters[cite: 6]. 

## Features

* **Job Scraping**: Automated extraction of job descriptions using `01_job_scraper.py`[cite: 6].
* **AI Evaluation & Orchestration**: Utilizes a `master_agent_prompt.md` and `job_evaluator_prompt.md` to intelligently compare scraped job requirements against your qualifications[cite: 6].
* **Dynamic Document Generation**: Injects tailored content into customizable Markdown templates (`cv_template.md` and `cover_letter_template.md`) based on the specific job context[cite: 6].
* **Single Source of Truth (SSOT)**: Centralizes all your skills, experiences, and educational background in a single `ssot_profile.json` file to ensure consistency across all generated documents[cite: 6].
* **Manual Override**: Includes `00_manual_generator.py` for instances where manual document generation or adjustments are required[cite: 6].

## Repository Structure

* `data/`: Contains the core `ssot_profile.json` detailing your professional background[cite: 6].
* `prompts/`: Stores the LLM system prompts (`cv_system_prompt.md`, `job_evaluator_prompt.md`, `master_agent_prompt.md`) responsible for reasoning and text generation[cite: 6].
* `src/`: Contains the core Python pipeline logic (`00_manual_generator.py`, `01_job_scraper.py`, `02_pipeline_manager.py`)[cite: 6].
* `templates/`: Holds the base Markdown structures for the CV and cover letter[cite: 6].

## Tech Stack

* Python
* Prompt Engineering / LLM Agents
* Web Scraping