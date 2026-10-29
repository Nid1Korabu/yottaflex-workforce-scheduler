
from itertools import combinations
from pathlib import Path
import json
import sqlite3

import pandas as pd
import streamlit as st


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Workforce Operations Console",
    page_icon="📊",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "workforce.db"

OPERATIONAL_TABLES = [
    "teams",
    "employees",
    "skills",
    "employee_skills",
    "shift_templates",
    "shift_assignments",
    "leave_requests",
    "holiday_calendar",
    "attendance_events",
    "coverage_requirements",
    "swap_requests",
    "swap_events",
]


# --------------------------------------------------
# 2. LOAD DATA FROM SQLITE
# --------------------------------------------------

@st.cache_data
def load_database_table(table_name, database_modified):
    """Load an operational table from the SQLite database."""
    if table_name not in OPERATIONAL_TABLES:
        raise ValueError(f"Unknown operational table: {table_name}")

    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(
            f'SELECT * FROM "{table_name}"',
            connection,
        )


@st.cache_data
def load_csv(filename):
    """Load derived reports and reference labels from CSV."""
    path = DATA_DIR / filename

    if path.exists():
        return pd.read_csv(path)

    return pd.DataFrame()


@st.cache_data
def load_json(filename):
    """Load a generated JSON report."""
    path = DATA_DIR / filename

    if path.exists():
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    return {}


if not DB_PATH.exists():
    st.error(
        "SQLite database not found. "
        "Run `python src/create_database.py` first."
    )
    st.stop()

database_modified = DB_PATH.stat().st_mtime_ns

try:
    teams = load_database_table("teams", database_modified)
    employees = load_database_table("employees", database_modified)
    skills = load_database_table("skills", database_modified)
    employee_skills = load_database_table(
        "employee_skills", database_modified
    )
    templates = load_database_table(
        "shift_templates", database_modified
    )
    assignments = load_database_table(
        "shift_assignments", database_modified
    )
    leaves = load_database_table("leave_requests", database_modified)
    holidays = load_database_table(
        "holiday_calendar", database_modified
    )
    attendance = load_database_table(
        "attendance_events", database_modified
    )
    requirements = load_database_table(
        "coverage_requirements", database_modified
    )
    swaps = load_database_table("swap_requests", database_modified)
    swap_events = load_database_table(
        "swap_events", database_modified
    )

except Exception as error:
    st.error(f"Could not load the SQLite database: {error}")
    st.stop()


# These are derived/reference outputs, not operational source tables.
coverage = load_csv("coverage_analysis.csv")
ground_truth = load_csv("anomaly_ground_truth.csv")
validation = load_json("validation_summary.json")


# --------------------------------------------------
# 3. HELPER FUNCTIONS
# --------------------------------------------------

def find_col(df, *names):
    """Find a column without depending on capitalization."""
    columns = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for name in names:
        if name.lower() in columns:
            return columns[name.lower()]

    return None


def normalized(value):
    if pd.isna(value):
        return ""

    return str(value).strip().lower()


def date_series(series):
    return pd.to_datetime(series, errors="coerce")


def employee_name(employee_id):
    id_col = find_col(employees, "employee_id")
    name_col = find_col(employees, "employee_name")

    if id_col and name_col:
        match = employees[
            employees[id_col].astype(str) == str(employee_id)
        ]

        if not match.empty:
            return str(match.iloc[0][name_col])

    return str(employee_id)


def assignment_times(df):
    """Read the assignment start and end timestamps."""
    start_col = find_col(df, "shift_start", "start_datetime")
    end_col = find_col(df, "shift_end", "end_datetime")

    if not start_col or not end_col:
        return None, None

    starts = date_series(df[start_col])
    ends = date_series(df[end_col])

    overnight = starts.notna() & ends.notna() & (ends <= starts)
    ends.loc[overnight] += pd.Timedelta(days=1)

    return starts, ends


def add_finding(findings, severity, issue, employee, record, explanation):
    findings.append({
        "Severity": severity,
        "Exception": issue,
        "Employee": str(employee),
        "Record": str(record),
        "Explanation": explanation,
    })


def table_inventory():
    """Build an inventory from the actual database-backed dataframes."""
    datasets = {
        "Employees": employees,
        "Teams": teams,
        "Skills": skills,
        "Employee skills": employee_skills,
        "Shift templates": templates,
        "Shift assignments": assignments,
        "Leave requests": leaves,
        "Holiday calendar": holidays,
        "Attendance events": attendance,
        "Coverage requirements": requirements,
        "Swap requests": swaps,
        "Swap history events": swap_events,
    }

    return pd.DataFrame({
        "Dataset": list(datasets.keys()),
        "Rows": [len(data) for data in datasets.values()],
        "Source": ["SQLite"] * len(datasets),
    })


# --------------------------------------------------
# 4. INDEPENDENT EXCEPTION DETECTION
# --------------------------------------------------

def detect_exceptions():
    findings = []

    emp_col = find_col(assignments, "employee_id")
    team_col = find_col(assignments, "team_id")
    shift_col = find_col(assignments, "shift_name")
    assignment_id_col = find_col(assignments, "assignment_id")

    starts, ends = assignment_times(assignments)

    # A. Overlapping assignments
    if emp_col and starts is not None and ends is not None:
        work = assignments.copy()
        work["_start"] = starts
        work["_end"] = ends
        work = work.dropna(subset=["_start", "_end"])

        for emp_id, group in work.groupby(emp_col):
            records = group.to_dict("records")

            for first, second in combinations(records, 2):
                overlaps = (
                    first["_start"] < second["_end"]
                    and second["_start"] < first["_end"]
                )

                if overlaps:
                    first_id = first.get(
                        assignment_id_col, "Shift 1"
                    )
                    second_id = second.get(
                        assignment_id_col, "Shift 2"
                    )

                    add_finding(
                        findings,
                        "High",
                        "Overlapping assignments",
                        employee_name(emp_id),
                        f"{first_id} / {second_id}",
                        "The employee has two assignments with "
                        "overlapping times.",
                    )

    # B. Assignments during approved leave
    leave_emp = find_col(leaves, "employee_id")
    leave_status = find_col(leaves, "status", "leave_status")
    leave_start = find_col(
        leaves, "start_date", "leave_start_date"
    )
    leave_end = find_col(
        leaves, "end_date", "leave_end_date"
    )
    shift_date = find_col(assignments, "shift_date")

    if all([
        emp_col,
        leave_emp,
        leave_status,
        leave_start,
        leave_end,
        shift_date,
    ]):
        approved = leaves[
            leaves[leave_status].map(normalized).isin(
                ["approved", "accepted"]
            )
        ].copy()

        approved["_start"] = date_series(
            approved[leave_start]
        ).dt.normalize()

        approved["_end"] = date_series(
            approved[leave_end]
        ).dt.normalize()

        scheduled = assignments.copy()
        scheduled["_date"] = date_series(
            scheduled[shift_date]
        ).dt.normalize()

        for _, leave in approved.iterrows():
            matches = scheduled[
                (scheduled[emp_col].astype(str)
                 == str(leave[leave_emp]))
                & (scheduled["_date"] >= leave["_start"])
                & (scheduled["_date"] <= leave["_end"])
            ]

            for _, shift in matches.iterrows():
                record = (
                    shift[assignment_id_col]
                    if assignment_id_col
                    else "Scheduled shift"
                )

                add_finding(
                    findings,
                    "High",
                    "Assignment during approved leave",
                    employee_name(leave[leave_emp]),
                    record,
                    "The assigned shift falls within approved "
                    "leave dates.",
                )

    # C. Missing required skill
    skill_emp = find_col(employee_skills, "employee_id")
    skill_name_col = find_col(employee_skills, "skill_name")
    req_team = find_col(requirements, "team_id")
    req_shift = find_col(requirements, "shift_name")
    req_skill = find_col(requirements, "required_skill")

    if all([
        emp_col,
        team_col,
        shift_col,
        skill_emp,
        skill_name_col,
        req_team,
        req_shift,
        req_skill,
    ]):
        employee_skill_map = {}

        for _, row in employee_skills.iterrows():
            key = str(row[skill_emp])
            employee_skill_map.setdefault(key, set()).add(
                normalized(row[skill_name_col])
            )

        requirement_map = {}

        for _, row in requirements.iterrows():
            key = (
                str(row[req_team]),
                normalized(row[req_shift]),
            )

            requirement_map.setdefault(key, set()).add(
                normalized(row[req_skill])
            )

        for _, assignment in assignments.iterrows():
            key = (
                str(assignment[team_col]),
                normalized(assignment[shift_col]),
            )

            required = requirement_map.get(key, set())
            held = employee_skill_map.get(
                str(assignment[emp_col]), set()
            )

            missing = sorted(
                skill
                for skill in required
                if skill and skill not in held
            )

            if missing:
                record = (
                    assignment[assignment_id_col]
                    if assignment_id_col
                    else "Shift assignment"
                )

                add_finding(
                    findings,
                    "High",
                    "Missing required skill",
                    employee_name(assignment[emp_col]),
                    record,
                    "Required skill missing: " + ", ".join(missing),
                )

    # D. Weekly scheduled hours above each employee's configured cap
    if emp_col and starts is not None and ends is not None:
        work = assignments.copy()
        work["_start"] = starts
        work["_end"] = ends
        work = work.dropna(subset=["_start", "_end"])

        work["_hours"] = (
            work["_end"] - work["_start"]
        ).dt.total_seconds() / 3600

        work["_week"] = (
            work["_start"]
            - pd.to_timedelta(
                work["_start"].dt.day_of_week, unit="D"
            )
        ).dt.normalize()

        weekly = work.groupby(
            [emp_col, "_week"], as_index=False
        )["_hours"].sum()

        employee_id_col = find_col(employees, "employee_id")
        cap_col = find_col(employees, "weekly_hours_cap")

        if employee_id_col and cap_col:
            caps = employees[[employee_id_col, cap_col]].copy()
            caps[cap_col] = pd.to_numeric(
                caps[cap_col], errors="coerce"
            )

            weekly = weekly.merge(
                caps,
                left_on=emp_col,
                right_on=employee_id_col,
                how="left",
            )

            weekly["_cap"] = weekly[cap_col].fillna(40)
        else:
            weekly["_cap"] = 40

        for _, row in weekly[
            weekly["_hours"] > weekly["_cap"]
        ].iterrows():
            add_finding(
                findings,
                "High",
                "Weekly hours exceed cap",
                employee_name(row[emp_col]),
                str(row["_week"].date()),
                f"{row['_hours']:.1f} scheduled hours exceed "
                f"the {row['_cap']:.1f}-hour weekly cap.",
            )

    # E. Swaps applied without manager approval
    # Use the actual employee ID columns from swap_requests.
    swap_id = find_col(swaps, "swap_id", "swap_request_id")

    applied_col = find_col(
        swaps, "applied", "is_applied", "swap_applied"
    )

    approved_col = find_col(
        swaps,
        "manager_approved",
        "approved_by_manager",
        "is_approved",
    )

    swap_emp = find_col(
        swaps,
        "requesting_employee_id",
        "employee_id",
        "requester_id",
    )

    target_emp = find_col(
        swaps,
        "target_employee_id",
        "target_employee",
        "recipient_employee_id",
    )

    if applied_col and approved_col:
        applied = swaps[applied_col].map(normalized).isin(
            ["true", "1", "yes", "applied"]
        )

        approved = swaps[approved_col].map(normalized).isin(
            ["true", "1", "yes", "approved"]
        )

        for _, swap in swaps[applied & ~approved].iterrows():
            record = (
                swap[swap_id] if swap_id else "Swap request"
            )

            if swap_emp:
                requester = employee_name(swap[swap_emp])
            else:
                requester = "Not specified"

            if target_emp:
                target = employee_name(swap[target_emp])
                emp = f"{requester} → {target}"
            else:
                emp = requester

            add_finding(
                findings,
                "High",
                "Swap applied without approval",
                emp,
                record,
                "The swap is marked as applied without "
                "manager approval.",
            )

    return pd.DataFrame(
        findings,
        columns=[
            "Severity",
            "Exception",
            "Employee",
            "Record",
            "Explanation",
        ],
    )


exceptions = detect_exceptions()


# --------------------------------------------------
# 5. NAVIGATION
# --------------------------------------------------

st.sidebar.title("Workforce Console")
st.sidebar.caption("Scheduling, coverage and compliance")

page = st.sidebar.radio(
    "Navigate",
    [
        "Overview",
        "Coverage",
        "Exceptions",
        "Workforce Data",
        "Validation",
    ],
)

st.sidebar.divider()
st.sidebar.caption("Operational data source: SQLite")
st.sidebar.caption("Database: data/workforce.db")
st.sidebar.caption("Synthetic data seed: 20261022")


# --------------------------------------------------
# 6. OVERVIEW
# --------------------------------------------------

if page == "Overview":
    st.title("Workforce Operations Dashboard")
    st.write(
        "Monitor workforce capacity, shift coverage and scheduling risks."
    )

    emp_id = find_col(employees, "employee_id")
    team_id = find_col(teams, "team_id")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Employees",
        employees[emp_id].nunique() if emp_id else len(employees),
    )

    c2.metric(
        "Teams",
        teams[team_id].nunique() if team_id else len(teams),
    )

    c3.metric("Shift assignments", len(assignments))

    staffing_gaps = 0
    skill_gaps = 0

    if not coverage.empty:
        staffing_col = find_col(coverage, "staffing_gap")
        skill_col = find_col(coverage, "skill_gap")

        if staffing_col:
            staffing_gaps = pd.to_numeric(
                coverage[staffing_col], errors="coerce"
            ).fillna(0).gt(0).sum()

        if skill_col:
            skill_gaps = pd.to_numeric(
                coverage[skill_col], errors="coerce"
            ).fillna(0).gt(0).sum()

    c4, c5, c6 = st.columns(3)
    c4.metric("Staffing gap records", int(staffing_gaps))
    c5.metric("Skill gap records", int(skill_gaps))
    c6.metric("Detected exceptions", len(exceptions))

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Scheduling exceptions")

        if exceptions.empty:
            st.success("No exceptions detected by the available checks.")
        else:
            st.dataframe(
                exceptions[
                    ["Severity", "Exception", "Employee", "Record"]
                ],
                width="stretch",
                hide_index=True,
            )

    with right:
        st.subheader("Database inventory")
        st.dataframe(
            table_inventory(),
            width="stretch",
            hide_index=True,
        )

    st.info(
        "Coverage gaps are surfaced for review rather than hidden. "
        "A gap indicates that a staffing or skill requirement may "
        "not be met."
    )


# --------------------------------------------------
# 7. COVERAGE
# --------------------------------------------------

elif page == "Coverage":
    st.title("Shift Coverage Analysis")
    st.write("Filter team and shift coverage results.")

    if coverage.empty:
        st.warning(
            "Coverage analysis is missing. Run "
            "`python src/validate_data.py` first."
        )
    else:
        filtered = coverage.copy()
        team_col = find_col(filtered, "team_id")
        shift_col = find_col(filtered, "shift_name")

        col1, col2 = st.columns(2)

        with col1:
            if team_col:
                values = sorted(
                    filtered[team_col].dropna().astype(str).unique()
                )

                chosen = st.multiselect(
                    "Filter by team",
                    values,
                    default=values,
                )

                filtered = filtered[
                    filtered[team_col].astype(str).isin(chosen)
                ]

        with col2:
            if shift_col:
                values = sorted(
                    filtered[shift_col].dropna().astype(str).unique()
                )

                chosen = st.multiselect(
                    "Filter by shift",
                    values,
                    default=values,
                )

                filtered = filtered[
                    filtered[shift_col].astype(str).isin(chosen)
                ]

        c1, c2 = st.columns(2)
        c1.metric("Coverage records shown", len(filtered))

        staffing_col = find_col(filtered, "staffing_gap")
        skill_col = find_col(filtered, "skill_gap")

        staffing_count = (
            pd.to_numeric(
                filtered[staffing_col], errors="coerce"
            ).fillna(0).gt(0).sum()
            if staffing_col
            else 0
        )

        skill_count = (
            pd.to_numeric(
                filtered[skill_col], errors="coerce"
            ).fillna(0).gt(0).sum()
            if skill_col
            else 0
        )

        c2.metric("Records with staffing gaps", int(staffing_count))
        st.metric("Records with skill gaps", int(skill_count))

        st.dataframe(filtered, width="stretch", hide_index=True)

        st.download_button(
            "Download filtered coverage CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="filtered_coverage_analysis.csv",
            mime="text/csv",
        )


# --------------------------------------------------
# 8. EXCEPTIONS
# --------------------------------------------------

elif page == "Exceptions":
    st.title("Scheduling Exceptions")
    st.write(
        "Findings are calculated from SQLite operational records, "
        "independently of ground-truth anomaly labels."
    )

    if exceptions.empty:
        st.success("No exceptions detected by the available checks.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            severities = sorted(exceptions["Severity"].unique())
            selected_severity = st.multiselect(
                "Severity",
                severities,
                default=severities,
            )

        with col2:
            issue_types = sorted(exceptions["Exception"].unique())
            selected_types = st.multiselect(
                "Exception type",
                issue_types,
                default=issue_types,
            )

        filtered = exceptions[
            exceptions["Severity"].isin(selected_severity)
            & exceptions["Exception"].isin(selected_types)
        ]

        st.metric("Findings shown", len(filtered))
        st.dataframe(filtered, width="stretch", hide_index=True)

        st.download_button(
            "Download exceptions CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="detected_exceptions.csv",
            mime="text/csv",
        )

    st.subheader("Checks included")
    st.markdown("""
    - Overlapping assignments
    - Assignments during approved leave
    - Assignments missing the required skill
    - Weekly scheduled hours above the employee's configured cap
    - Swaps applied without manager approval
    """)


# --------------------------------------------------
# 9. WORKFORCE DATA
# --------------------------------------------------

elif page == "Workforce Data":
    st.title("Workforce Data Explorer")
    st.caption("Operational records are loaded from SQLite.")

    datasets = {
        "Employees": employees,
        "Teams": teams,
        "Skills": skills,
        "Employee Skills": employee_skills,
        "Shift Templates": templates,
        "Shift Assignments": assignments,
        "Leave Requests": leaves,
        "Holiday Calendar": holidays,
        "Attendance Events": attendance,
        "Coverage Requirements": requirements,
        "Swap Requests": swaps,
        "Swap History Events": swap_events,
    }

    selected = st.selectbox(
        "Choose a dataset",
        list(datasets.keys()),
    )

    data = datasets[selected]

    st.subheader(selected)
    st.caption(f"{len(data):,} rows")

    if data.empty:
        st.warning("This dataset is empty.")
    else:
        st.dataframe(data, width="stretch", hide_index=True)

        st.download_button(
            "Download CSV",
            data=data.to_csv(index=False).encode("utf-8"),
            file_name=selected.lower().replace(" ", "_") + ".csv",
            mime="text/csv",
        )


# --------------------------------------------------
# 10. VALIDATION AND GROUND TRUTH
# --------------------------------------------------

elif page == "Validation":
    st.title("Data Validation & Evaluation")

    st.subheader("Database integrity")

    try:
        with sqlite3.connect(DB_PATH) as connection:
            foreign_key_errors = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

            db_table_names = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table'"
                )
            }

        db_checks = [
            (
                "All 12 operational tables exist",
                all(
                    table in db_table_names
                    for table in OPERATIONAL_TABLES
                ),
            ),
            (
                "Foreign-key integrity",
                len(foreign_key_errors) == 0,
            ),
            (
                "Ground-truth labels excluded from database",
                "anomaly_ground_truth" not in db_table_names,
            ),
        ]

        db_passed = sum(result for _, result in db_checks)
        db_failed = len(db_checks) - db_passed

        c1, c2, c3 = st.columns(3)
        c1.metric("Database checks passed", db_passed)
        c2.metric("Database checks failed", db_failed)
        c3.metric("Operational tables", len(OPERATIONAL_TABLES))

        for description, passed in db_checks:
            if passed:
                st.write(f"✅ {description}")
            else:
                st.error(f"❌ {description}")

    except sqlite3.Error as error:
        st.error(f"Database integrity check failed: {error}")

    st.divider()
    st.subheader("Generated data validation")

    if validation:
        c1, c2, c3 = st.columns(3)
        c1.metric("Checks passed", validation.get("checks_passed", 0))
        c2.metric("Checks failed", validation.get("checks_failed", 0))
        c3.metric("Total checks", validation.get("total_checks", 0))

        if validation.get("overall_pass"):
            st.success("The generated data validation report passed.")
        else:
            st.error("The data validation report contains failures.")

        with st.expander("View detailed validation report"):
            st.json(validation)
    else:
        st.warning(
            "Validation summary not found. Run "
            "`python src/validate_data.py`."
        )

    st.divider()
    st.subheader("Evaluation and data integrity")

    st.write(
        "Reference anomaly labels are maintained separately for "
        "validation. They are excluded from operational database "
        "tables and are not used to produce exception findings."
    )

    st.divider()
    st.subheader("Database file")
    

    st.divider()
    st.subheader("Database file")

    if DB_PATH.exists():
        st.write(f"**Path:** `{DB_PATH}`")
        st.write(
            f"**Size:** {DB_PATH.stat().st_size / 1024:.2f} KB"
        )

    st.subheader("Generated supporting files")

    files = sorted(DATA_DIR.glob("*"))

    if files:
        st.dataframe(
            pd.DataFrame({
                "File": [file.name for file in files],
                "Size (KB)": [
                    round(file.stat().st_size / 1024, 2)
                    for file in files
                ],
            }),
            width="stretch",
            hide_index=True,
        )
