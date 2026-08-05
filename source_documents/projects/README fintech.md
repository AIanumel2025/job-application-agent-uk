# fintechflow — A complete Banking Data Pipeline on AWS

A production-grade data engineering project which simulates a UK bank's data infrastructure. It is built using Python, and several AWS services, including Glue, Athena, dbt, with Tableau for visualisation.

---

## Overview
 
In today's competitive banking landscape, banks use data to manage hundreds of branches, millions of customers and billions in assets. To stay ahead of their competitors, it is crucial to derive insights from such data to make operational, financial, and strategic decisions. These insights are needed to improve performance across the entire organisation by increasing profitability, reducing their financial risk and improving customer experience. Some examples of key business questions which when addressed maximises performance include:
 
- Which branches are processing the most transactions?
- Which cities generate the most revenue?
- How are customers distributed across risk indicators and employment statuses?
- Which loan types have the highest default rates?
- Which banking products do customers use frequently?


Due to rising regulatory pressures and expanding customer expectations, most banks need robust data pipelines to turn transactional, customer and operational data into real, impactful insights. I built Fintechflow as a complete data pipeline to address that need. The pipeline ingests raw data, cleans, and ultimately transforms them into gold layer tables, ready for visualisation. The pipeline replicates the modern data infrastructure banks like Capitec (South Africa), Lloyds (UK), Barclays (UK) and others operate on.
 
---

## Project Architecture

![FintechFlow Pipeline Architecture](docs/project_architecture.png)

---

## Repository Structure
 
```
fintech-flow-data-pipeline/
│
├── data_generation/
│   ├── generate_branches.py        # 800 UK bank branches
│   ├── generate_customers.py       # 1,000,000 customer profiles
│   ├── generate_transactions.py    # 3,000,000 transaction records
│   └── generate_loans.py           # 200,000 loan records
│
├── ingestion/
│   └── ingest_to_s3.py             # boto3 upload script to S3 bronze layer
│
├── glue_jobs/
│   ├── silver_branches.py          # Glue ETL — clean branches
│   ├── silver_customers.py         # Glue ETL — clean customers (chunk processing)
│   ├── silver_transactions.py      # Glue ETL — clean transactions (chunk processing)
│   └── silver_loans.py             # Glue ETL — clean loans
│
├── dbt_project/
│   ├── dbt_project.yml             # dbt project configuration
│   └── models/
│       └── gold/
│           ├── sources.yml                    # silver layer source definitions
│           ├── gold_branch_performance.sql    # branch KPI mart
│           ├── gold_customer_segments.sql     # customer segmentation mart
│           └── gold_loan_performance.sql      # loan performance mart
│
├── athena_queries/
│   ├── bronze_validation.sql       # row counts and dirty data checks
│   ├── silver_validation.sql       # cleaning verification queries
│   └── gold_analytics.sql          # business question queries
│
├── docs/
│   └── screenshots/                # pipeline screenshots for documentation
│
├── README.md
└── LICENSE
```
 
---

## Datasets
 
The raw data is generated across customer, branch, loan, transaction and digital banking systems  and consolidated into datasets. The datasets contain incomplete, duplicate and are stored in many different formats, because they are acquired by independent operational systems. These data quality issues simulate real UK banking workflows. The Datasets are described below:
 
| Dataset | Rows | Description |
|---------|------|-------------|
| `branches` | 800 | UK bank branches across 10 cities |
| `customers` | 1,000,000 | Customer profiles with demographics and risk ratings |
| `transactions` | 3,000,000 | Banking transactions across 12 UK payment channels |
| `loans` | 200,000 | Loan records with principal, interest rate and repayment status |
 
---

## Dirty Data Characteristics
 
| Dataset | Issue | Injection Rate | Reason |
|---------|-------|---------------|--------|
| Branches | Whitespace in `branch_manager` | 5% | Data entry errors in source system |
| Branches | Null `no_of_staff` | 10% | Operational data gaps |
| Branches | Inconsistent `branch_type` | 10% | Multiple source systems with different conventions |
| Branches | Duplicate rows | 2% | System sync failures |
| Branches | Invalid postcodes | 3% | Manual entry errors |
| Customers | Gender inconsistencies | 5% | Mixed encoding standards |
| Customers | Null `annual_income` | 7% | Missing on account creation |
| Customers | Whitespace in `email` | 8% | Form input not trimmed |
| Customers | KYC status inconsistencies | 10% | Multiple verification systems |
| Transactions | Null `customer_id` | 5% | Orphan transactions — retained for branch volume |
| Transactions | Currency inconsistencies | 7% | Legacy system field variations |
| Transactions | Negative balances | 5% | System calculation errors |
| Loans | Invalid interest rates | 5% | Out-of-range system defaults |
| Loans | Null `issue_date` | 5% | Migration failures |
| Loans | Balance > principal | 4% | Fee application errors |
 
---

## Pipeline Phases
 
### Phase 1 — Data Generation (Google Colab)
Banking data is generated using Python and Faker, modelled after real UK banking workflows. Dirty data is deliberately injected to simulate realistic source system quality issues.
 
### Phase 2 — Raw Ingestion (AWS S3)
CSVs are uploaded to S3 bronze layer using a boto3 script. Raw dirty data lands in S3 exactly as-is with no filtering applied.
 
S3 folder structure:
```
s3://bucket/
├── raw/branches/
├── raw/customers/
├── raw/transactions/
├── raw/loans/
├── silver/branches/
├── silver/customers/
├── silver/transactions/
├── silver/loans/
├── gold/
└── query-results/
```
 
### Phase 3 — Schema Registration (AWS Glue Crawler)
A CSV classifier and Glue crawler scan the bronze S3 layer and register table schemas in the Glue Data Catalog, making raw data queryable via Athena before any cleaning has occurred.
 
### Phase 4 — Bronze Validation (Athena)
Raw data is validated in Athena before cleaning to confirm row counts, dirty data presence, and schema correctness.

### Phase 5 — Silver Layer (AWS Glue ETL)
I write four Python Shell Glue jobs to clean each dataset and write Parquet to the silver S3 layer. Parquet is used over CSV because it stores the data by columns instead of rows, reading the data faster and improving the speed of analytical queries. It also reduces the sizes of the datasets considerably, consuming less S3 storage and reducing infrastructural and query costs.

### Phase 6 — Gold Layer (dbt + Athena)
Three dbt models transform silver Parquet into pre-aggregated gold tables via Athena. Each model answers a specific set of business questions.
 
| Model | Rows | Business questions answered |
|-------|------|-----------------------------|
| `gold_branch_performance` | 800 | Which branches are busiest? Which cities generate most value? What is the channel mix? |
| `gold_customer_segments` | 90 | How are customers distributed by risk and employment? What is KYC verification coverage? |
| `gold_loan_performance` | 16 | Which loan types default most? What is the total remaining balance by segment? |

### Phase 7 — Analytics (using Tableau or QuickSight)
Dashboards are built in Tableau and QuickSight to connect to gold layer CSV exports, answering the core business questions that motivated the data pipeline.

---

## Tech Stack
 
| Layer | Technology |
|-------|-----------|
| Data generation | Python, Pandas |
| Raw ingestion | boto3, AWS S3 |
| Schema registration | AWS Glue Crawler, Glue Data Catalog |
| Transformation | AWS Glue Python Shell Jobs |
| Querying | AWS Athena |
| Gold modelling | dbt (dbt-athena-community 1.9.5) |
| Analytics | Tableau and QuickSight |
| Infrastructure | AWS IAM, AWS Secrets Manager |
| Version control | Git, GitHub |
 
---

