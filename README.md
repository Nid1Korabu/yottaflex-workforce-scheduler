# Workforce Scheduling & Compliance Console

A Python-based workforce operations system for analyzing shift coverage, employee skills, leave requests, scheduled working hours, attendance, and shift swaps. The project uses synthetic workforce data, SQLite, and Streamlit to identify scheduling risks and make operational exceptions easier to review.

## Project Overview

The Workforce Console provides a dashboard for exploring workforce records, monitoring staffing requirements, detecting scheduling exceptions, and reviewing data validation results.

The system generates reproducible synthetic workforce data, stores operational records in a relational SQLite database, and evaluates coverage and scheduling constraints.

### Key Features

- **Workforce data generation:** Generate synthetic workforce data using a configurable random seed.
- **Relational database:** Store operational records across 12 SQLite tables with primary-key and foreign-key relationships.
- **Coverage analysis:** Identify staffing shortages and missing required skills across teams, shifts, and dates.
- **Exception detection:** Detect overlapping assignments, assignments during approved leave, missing skills, overtime-cap violations, and swaps applied without approval.
- **Attendance reconciliation:** Check that clock-in and clock-out events correspond to shift assignments.
- **Data validation:** Check identifiers, relationships, dates, shift durations, lifecycle states, and known anomalies.
- **Audit history:** Preserve swap lifecycle events for traceability.
- **Ground-truth separation:** Keep injected anomaly reference labels outside the operational database and independently evaluate exception detection.
- **Interactive dashboard:** Explore overview metrics, coverage results, exceptions, workforce records, and validation summaries.

## Technology Stack

- Python
- Streamlit
- Pandas
- SQLite
- CSV and JSON
- Git and GitHub

## Dataset

The full dataset is generated synthetically using seed `20261022`.

| Dataset component | Records |
|---|---:|
| Employees | 2,000 |
| Teams | 100 |
| Skills | 4 |
| Employee-skill relationships | 6,104 |
| Shift templates | 3 |
| Shift assignments | 81,003 |
| Leave requests | 5,001 |
| Holiday calendar entries | 4 |
| Attendance events | 162,006 |
| Coverage requirements | 300 |
| Swap requests | 200 |
| Swap history events | 333 |
| **Total operational database records** | **257,058** |

The leave dataset includes the additional record used to inject a labelled anomaly.

### Coverage Analysis

The full dataset contains 27,000 team/shift/date combinations.

The current validation run reported:
- 2 combinations with staffing shortages.
- 3 combinations with skill shortages.

Coverage gaps are surfaced for review rather than silently treated as satisfied.

### Injected Anomalies

Five labelled anomaly categories are included to test whether the system detects important scheduling risks.

1. Employee double-booking.
2. Assignment overlapping approved leave.
3. Assignment missing a required skill.
4. Weekly scheduled hours exceeding an employee's configured cap.
5. Shift swap applied without manager approval.

The exception-detection logic evaluates operational records independently of the reference anomaly labels. The labels are maintained separately for evaluation and are excluded from the operational SQLite database.

## Project Structure

```text
YottaFlexWorkforce/
├── app.py
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   ├── generate_data.py
│   ├── validate_data.py
│   ├── create_database.py
│   └── verify_database.py
├── data/
│   ├── workforce.db
│   ├── coverage_analysis.csv
│   ├── database_import_summary.json
│   └── generated CSV and JSON files
├── docs/
│   ├── schema.md
│   └── data_dictionary.md
├── tests/
└── prompts/
    └── prompt_history.md
```

The documentation and prompt-history files should be included as they are completed. Generated data files may vary depending on the generation mode and output configuration.

## Setup

### 1. Clone the repository

```bash
git clone <YOUR_PUBLIC_GITHUB_REPOSITORY_URL>
cd YottaFlexWorkforce
```

Replace the placeholder with your actual public repository URL.

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Generate the full dataset

```powershell
python src/generate_data.py --full --seed 20261022
```

### 5. Validate the generated data

```powershell
python src/validate_data.py
```

### 6. Create the SQLite database

```powershell
python src/create_database.py
```

### 7. Verify the database

```powershell
python src/verify_database.py
```

### 8. Launch the dashboard

```powershell
python -m streamlit run app.py
```

Open the local URL displayed in the terminal.

**Important:** Run the commands in order when building the project from scratch. Database creation and validation use the generated files, so generate the data first.

## Dashboard Pages

### Overview
Displays workforce totals, staffing and skill gaps, detected exceptions, and database inventory.

### Coverage
Allows users to filter coverage results by team and shift and review staffing and skill shortages.

### Exceptions
Shows scheduling findings calculated from operational records, including the five injected anomaly categories.

### Workforce Data
Provides access to operational records loaded from SQLite.

### Validation
Displays database integrity results, generated-data validation results, and information about the separately stored anomaly reference labels.

## Reproducibility

The generator supports a fixed seed so that the same configuration can be reproduced.

Full-scale generation:

```powershell
python src/generate_data.py --full --seed 20261022
```

Development generation:

```powershell
python src/generate_data.py --seed 20261022
```

The full mode uses 2,000 employees, 100 teams, and a 90-day scheduling period. Development mode generates a smaller dataset for faster local testing.

To verify reproducibility, generate the data twice with the same seed and configuration, then compare the generated row counts and file checksums. The comparison should use the same Python and dependency environment.

## Validation Results

The current full-scale dataset passed the following checks:

- **52 generated-data validation checks passed; 0 failed.**
- **27 database verification checks passed; 0 failed.**
- All 12 operational tables were present.
- Primary-key uniqueness and foreign-key relationships were verified.
- Ground-truth anomaly labels were excluded from the operational database.
- Attendance events reconciled with shift assignments.
- The five intended anomaly categories were verified.

The reported staffing gaps, skill gaps, and overtime exception are intentional evaluation findings, not failures of the validation scripts.

## Data Provenance and Limitations

All workforce records are synthetically generated for development and evaluation. They do not represent a real employer's workforce or real employee records.

The dataset is intended to demonstrate relational data modelling, scheduling validation, exception detection, traceability, and reproducible data generation. The current project is a prototype; its synthetic findings should not be interpreted as proof of compliance with every applicable employment law or company policy.

## Future Improvements

- Add more configurable workforce and scheduling constraints.
- Improve coverage visualizations and filtering.
- Add automated tests for edge cases and lifecycle transitions.
- Add configurable reporting and export options.
- Extend evaluation with additional workload and fairness metrics.

## Author

Developed as a workforce scheduling and compliance analytics project using Python, SQLite, Pandas, and Streamlit.
