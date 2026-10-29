
import csv
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "workforce.db"

# Operational data only. Ground-truth anomaly labels are deliberately
# excluded from the database used by the application.
TABLES = [
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

# Preferred primary keys for each table.
PRIMARY_KEY_CANDIDATES = {
    "teams": ["team_id"],
    "employees": ["employee_id"],
    "skills": ["skill_id"],
    "employee_skills": [],
    "shift_templates": ["shift_template_id"],
    "shift_assignments": ["assignment_id"],
    "leave_requests": ["leave_request_id", "leave_id", "request_id"],
    "holiday_calendar": ["holiday_id"],
    "attendance_events": ["attendance_event_id", "event_id", "attendance_id"],
    "coverage_requirements": ["coverage_id"],
    "swap_requests": ["swap_request_id", "swap_id", "request_id"],
    "swap_events": ["swap_event_id", "event_id"],
}

# Child column -> (parent table, parent column).
# Only relationships whose columns actually exist are added.
FOREIGN_KEY_RULES = {
    "team_id": ("teams", "team_id"),
    "employee_id": ("employees", "employee_id"),
    "skill_id": ("skills", "skill_id"),
    "skill_name": ("skills", "skill_name"),
    "shift_template_id": ("shift_templates", "shift_template_id"),
    "assignment_id": ("shift_assignments", "assignment_id"),
    "leave_request_id": ("leave_requests", "leave_request_id"),
    "leave_id": ("leave_requests", "leave_id"),
    "coverage_id": ("coverage_requirements", "coverage_id"),
    "swap_request_id": ("swap_requests", "swap_request_id"),
    "swap_id": ("swap_requests", "swap_id"),
}


def quote(identifier):
    """Safely quote a SQLite table or column name."""
    return '"' + identifier.replace('"', '""') + '"'


def read_csv(filename):
    path = DATA_DIR / f"{filename}.csv"

    if not path.exists():
        print(f"Skipping {filename}: CSV file not found.")
        return None, []

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames or []
        rows = list(reader)

    if not columns:
        raise ValueError(f"{path.name} has no column headers.")

    return columns, rows


def choose_primary_key(table, columns):
    for candidate in PRIMARY_KEY_CANDIDATES.get(table, []):
        if candidate in columns:
            return [candidate]

    # Employee skills is a many-to-many bridge table.
    if table == "employee_skills":
        if "employee_id" in columns and "skill_name" in columns:
            return ["employee_id", "skill_name"]
        if "employee_id" in columns and "skill_id" in columns:
            return ["employee_id", "skill_id"]

    # Fallback for an unfamiliar ID column.
    for column in columns:
        if column.lower().endswith("_id"):
            return [column]

    return []


def sqlite_type(column):
    name = column.lower()

    if any(word in name for word in ("hour", "duration", "salary", "budget", "price")):
        return "REAL"

    if any(word in name for word in (
        "active", "required_employees", "assigned_employees",
        "qualified_employees", "staffing_gap", "skill_gap"
    )):
        return "INTEGER"

    # Keep IDs, dates, timestamps, statuses, and names as TEXT.
    return "TEXT"


def build_schema(connection, table_info):
    for table, info in table_info.items():
        columns = info["columns"]
        primary_key = info["primary_key"]
        definitions = []

        for column in columns:
            definition = f"{quote(column)} {sqlite_type(column)}"

            # Skill names are referenced by the employee_skills bridge.
            if table == "skills" and column == "skill_name":
                definition += " UNIQUE"

            definitions.append(definition)

        if primary_key:
            pk_columns = ", ".join(quote(column) for column in primary_key)
            definitions.append(f"PRIMARY KEY ({pk_columns})")

        for column in columns:
            parent = None

            if column in FOREIGN_KEY_RULES:
                parent = FOREIGN_KEY_RULES[column]

            # Handle fields such as from_employee_id or requester_employee_id.
            elif column.endswith("_employee_id"):
                parent = ("employees", "employee_id")

            elif column.endswith("_assignment_id"):
                parent = ("shift_assignments", "assignment_id")

            if parent:
                parent_table, parent_column = parent

                if parent_table not in table_info:
                    continue

                if parent_column not in table_info[parent_table]["columns"]:
                    continue

                # Avoid a foreign key pointing at a non-unique parent column.
                parent_info = table_info[parent_table]
                parent_is_unique = (
                    parent_column in parent_info["primary_key"]
                    or (
                        parent_table == "skills"
                        and parent_column == "skill_name"
                    )
                )

                if parent_is_unique:
                    definitions.append(
                        f"FOREIGN KEY ({quote(column)}) "
                        f"REFERENCES {quote(parent_table)}"
                        f"({quote(parent_column)})"
                    )

        sql = (
            f"CREATE TABLE {quote(table)} "
            f"({', '.join(definitions)})"
        )
        connection.execute(sql)


def main():
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Data folder not found: {DATA_DIR}")

    table_info = {}

    # Read and inspect every source table before creating relationships.
    for table in TABLES:
        columns, rows = read_csv(table)

        if columns is None:
            continue

        table_info[table] = {
            "columns": columns,
            "rows": rows,
            "primary_key": choose_primary_key(table, columns),
        }

    if not table_info:
        raise RuntimeError("No CSV files were found in the data folder.")

    # Start with a fresh database so repeated runs are reproducible.
    if DB_PATH.exists():
        DB_PATH.unlink()

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        build_schema(connection, table_info)

        # Import parent tables before their dependent tables.
        import_order = [
            "teams",
            "skills",
            "employees",
            "shift_templates",
            "employee_skills",
            "shift_assignments",
            "leave_requests",
            "holiday_calendar",
            "coverage_requirements",
            "attendance_events",
            "swap_requests",
            "swap_events",
        ]

        imported_counts = {}

        for table in import_order:
            if table not in table_info:
                continue

            info = table_info[table]
            columns = info["columns"]
            rows = info["rows"]

            column_sql = ", ".join(quote(column) for column in columns)
            placeholders = ", ".join("?" for _ in columns)
            insert_sql = (
                f"INSERT INTO {quote(table)} ({column_sql}) "
                f"VALUES ({placeholders})"
            )

            values = [
                tuple(row[column] for column in columns)
                for row in rows
            ]

            if values:
                connection.executemany(insert_sql, values)

            imported_counts[table] = len(rows)
            print(f"Imported {len(rows):>5} rows into {table}")

        # Check database foreign-key integrity.
        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if foreign_key_errors:
            raise RuntimeError(
                "Foreign-key check failed. First errors: "
                + repr(foreign_key_errors[:10])
            )

        connection.commit()

        summary = {
            "database": str(DB_PATH),
            "tables": imported_counts,
            "total_rows": sum(imported_counts.values()),
            "foreign_key_errors": len(foreign_key_errors),
            "ground_truth_included": False,
        }

        summary_path = DATA_DIR / "database_import_summary.json"
        summary_path.write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )

        print("\nDatabase created successfully!")
        print(f"Location: {DB_PATH}")
        print(f"Total rows imported: {summary['total_rows']}")
        print("Foreign-key errors: 0")
        print("Ground-truth anomaly labels: excluded")
        print(f"Import summary: {summary_path}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
