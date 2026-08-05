# Document Intelligence ETL Pipeline

An end-to-end production-ready **AI Document ETL pipeline** for math worksheet PDFs. It transforms structured and unstructured PDF data into structured, analysis-ready records. It features a modular architecture, automated test codes/suites and is containerised-deployment ready.

## Repository Contents
```
├── Complete_ETL_Pipeline_V4.ipynb # My original notebook
├── Dockerfile                     # Instructions on how to containerise the pipeline
├── LICENSE                        # Project license
├── README.md                      # Documentation
├── pyproject.toml                 # The project metadata and dependency configuration
├── run_entire_pipeline.py         # Main script to execute the pipeline
├── student_performance_ML.py      # An experimental, synthetic dataset generator for ML demos
├── config/                        # Configuration files and environment variables
├── data/                          # Local staging area for raw/processed artifacts
├── infra/                         # Cloud deployment blueprints and orchestration scripts
├── src/                           # Core source code (The Pipeline Logic)
│   ├── crawler.py                 # URL discovery and PDF fetching logic
│   ├── preprocessor.py            # PDF-to-Image rendering and quality cleanup
│   ├── cropper.py                 # CV-based region detection and OCR integration
│   ├── transformer.py             # Data parsing and schema enforcement
│   └── persistence.py             # Database connectivity and JSONL export
└── tests/                         # Automated test suite (Quality Gates)
    ├── test_crawler.py            # Tests for link extraction and downloading
    ├── test_preprocessor.py       # Tests for image rendering and resolution
    ├── test_cropper.py            # Tests for segmentation and OCR logic
    ├── test_transformer.py        # Tests for parsing and metadata inference
    └── test_persistence.py        # Tests for DB upserts and data integrity
```

## Project Overview

This project is organised as a staged ETL pipeline that:

1. **Discovers PDF sources** from multiple target websites.
2. **Downloads and deduplicates** PDF files.
3. **Converts PDF pages to cleaned images** for vision processing.
4. **Detects question regions** using hybrid layout and CV strategies.
5. **Crops required question regions and performs OCR** to convert to markdown (Mathpix).
6. **Evaluates extraction quality** with scoring heuristics.
7. **Transforms extracted markdown** into structured, analytics-ready records.
8. **Outlines cloud-oriented orchestration concepts** for AWS deployment (see notebook).

This structure addresses common AI/data-engineering concerns: robust ingestion, quality checks, schema-ready transformations, and deployment planning.

## Pipeline Architecture (Notebook)

### Stage 1: Discover & Fetch PDFs
- Uses static + dynamic page retrieval patterns.
- Extracts and normalises candidate PDF links from anchors, scripts, and forms.

### Stage 2: Download & Store PDFs
- Downloads files to local storage.
- Uses hash-based deduplication and metadata tracking.

### Stage 3: Render PDFs as Images
- Converts pages to images.
- Applies preprocessing (including orientation/quality cleanup) to improve downstream detection and OCR.

### Stage 4: Locate Question Boundaries
- It uses a hybrid strategy combining semantic layout signals (using LayoutLMV3 model) and classical computer vision heuristics.
- Runs multiple segmentation strategies and validates/cleans candidate regions.

### Stage 5: OCR to Markdown
- Crops detected regions.
- Sends crops through OCR to extract markdown/LaTeX-friendly question text.

### Stage 6: Evaluation
- Scores extraction outputs with markdown/LaTeX quality heuristics.
- Supports quick quality auditing before large-scale transformation.

### Stage 7: Transform to Structured Records
- Parses markdown into question-level structured objects.
- Infers useful schema/metadata (e.g., question number, choices, topic/difficulty hints).

### Stage 8: Cloud Orchestration Concept
- Includes orchestration notes for an AWS target architecture.
- Develops a blueprint for turning notebook logic into productionised, scheduled jobs.

## Tech Stack

- **Language:** Python
- **Notebook workflow:** Jupyter
- **Web ingestion:** `requests`, `beautifulsoup4`, Selenium/Playwright patterns
- **Document/image processing:** PDF-to-image conversion, OpenCV, Transformers (LayoutLMv3)
- **ML/CV signals:** transformer-based layout analysis + vision embeddings
- **OCR layer:** Mathpix API workflow
- **Storage/serialisation:** local filesystem, JSON-like structured outputs, PostgreSQL.
- **Containeristion:** Docker
- **Quality Assurance:** `pytest` 

## How to Run

### 1. Environment setup
```
# Clone the repo
git clone <your-repo-url>
cd <repo-name>

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure credentials and paths
Before running OCR or cloud-connected components, configure:
- API keys/secrets (e.g., OCR provider)
- local output directories
- optional cloud resource settings

### 3. Running the Test codes
`pytest tests/`

### 4. Deployment (Docker)
```
docker build -t math-etl .
docker run --env-file .env math-etl
```

## Ancillary Work/script: A Synthetic ML Dataset Generator
`student_performance_ML.py` An aside script, which produces a synthetic student performance dataset with demographic, behavioural, and academic features plus a generated grade target.


## Portfolio Value

This repository demonstrates practical AI engineering across:
- Unstructured data ingestion, by handling variable PDFs from multiple sources
- Document preprocessing and transformation,
- Data extraction quality control,
- Analytics-oriented structuring for scalable downstream use.
- Deployment infrastructure using Docker and Cloud platforms such as AWS.
