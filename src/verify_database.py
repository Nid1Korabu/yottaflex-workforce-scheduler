
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "workforce.db"

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


def quote(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    passed = 0
    failed = 0

    def check(description, success, detail=""):
        nonlocal passed, failed

        if success:
            passed += 1
            print(f"PASS: {description}")
        else:
            failed += 1
            print(f"FAIL: {description}")

        if detail:
            print(f"      {detail}")

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        existing_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

        check(
            "All 12 operational tables exist",
            all(table in existing_tables for table in TABLES),
        )

        total_rows = 0

        for table in TABLES:
            if table not in existing_tables:
                continue

            db_count = connection.execute(
                f"SELECT COUNT(*) FROM {quote(table)}"
            ).fetchone()[0]

            csv_path = DATA_DIR / f"{table}.csv"

            with csv_path.open(
                "r", encoding="utf-8-sig", newline=""
            ) as file:
                csv_count = sum(1 for _ in csv.DictReader(file))

            total_rows += db_count

            check(
                f"{table}: CSV count matches database",
                db_count == csv_count,
                f"CSV={csv_count}, database={db_count}",
            )

            # Inspect the actual primary key defined in SQLite.
            columns = connection.execute(
                f"PRAGMA table_info({quote(table)})"
            ).fetchall()

            primary_key_columns = [
                row[1]
                for row in sorted(columns, key=lambda row: row[5])
                if row[5] > 0
            ]

            if primary_key_columns:
                group_columns = ", ".join(
                    quote(column) for column in primary_key_columns
                )

                duplicates = connection.execute(
                    f"SELECT COUNT(*) FROM ("
                    f"SELECT {group_columns} FROM {quote(table)} "
                    f"GROUP BY {group_columns} HAVING COUNT(*) > 1"
                    f")"
                ).fetchone()[0]

                null_conditions = " OR ".join(
                    f"{quote(column)} IS NULL"
                    for column in primary_key_columns
                )

                null_keys = connection.execute(
                    f"SELECT COUNT(*) FROM {quote(table)} "
                    f"WHERE {null_conditions}"
                ).fetchone()[0]

                check(
                    f"{table}: primary key is unique and non-null",
                    duplicates == 0 and null_keys == 0,
                    f"duplicate keys={duplicates}, null keys={null_keys}",
                )
            else:
                check(
                    f"{table}: primary key defined",
                    False,
                    "No primary key was found in the SQLite schema.",
                )

        fk_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        check(
            "Foreign-key relationships are valid",
            len(fk_errors) == 0,
            f"foreign-key errors={len(fk_errors)}",
        )

        check(
            "Ground-truth labels are not stored in operational tables",
            "anomaly_ground_truth" not in existing_tables,
        )

        print("\n--- Database summary ---")
        print(f"Database: {DB_PATH}")
        print(f"Operational tables: {len(TABLES)}")
        print(f"Total records: {total_rows}")
        print(f"Checks passed: {passed}")
        print(f"Checks failed: {failed}")

        if failed:
            print("\nSome checks failed. Save the output and send it to me.")
        else:
            print("\nAll database verification checks passed!")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
