# UK Job Application Agent

A human-in-the-loop system for preparing stronger UK job applications from a structured, verified career database.

The project is designed to:

- store career evidence in structured YAML files;
- validate claims before they are used;
- protect sensitive information;
- prepare for later job matching, CV tailoring, cover-letter drafting, and application tracking;
- keep final submission decisions under human control.

## Current Project Status

### Phase 1 — Career Evidence Database

Complete.

The repository contains structured YAML files for:

- professional profile;
- employment experience;
- projects;
- education;
- certifications;
- skills;
- achievements and claim verification;
- application answers;
- target roles;
- profile links;
- project links;
- article links;
- certification indexes.

### Phase 2 — Validation Layer

Complete.

The validation layer includes:

- Pydantic data models;
- YAML loading;
- file-level validation;
- cross-file validation;
- claim-safety rules;
- privacy scanning;
- terminal validation command;
- JSON validation reporting;
- automated tests.

All 31 automated tests currently pass.

## Repository Structure

```text
job-application-agent-uk/
├── career_data/
│   ├── profile.yaml
│   ├── experience.yaml
│   ├── projects.yaml
│   ├── education.yaml
│   ├── certifications.yaml
│   ├── skills.yaml
│   ├── achievements.yaml
│   ├── application_answers.yaml
│   └── target_roles.yaml
│
├── source_documents/
│   ├── profile_links.yaml
│   ├── project_links.yaml
│   ├── article_links.yaml
│   ├── certification_index.yaml
│   ├── cv/
│   ├── projects/
│   ├── articles/
│   └── certifications/
│
├── src/
│   ├── __init__.py
│   ├── models.py
│   ├── career_data_loader.py
│   ├── validation_rules.py
│   ├── privacy_scanner.py
│   └── validate_career_data.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_loader.py
│   ├── test_validation.py
│   ├── test_cross_references.py
│   └── test_privacy_scanner.py
│
├── reports/
│   ├── .gitkeep
│   └── career_data_validation.json
│
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.11 or later
- pip

The current local environment has been tested successfully with Python 3.14.

## Installation

From the repository root:

```bash
python3 -m pip install -r requirements.txt
```

A virtual environment is recommended:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Validate the Career Database

Run:

```bash
python3 -m src.validate_career_data
```

This command:

1. locates the repository root;
2. loads all required YAML files;
3. validates them using Pydantic;
4. runs cross-file validation rules;
5. checks claim safety;
6. scans for sensitive data and secrets;
7. prints a terminal report;
8. writes a JSON report to:

```text
reports/career_data_validation.json
```

For a shorter terminal output:

```bash
python3 -m src.validate_career_data --quiet
```

To inspect the command exit code:

```bash
echo $?
```

An exit code of `0` means the validation passed sufficiently for later automation.

An exit code of `1` means there is at least one structural error, broken reference, or critical privacy issue.

## Validation Results

The validator returns one of three results.

### PASSED

All structural, cross-file, claim-safety, and privacy checks passed.

### PASSED WITH WARNINGS

No blocking errors exist, but one or more items need review.

Typical warnings include:

- claims that still need underlying benchmark evidence;
- project details awaiting clarification;
- open questions;
- expired or soon-to-expire credentials;
- expected contact information in a private repository.

This status is acceptable for continued development.

### FAILED

At least one blocking problem exists.

Typical causes include:

- malformed YAML;
- missing required files;
- duplicate identifiers;
- missing claim references;
- inconsistent repository URLs;
- blocked claims marked as approved;
- confidential projects exposing restricted links;
- salary inconsistencies;
- missing sensitive application answers;
- API keys, access tokens, private keys, or other critical personal data.

## Claim-Safety Rules

Each claim in `career_data/achievements.yaml` has a verification status and an application-use flag.

Example:

```yaml
verification_status: source_supported
approved_for_application: true
```

Blocked claims must use:

```yaml
approved_for_application: false
```

The future application generator must never use a claim where:

```yaml
approved_for_application: false
```

Claims marked as needing clarification or baseline definition remain blocked until supporting evidence is added.

## Privacy Rules

The privacy scanner checks for:

- AWS access keys;
- GitHub tokens;
- API keys;
- bearer tokens;
- private cryptographic keys;
- passwords and secrets;
- database URLs with embedded credentials;
- National Insurance numbers;
- card numbers;
- IBANs;
- passport numbers;
- visa or residence-permit document numbers;
- possible full street addresses.

Expected contact details such as an email address or UK phone number are treated as informational findings rather than critical errors.

This repository should remain private.

Do not commit:

- passports;
- visa documents;
- National Insurance numbers;
- bank details;
- card numbers;
- API keys;
- GitHub tokens;
- AWS credentials;
- passwords;
- references' private information;
- confidential source code covered by an NDA.

## Run the Tests

Run the complete test suite:

```bash
python3 -m pytest -v
```

The current expected result is:

```text
31 passed
```

Run individual modules with:

```bash
python3 -m pytest tests/test_loader.py -v
python3 -m pytest tests/test_validation.py -v
python3 -m pytest tests/test_cross_references.py -v
python3 -m pytest tests/test_privacy_scanner.py -v
```

## Main Python Modules

### `src/models.py`

Defines the Pydantic models for all Phase 1 YAML documents.

### `src/career_data_loader.py`

Locates, reads, parses, and validates all required YAML files.

### `src/validation_rules.py`

Applies business rules and cross-file integrity checks.

### `src/privacy_scanner.py`

Scans YAML text for secrets and sensitive personal information.

### `src/validate_career_data.py`

Combines the loader, validation rules, privacy scanner, terminal reporting, exit codes, and JSON report generation.

## Development Rule

Before any later module searches for jobs, scores vacancies, tailors a CV, or writes application material, run:

```bash
python3 -m src.validate_career_data
```

Only continue when the result is:

```text
PASSED
```

or:

```text
PASSED WITH WARNINGS
```

## Next Phase

Phase 3 will build the job-ingestion layer.

Its purpose will be to accept job URLs or structured vacancy records, extract job descriptions, normalise the information, prevent duplicates, and store the vacancies in a local database for later scoring.

The project will continue to use a human-in-the-loop workflow. It will not submit job applications automatically.

# Phase 3 — Job Ingestion and Vacancy Database

Phase 3 accepts public vacancy URLs, extracts job information, normalises the
records, detects duplicates, and stores valid jobs in a local SQLite database.

## Phase 3 structure

```text
config/
└── job_sources.yaml

input/
├── job_urls.csv
└── manual_jobs/
    └── .gitkeep

src/
├── job_models.py
├── job_url_loader.py
├── job_page_fetcher.py
├── job_parser.py
├── job_normaliser.py
├── job_deduplicator.py
├── job_database.py
└── ingest_jobs.py

tests/
├── conftest.py
├── test_job_models.py
├── test_job_url_loader.py
├── test_job_page_fetcher.py
├── test_job_parser.py
├── test_job_normaliser.py
├── test_job_deduplicator.py
├── test_job_database.py
└── test_ingest_jobs.py

data/
└── jobs.db

reports/
└── job_ingestion_report.json
```

## Add vacancy URLs

Edit:

```text
input/job_urls.csv
```

Columns:

```csv
url,source,notes,enabled,added_at
```

Example:

```csv
https://company.example/jobs/123,company_site,Strong AI engineering fit,true,2026-08-04T19:00:00+01:00
```

A completely blank row is ignored. A row with `enabled=false` is skipped.

## Supported source values

```text
company_site
greenhouse
lever
workable
ashby
smartrecruiters
linkedin_alert
indeed_alert
reed
totaljobs
civil_service_jobs
nhs_jobs
manual
other
```

## Run ingestion

From the repository root:

```bash
python3 -m src.ingest_jobs
```

Optional arguments:

```bash
python3 -m src.ingest_jobs \
  --csv input/job_urls.csv \
  --db data/jobs.db \
  --report reports/job_ingestion_report.json \
  --timeout 20 \
  --max-bytes 5000000
```

Quiet mode:

```bash
python3 -m src.ingest_jobs --quiet
```

The command performs:

```text
CSV
→ public-page fetch
→ structured or generic parsing
→ normalisation
→ duplicate detection
→ SQLite insertion
→ JSON report
```

## Generated outputs

SQLite database:

```text
data/jobs.db
```

Ingestion report:

```text
reports/job_ingestion_report.json
```

The database stores normalised vacancies and ingestion-run history.

## Safety and platform limits

The fetcher is limited to ordinary public pages. It does not bypass:

- logins;
- paywalls;
- CAPTCHAs;
- bot controls;
- access restrictions;
- authentication requirements.

A blocked or unsupported page is reported rather than circumvented.

## Run Phase 3 tests

Run the complete Phase 3 suite:

```bash
python3 -m pytest \
  tests/test_job_models.py \
  tests/test_job_url_loader.py \
  tests/test_job_page_fetcher.py \
  tests/test_job_parser.py \
  tests/test_job_normaliser.py \
  tests/test_job_deduplicator.py \
  tests/test_job_database.py \
  tests/test_ingest_jobs.py -v
```

Expected result:

```text
29 passed
```

Run the entire repository suite:

```bash
python3 -m pytest -v
```

With the existing 31 Phase 2 tests and the new 29 Phase 3 tests, the expected
combined result is:

```text
60 passed
```

## Phase 3 completion criteria

Phase 3 is complete when:

- job URL input loads successfully;
- public HTML pages can be fetched safely;
- JSON-LD and generic HTML jobs can be parsed;
- salary, location, work model, employment type, and sponsorship are normalised;
- duplicate jobs are detected;
- valid jobs are stored in SQLite;
- ingestion reports are generated;
- all Phase 3 tests pass.

# Phase 4 — Job Matching, Scoring, and Ranking

Phase 4 compares the validated career profile with jobs stored in the local
SQLite database. It produces transparent scores, eligibility findings,
evidence-backed explanations, and a ranked vacancy list.

## Phase 4 files

```text
config/
└── matching_rules.yaml

src/
├── matching_models.py
├── career_profile_builder.py
├── job_requirement_extractor.py
├── skill_matcher.py
├── experience_matcher.py
├── eligibility_checker.py
├── salary_location_matcher.py
├── match_scoring.py
├── match_explainer.py
├── job_ranker.py
└── score_jobs.py

tests/
├── phase4_helpers.py
├── test_matching_models.py
├── test_career_profile_builder.py
├── test_job_requirement_extractor.py
├── test_skill_matcher.py
├── test_experience_matcher.py
├── test_eligibility_checker.py
├── test_salary_location_matcher.py
├── test_match_scoring.py
├── test_match_explainer.py
├── test_job_ranker.py
└── test_score_jobs.py
```

The Phase 4 tests do not replace or modify `tests/conftest.py`.

## Run scoring

First ensure that career validation passes:

```bash
python3 -m src.validate_career_data
```

Then ensure that `data/jobs.db` contains ingested vacancies and run:

```bash
python3 -m src.score_jobs
```

Quiet mode:

```bash
python3 -m src.score_jobs --quiet
```

Custom paths:

```bash
python3 -m src.score_jobs \
  --root . \
  --db data/jobs.db \
  --json-report reports/job_match_scores.json \
  --csv-report reports/ranked_jobs.csv
```

## Outputs

Detailed JSON report:

```text
reports/job_match_scores.json
```

Ranked vacancy table:

```text
reports/ranked_jobs.csv
```

## Default scoring weights

```text
Skills                30%
Experience            25%
Eligibility           20%
Preferences           15%
Evidence quality      10%
```

Preference scoring is further divided into:

```text
Salary                         45%
Location and work model        40%
Employment type                15%
```

## Score bands

```text
85–100  Strong match
70–84   Good match
55–69   Possible match
40–54   Weak match
0–39    Poor match
```

## Eligibility overrides

A high technical score does not override a hard eligibility conflict.

Examples include:

- sponsorship explicitly unavailable when future sponsorship is needed;
- an unmet citizenship restriction;
- an incompatible security-clearance condition;
- a mandatory driving licence that is not held;
- an expired vacancy;
- missing current right to work.

Hard-stop vacancies receive a non-application recommendation and a zero ranking
score.

## Run Phase 4 tests

```bash
python3 -m pytest \
  tests/test_matching_models.py \
  tests/test_career_profile_builder.py \
  tests/test_job_requirement_extractor.py \
  tests/test_skill_matcher.py \
  tests/test_experience_matcher.py \
  tests/test_eligibility_checker.py \
  tests/test_salary_location_matcher.py \
  tests/test_match_scoring.py \
  tests/test_match_explainer.py \
  tests/test_job_ranker.py \
  tests/test_score_jobs.py -v
```

Then run the complete repository suite:

```bash
python3 -m pytest -v
```

## Interpreting the result

Each job receives:

- extracted required and preferred criteria;
- exact, related, transferable, and missing skill findings;
- direct, project-based, academic, or insufficient experience evidence;
- eligibility checks;
- salary and location fit;
- a weighted total score;
- strengths, gaps, risks, and next actions;
- a final recommendation;
- a ranking position.

The system remains human-in-the-loop. It recommends and explains; it does not
submit an application automatically.

# Phase 5 Output Structure

Generated application packs are written to:

```text
output/applications/
```

Each vacancy receives its own folder using this pattern:

```text
<company>_<role>_<job-id-prefix>/
```

Example:

```text
output/applications/
└── example_ai_ltd_data_engineer_a1b2c3d4/
    ├── tailored_cv.md
    ├── cover_letter.md
    ├── application_answers.json
    ├── interview_evidence.md
    └── application_manifest.json
```

## File purposes

### `tailored_cv.md`

A job-specific CV draft containing:

- tailored professional summary;
- prioritised skills;
- selected experience;
- selected projects;
- education;
- certifications;
- evidence-backed wording only.

### `cover_letter.md`

A company- and role-specific cover letter draft.

### `application_answers.json`

Structured answers to common application questions, including:

- motivation;
- relevant experience;
- salary expectations;
- sponsorship;
- start date.

Sensitive answers remain marked for human review.

### `interview_evidence.md`

A compact evidence sheet containing the strongest career examples selected for
the vacancy. It can later support interview preparation.

### `application_manifest.json`

The control file for the application pack. It records:

- job ID;
- company;
- role;
- generation time;
- generated filenames;
- selected evidence IDs;
- claim checks;
- quality checks;
- warnings;
- pack status;
- whether human review is required.

## Generate a pack

After jobs have been ingested and scored:

```bash
python3 -m src.generate_application_pack --job-id JOB_ID
```

Optional custom output location:

```bash
python3 -m src.generate_application_pack   --job-id JOB_ID   --output-root output/applications
```

## Pack statuses

```text
draft
review_required
approved
blocked
```

The current system never automatically marks a pack as approved. Human review
is required before submission.

A pack becomes blocked when the claim guard detects a serious unsupported
claim, such as an unverified numerical achievement.

## Git guidance

Generated application packs may contain personal information and vacancy-
specific content.

The safest default is to keep generated folders out of Git while retaining the
directory itself.

Add this to `.gitignore`:

```gitignore
output/applications/*
!output/applications/.gitkeep
```

This keeps the empty folder structure in the repository but prevents generated
application materials from being committed accidentally.
