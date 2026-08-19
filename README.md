# UK Job Application Agent

A local, human-in-the-loop pipeline for finding the best fit among supplied UK job vacancies and preparing evidence-based application drafts.

The agent uses a structured career profile as its source of truth. It validates that profile, imports public vacancy pages, scores each role against the candidate's skills and constraints, and creates a reviewable application pack. It **does not apply for jobs or submit personal information automatically**.

## What it does today

The working pipeline covers five stages:

1. **Validate career evidence** — load the YAML career record, check cross-references and claim approval, and scan for secrets or sensitive data.
2. **Ingest vacancies** — read enabled URLs from a CSV, fetch ordinary public pages, parse and normalise the vacancy, deduplicate it, and store it in SQLite.
3. **Score and rank jobs** — compare each stored vacancy with skills, experience, right-to-work constraints, salary, location, work model, and employment preferences.
4. **Select evidence safely** — choose only relevant, application-approved career evidence and block unsupported numerical or confidential claims.
5. **Draft an application pack** — tailor a CV using the registered master/reference CVs, then create a cover letter, standard application answers, interview evidence, and a manifest of warnings and quality checks.

Every result is a draft. Eligibility conflicts can stop a recommendation, sensitive answers are flagged, and a person must review all generated material before using it.

## End-to-end workflow

### 1. Install

Requires Python 3.11 or later.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. Validate the career profile

```bash
python3 -m src.validate_career_data
```

This reads `career_data/` and `source_documents/`, prints `PASSED`, `PASSED WITH WARNINGS`, or `FAILED`, and writes `reports/career_data_validation.json`. Resolve failures before continuing; warnings require judgement but do not block the pipeline.

### 3. Add and ingest job URLs

Add one row per vacancy to `input/job_urls.csv`:

```csv
url,source,notes,enabled,added_at
https://company.example/jobs/123,company_site,Strong data role,true,2026-08-19T09:00:00+00:00
```

Then run:

```bash
python3 -m src.ingest_jobs
```

Valid, non-duplicate jobs are stored in `data/jobs.db`; the run summary is written to `reports/job_ingestion_report.json`. Disabled and blank rows are skipped.

The fetcher handles ordinary public vacancy pages only. It does not bypass logins, paywalls, CAPTCHAs, authentication, or site access controls.

### 4. Score the stored jobs

```bash
python3 -m src.score_jobs
```

The scorer produces:

- `reports/ranked_jobs.csv` — a compact ranked list;
- `reports/job_match_scores.json` — detailed requirements, matches, gaps, eligibility findings, risks, and recommendations.

The default score combines skills (30%), experience (25%), eligibility (20%), preferences (15%), and evidence quality (10%). Hard eligibility conflicts—such as an explicit sponsorship, citizenship, clearance, licence, right-to-work, or closing-date conflict—override a high technical match and result in a do-not-apply recommendation.

### 5. Generate an application pack

Choose a job ID from the scoring output and run:

```bash
python3 -m src.generate_application_pack --job-id JOB_ID
```

The resulting folder is created under `output/applications/`:

```text
<company>_<role>_<job-id-prefix>/
├── tailored_cv.md
├── cover_letter.md
├── application_answers.json
├── interview_evidence.md
└── application_manifest.json
```

The CV process uses `source_documents/cv/plain_master_template.docx` for structure and selects suitable AI/ML, data, or teaching reference CV wording by role family. Reference CVs are never treated as factual authority: all reused wording must map back to approved evidence in `career_data/`.

The manifest records selected evidence, claim checks, document-quality results, warnings, pack status, and the mandatory human-review flag. A pack can be `draft`, `review_required`, or `blocked`; the generator never approves it automatically.

## Useful command options

```bash
# Concise output
python3 -m src.validate_career_data --quiet
python3 -m src.ingest_jobs --quiet
python3 -m src.score_jobs --quiet

# Custom inputs and outputs
python3 -m src.ingest_jobs \
  --csv input/job_urls.csv \
  --db data/jobs.db \
  --report reports/job_ingestion_report.json

python3 -m src.score_jobs \
  --db data/jobs.db \
  --json-report reports/job_match_scores.json \
  --csv-report reports/ranked_jobs.csv

python3 -m src.generate_application_pack \
  --job-id JOB_ID \
  --db data/jobs.db \
  --output-root output/applications
```

Use `python3 -m <module> --help` for the complete options for any command.

## Repository map

```text
career_data/          Verified profile, experience, projects, skills, and preferences
config/               Job-source, matching, and document-generation rules
input/                Vacancy URL CSV and optional manual inputs
source_documents/     Supporting links, documents, and registered CV templates
src/                  Validation, ingestion, scoring, and generation pipeline
tests/                Automated unit and workflow tests
data/                 Generated local SQLite database (ignored by Git)
reports/              Generated validation, ingestion, and scoring reports
output/applications/  Generated application drafts (ignored by Git)
```

The main command modules are:

- `src.validate_career_data` — career-data validation and privacy checks;
- `src.ingest_jobs` — vacancy fetching, parsing, normalisation, and storage;
- `src.score_jobs` — requirement extraction, eligibility checks, scoring, and ranking;
- `src.generate_application_pack` — evidence selection and application drafting.

## Safety and current boundaries

- `career_data/` is the factual source of truth; reference CVs may supply wording only.
- Unapproved, unverified, or confidential evidence is excluded or blocked.
- Generated answers about sponsorship, salary, and right to work require review.
- The system works from URLs supplied by the user; it does not discover vacancies autonomously.
- Fetching and parsing depend on the public page being accessible and supported.
- Outputs are Markdown/JSON drafts, not final submitted forms or automatically formatted DOCX files.
- Local databases, reports, and generated packs are ignored by Git because they can contain personal or vacancy-specific information.

Keep the repository private. Never commit identity documents, National Insurance or banking details, credentials, tokens, private keys, references' personal information, or NDA-protected material.

## Development

Run the complete test suite:

```bash
python3 -m pytest
```

When changing one stage, its focused tests can be run directly, for example:

```bash
python3 -m pytest tests/test_ingest_jobs.py tests/test_score_jobs.py tests/test_generate_application_pack.py
```

The project is currently a local, deterministic preparation tool: it explains its matches and preserves human control rather than acting as an autonomous application submitter.
