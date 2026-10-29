# AI Prompt History

## Introduction

I used ChatGPT during the development of my Workforce Scheduling and Compliance project whenever I needed help with coding, debugging, testing, or understanding something.

## AI Tool Used

- ChatGPT

## Prompts Used

### 1. Generating Workforce Data

**Prompt:**

"Help me create a python program to generate workforce data for employees, teams, skills, shifts, leave requests, attendance and shift swaps. I need both development and full data modes and the data should be generated using a fixed seed."

**Explanation:** I used this to work on generating reproducible workforce data for testing the project with different dataset sizes.

### 2. Creating Scheduling Anomalies

**Prompt:**

"How can I add some scheduling problems in my generated data, like an employee assigned to two shifts at the same time, approved leave overlapping with a shift, missing required skills, overtime limit exceeded and a swap applied without approval?"

**Explanation:** This helped me plan test cases for checking whether the system could identify different scheduling problems.

### 3. Validating the Generated Data

**Prompt:**

"Help me write a python validation script to check duplicate IDs, foreign key references, invalid dates, shift overlaps, leave conflicts, missing skills, overtime and attendance records."

**Explanation:** I used this guidance to check the quality and consistency of the generated data.

### 4. Creating the SQLite Database

**Prompt:**

"How do I create an SQLite database from my generated CSV files and create the tables with primary keys and foreign keys? Also help me verify that all records are imported correctly."

**Explanation:** This helped me organize the generated data into relational tables and verify the database after importing the records.

### 5. Building the Streamlit Dashboard

**Prompt:**

"Help me build a Streamlit dashboard for my workforce scheduling project with overview metrics, coverage gaps, scheduling exceptions, workforce data and validation results."

**Explanation:** I used this guidance to organize the dashboard so that important workforce information and scheduling problems could be viewed easily.

### 6. Fixing Code Errors

**Prompt:**

"My code is showing an error. Can you explain why it is happening, help me to fix it ."

**Explanation:** I used this approach when I encountered errors or needed to improve the performance of my existing code.

### 7. Creating Project Documentation

**Prompt:**

"Help me write a simple README for my project with its features, technologies used, folder structure, setup steps, commands to run it and validation results."

**Explanation:** This helped me document how to set up, run and understand the project.

### 8. Creating the Data Dictionary

**Prompt:**

"Help me create a data dictionary for my SQLite database using the actual table names and column names. Explain the purpose of each table, its columns and the relationships between tables."

**Explanation:** I used the database schema output to document the tables and their columns.

### 9. Writing Database Tests

**Prompt:**

"Help me write python unit tests to check whether all expected database tables exist, primary keys are unique and not null, foreign keys are valid and ground truth labels are not stored in the operational database."

**Explanation:** I ran the tests locally to check database integrity. All four automated tests passed.

## Verification

I tested the project in my local environment by generating the full dataset, running the validation script, creating and verifying the SQLite database, running the unit tests and checking the Streamlit dashboard.

- Data validation: 52 checks passed, zero failed.
- Database verification: 27 checks passed, zero failed.
- Automated unit tests: 4 passed.

## Conclusion

ChatGPT helped me when I needed guidance with particular parts of the project. I ran the code in my local environment and checked the output to verify that the implementation was working as expected.
