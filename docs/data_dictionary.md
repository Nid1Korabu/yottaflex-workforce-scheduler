# Data Dictionary

## 1. Overview

This document describes the columns in the 12 operational SQLite tables used by the Workforce Scheduling & Compliance Console.

Column names and SQLite data types below are based on the database schema inspected in `data/workforce.db`.

- `TEXT` is used for identifiers, names, statuses, dates, timestamps, and other text values.
- `INTEGER` is used for whole-number values and Boolean-like flags.
- `REAL` is used for numeric values that may contain decimals.
- `PRIMARY KEY` identifies a row uniquely. Some tables use composite primary keys.
- `FOREIGN KEY` links a column to a record in another table.

Date and timestamp values are stored as text in this database. Their precise formatting is determined by the data generator.

## 2. Teams

**Purpose:** Stores workforce team records.

| Column | Type | Key | Description |
|---|---|---|---|
| `team_id` | TEXT | Primary key | Unique identifier for a team. |
| `team_name` | TEXT | — | Display name of the team. |

## 3. Employees

**Purpose:** Stores employee information and weekly working-hour limits.

| Column | Type | Key | Description |
|---|---|---|---|
| `employee_id` | TEXT | Primary key | Unique employee identifier. |
| `employee_name` | TEXT | — | Employee display name. |
| `team_id` | TEXT | Foreign key → `teams.team_id` | Team associated with the employee. |
| `weekly_hours_cap` | REAL | — | Configured maximum weekly hours for the employee. |
| `active` | INTEGER | — | Integer flag indicating whether the employee is active. |

## 4. Skills

**Purpose:** Defines the skills available in the workforce.

| Column | Type | Key | Description |
|---|---|---|---|
| `skill_id` | TEXT | Primary key | Unique skill identifier. |
| `skill_name` | TEXT | — | Skill name used in employee qualifications and coverage requirements. |

## 5. Employee Skills

**Purpose:** Implements the many-to-many relationship between employees and skills.

| Column | Type | Key | Description |
|---|---|---|---|
| `employee_id` | TEXT | Composite primary key; foreign key → `employees.employee_id` | Employee possessing the skill. |
| `skill_name` | TEXT | Composite primary key; foreign key → `skills.skill_name` | Skill associated with the employee. |

The composite primary key prevents the same employee-skill pair from appearing more than once.

## 6. Shift Templates

**Purpose:** Defines reusable shift patterns.

| Column | Type | Key | Description |
|---|---|---|---|
| `shift_template_id` | TEXT | Primary key | Unique shift-template identifier. |
| `shift_name` | TEXT | — | Name of the shift. |
| `start_time` | TEXT | — | Scheduled start time represented as text. |
| `duration_hours` | REAL | — | Planned shift duration in hours. |

## 7. Shift Assignments

**Purpose:** Records employee shift assignments and their scheduled times.

| Column | Type | Key | Description |
|---|---|---|---|
| `assignment_id` | TEXT | Primary key | Unique assignment identifier. |
| `employee_id` | TEXT | Foreign key → `employees.employee_id` | Employee assigned to the shift. |
| `team_id` | TEXT | Foreign key → `teams.team_id` | Team responsible for the assignment. |
| `shift_template_id` | TEXT | Foreign key → `shift_templates.shift_template_id` | Shift template used for the assignment. |
| `shift_date` | TEXT | — | Calendar date of the shift. |
| `shift_name` | TEXT | — | Name of the assigned shift. |
| `start_hour` | REAL | — | Numeric start-hour value used by the scheduling data. |
| `duration_hours` | REAL | — | Scheduled duration in hours. |
| `shift_start` | TEXT | — | Scheduled shift start timestamp. |
| `shift_end` | TEXT | — | Scheduled shift end timestamp. |
| `status` | TEXT | — | Assignment lifecycle status. |

The generator and validation scripts check consistency between shift timestamps, dates, durations, and templates.

## 8. Leave Requests

**Purpose:** Stores employee leave requests and decision information.

| Column | Type | Key | Description |
|---|---|---|---|
| `leave_id` | TEXT | Primary key | Unique leave-request identifier. |
| `employee_id` | TEXT | Foreign key → `employees.employee_id` | Employee requesting leave. |
| `start_date` | TEXT | — | First date covered by the leave request. |
| `end_date` | TEXT | — | Last date covered by the leave request. |
| `leave_type` | TEXT | — | Category of leave. |
| `status` | TEXT | — | Current leave-request status. |
| `requested_at` | TEXT | — | Timestamp when the request was submitted. |
| `decided_at` | TEXT | — | Timestamp when a decision was recorded, where applicable. |

## 9. Holiday Calendar

**Purpose:** Stores calendar holidays used in workforce scheduling.

| Column | Type | Key | Description |
|---|---|---|---|
| `holiday_id` | TEXT | Primary key | Unique holiday identifier. |
| `holiday_date` | TEXT | — | Date of the holiday. |
| `holiday_name` | TEXT | — | Name of the holiday. |
| `region` | TEXT | — | Region associated with the holiday. |
| `source_type` | TEXT | — | Classification of the holiday record's source. |

The dataset is synthetic; holiday records should not be assumed to represent a complete official holiday calendar.

## 10. Attendance Events

**Purpose:** Records attendance events associated with employees and shift assignments.

| Column | Type | Key | Description |
|---|---|---|---|
| `attendance_id` | TEXT | Primary key | Unique attendance-event identifier. |
| `employee_id` | TEXT | Foreign key → `employees.employee_id` | Employee associated with the event. |
| `assignment_id` | TEXT | Foreign key → `shift_assignments.assignment_id` | Shift assignment associated with the event. |
| `event_type` | TEXT | — | Type of attendance event, such as clock-in or clock-out. |
| `event_timestamp` | TEXT | — | Timestamp when the event occurred. |

The validation process checks attendance-event types and reconciles generated attendance events with shift assignments.

## 11. Coverage Requirements

**Purpose:** Defines staffing and skill requirements for teams and shifts.

| Column | Type | Key | Description |
|---|---|---|---|
| `coverage_id` | TEXT | Primary key | Unique coverage-requirement identifier. |
| `team_id` | TEXT | Foreign key → `teams.team_id` | Team whose coverage is being evaluated. |
| `shift_name` | TEXT | — | Shift to which the requirement applies. |
| `required_employees` | INTEGER | — | Minimum number of employees required. |
| `required_skill` | TEXT | — | Skill required for the coverage requirement. |

The coverage analysis compares staffing and employee qualifications against the configured requirements.

## 12. Swap Requests

**Purpose:** Stores requests to exchange shifts between employees and their approval/application status.

| Column | Type | Key | Description |
|---|---|---|---|
| `swap_id` | TEXT | Primary key | Unique swap-request identifier. |
| `requesting_employee_id` | TEXT | Foreign key → `employees.employee_id` | Employee initiating the request. |
| `target_employee_id` | TEXT | Foreign key → `employees.employee_id` | Employee targeted by the request. |
| `status` | TEXT | — | Current swap-request status. |
| `manager_approved` | TEXT | — | Stored indicator of manager approval. |
| `applied` | TEXT | — | Stored indicator of whether the swap was applied. |
| `requested_at` | TEXT | — | Timestamp when the swap was requested. |
| `decided_at` | TEXT | — | Timestamp when a decision was recorded, where applicable. |
| `applied_at` | TEXT | — | Timestamp when the swap was applied, where applicable. |

The approval and application fields are stored as text in the current schema. Their allowed values are governed by the generator and validation logic.

## 13. Swap Events

**Purpose:** Maintains the lifecycle history of shift-swap requests.

| Column | Type | Key | Description |
|---|---|---|---|
| `swap_event_id` | TEXT | Primary key | Unique swap-history event identifier. |
| `swap_id` | TEXT | Foreign key → `swap_requests.swap_id` | Swap request associated with the event. |
| `event_type` | TEXT | — | Type of lifecycle event. |
| `event_timestamp` | TEXT | — | Timestamp when the event occurred. |
| `actor` | TEXT | — | Actor associated with the event. |
| `details` | TEXT | — | Additional information describing the event. |

Keeping swap events separate from the current swap-request record allows the project to preserve a history of lifecycle changes.

## 14. Key Relationships

- One team can have multiple employees and shift assignments.
- Employees and skills are connected through `employee_skills`.
- One employee can have multiple shift assignments, leave requests, and attendance events.
- Each shift assignment references an employee, team, and shift template.
- Coverage requirements reference teams and skills.
- Swap requests identify requesting and target employees.
- Swap events preserve the history of their associated swap requests.

## 15. Validation and Evaluation

The full-scale database verification reported 27 checks passed and zero failed. Generated-data validation reported 52 checks passed and zero failed.

The operational database excludes the separate ground-truth anomaly labels. The dashboard evaluates scheduling exceptions using operational records, while the reference labels are retained for independent evaluation.

For database creation and integrity checks, see:

- `src/create_database.py`
- `src/verify_database.py`
- `src/validate_data.py`
