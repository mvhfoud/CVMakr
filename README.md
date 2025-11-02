# CVMakr

An end-to-end résumé and motivation-letter generator that blends a Streamlit front-end with LangChain‑powered agents, background job orchestration, and automated compliance checks. The app lets you enqueue multiple résumés, watch their progress in real time, and retrieve richly formatted LaTeX output together with ATS guidance.

---

## ✨ Key Features

- **Guided résumé generation:** Paste a job description, pick a language, and let the pipeline build a tailored CV using curated projects, skills, and experiences.
- **Motivation letter on demand:** Toggle the letter option to produce a matching cover letter that respects your ATS constraints.
- **Non-blocking queue:** Submissions are processed by worker threads; you can enqueue several jobs and continue using the UI while they run in parallel.
- **Section previews & downloads:** Expanders surface every LaTeX snippet (summary, skills, experience, projects). When a job finishes you get one-click downloads for the full CV/letter files.
- **ATS & authenticity review:** Automatic keyword coverage checks, tone scoring, and optional refinement ensure the final document is both compliant and human-sounding.
- **Job metadata & metrics:** Company and role names are extracted from the job description, and every step’s duration/token usage is logged to `data/logs/resume_job_metrics.csv` for analysis.

---

## 🧭 Architecture Overview

```
Streamlit UI
 ├─ Submission form (job description, lang, toggles)
 ├─ In-memory queue (concurrent worker threads)
 ├─ Job cards (status, metrics, downloads, previews)
 └─ Custom “Product-to-Production” about section

Worker (per job)
 ├─ Template copy to drive/output directory
 ├─ LangChain agents
 │   ├─ Project selection            (gpt-4.1-mini)
 │   ├─ Skills grouping & verification
 │   ├─ Summary writer               (gpt-4.1-mini)
 │   └─ Optional motivation letter
 ├─ Compliance pass (keywords, tone)
 ├─ Optional refinement loop
 ├─ Google Drive upload + Sheets append
 └─ Metrics logger → CSV
```

All compute-heavy or I/O operations happen in the background worker so Streamlit stays responsive. The queue implementation mimics Celery/RQ semantics, making it easy to swap in a full broker if you outgrow in-process threads.

---

## 🚀 Quickstart

### 1. Prerequisites

- Python 3.10+
- (Optional) Virtual environment tool (`venv`, `conda`, or `pipenv`)
- API keys:
  - `OPENAI_API_KEY` (used by LangChain agents)
  - Google Drive & Sheets credentials (JSON) stored where `cvmakr.services.google` expects them (see below)

### 2. Install dependencies

```bash
python -m venv .venv
.\.venv\Scripts\activate        # PowerShell / Windows
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment

Create a `.env` file in the project root (or set env variables through your shell):

```
OPENAI_API_KEY=sk-...
GOOGLE_APPLICATION_CREDENTIALS=path/to/google-credentials.json
GOOGLE_DRIVE_FOLDER_ID=...
GOOGLE_SHEET_ID=...
```

The Google helper (`src/cvmakr/services/google.py`) reads these values and caches OAuth tokens in `token.json`. Make sure the service account or OAuth client has access to the Drive folder and Sheet.

### 4. Seed your content

The default templates expect source material in `data/content/`:

- `Experience_*.txt` — experience snippets referenced by the agents
- `projects.txt` — long-form descriptions of projects (parsed by the project agent)
- `personalaspirations.txt`, etc.

Update or replace these with your own content before running the app.

> **Missing personal files:** the repository does not include these documents. Create your own `Experience_*.txt`, `projects.txt`, `personalaspirations.txt`, etc., with the same names referenced above. They are ignored by Git on purpose.

### 5. Run Streamlit

```bash
streamlit run src/cvmakr/app/streamlit_app.py
```

Load the provided URL in your browser. Submit a job, then watch the “Recent Jobs” section update as the queue processes it. When a job finishes, expanders and download buttons appear automatically.

---

## 🛠️ Customisation Guide

| Area | How to tweak |
|------|--------------|
| **Concurrency** | Change `ensure_worker(build_resume_job, concurrency=3)` in `streamlit_app.py`. |
| **Job labels** | `job_metadata.py` trims the first 100 chars of the job description and attempts to extract `company` / `role`. Adjust the prompt or fallback logic if your postings differ. |
| **Templates** | LaTeX placeholders live in `data/templates/base_resume.tex`. The `resume_builder` pipeline writes sections to hard-coded indices — keep those placeholders in sync when editing the template. |
| **Agents** | Modify prompts or models inside `src/cvmakr/agents/`. Each agent is isolated so you can swap models (e.g. Anthropic) without affecting others. |
| **Logging** | The CSV at `data/logs/resume_job_metrics.csv` includes per-step durations & token counts. Extend `job_logging.py` or plug into your BI tool to chart throughput. |
| **Queue backend** | The in-process queue mirrors Celery’s API. You can swap `background_queue.ensure_worker` and `submit_job` for a Celery task without touching UI code. |

> **Prompt review:** each agent prompt inside `src/cvmakr/agents/` carries assumptions tailored to the original author (language, tone, experiences). Before using this tool in your own setting, read and adapt every prompt so no personal constraints bleed into your output.

---

## 🧩 Project Structure

```
.
├─ data/
│  ├─ content/              # Résumé source material (experiences, projects, aspirations)
│  ├─ templates/            # LaTeX base templates
│  └─ logs/resume_job_metrics.csv
├─ src/
│  └─ cvmakr/
│     ├─ agents/            # LangChain agents for summary, skills, projects, letter, etc.
│     ├─ app/               # Streamlit entrypoint & UI helpers
│     ├─ pipelines/         # Resume orchestration logic
│     ├─ services/          # Queue, Google integration, metadata extraction, logging
│     ├─ templates/         # LaTeX loader utilities
│     └─ utils/             # Config, text & skill helpers
├─ requirements.txt
├─ README.md
└─ .gitignore
```

---

## 🧪 Testing & Troubleshooting

- **Agent errors:** Most LLM calls raise through the queue and mark the job as failed. Expand the job card to view the exception message.
- **Google auth issues:** Delete `token.json` and restart to refresh OAuth credentials. Ensure the `GOOGLE_APPLICATION_CREDENTIALS` path is valid.
- **Streamlit stuck on “Processing”:** The job usually completed; refresh the page to rerun Streamlit and fetch the latest status. You can also add a manual “Refresh” button calling `st.experimental_rerun()`.
- **Performance:** Increase `concurrency` in `ensure_worker` for more simultaneous jobs. Be mindful of API rate limits and system RAM when running multiple heavy agents.

---

## 📜 License & Credits

This project is released under the MIT License (see `LICENSE` if included). It is built on top of Streamlit, LangChain, and various OpenAI models; remember to follow their respective terms of service when deploying publicly.

Enjoy shipping résumés at scale! Contributions, issues, and feature requests are welcome once the repository goes public. 🎉
