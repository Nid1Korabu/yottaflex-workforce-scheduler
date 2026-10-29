
import sqlite3
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "workforce.db"

EXPECTED_TABLES = {
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
}


class TestWorkforceDatabase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not DATABASE_PATH.exists():
            raise FileNotFoundError(
                f"Database not found: {DATABASE_PATH}"
            )

        cls.connection = sqlite3.connect(DATABASE_PATH)
        cls.connection.execute("PRAGMA foreign_keys = ON")

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()

    def test_all_operational_tables_exist(self):
        rows = self.connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
        """).fetchall()

        actual_tables = {row[0] for row in rows}

        self.assertEqual(actual_tables, EXPECTED_TABLES)

    def test_primary_keys_are_unique_and_not_null(self):
        for table in sorted(EXPECTED_TABLES):
            columns = self.connection.execute(
                f'PRAGMA table_info("{table}")'
            ).fetchall()

            primary_key_columns = [
                column[1]
                for column in columns
                if column[5] > 0
            ]

            self.assertTrue(
                primary_key_columns,
                f"{table} has no primary key"
            )

            primary_key_columns.sort(
                key=lambda name: next(
                    column[5]
                    for column in columns
                    if column[1] == name
                )
            )

            key_expression = ", ".join(
                f'"{column}"'
                for column in primary_key_columns
            )

            duplicate_query = f"""
                SELECT {key_expression}
                FROM "{table}"
                GROUP BY {key_expression}
                HAVING COUNT(*) > 1
                LIMIT 1
            """

            duplicate = self.connection.execute(
                duplicate_query
            ).fetchone()

            self.assertIsNone(
                duplicate,
                f"Duplicate primary key in {table}: {duplicate}"
            )

            null_conditions = " OR ".join(
                f'"{column}" IS NULL'
                for column in primary_key_columns
            )

            null_query = f"""
                SELECT 1
                FROM "{table}"
                WHERE {null_conditions}
                LIMIT 1
            """

            null_key = self.connection.execute(
                null_query
            ).fetchone()

            self.assertIsNone(
                null_key,
                f"NULL primary-key value in {table}"
            )

    def test_foreign_key_integrity(self):
        violations = self.connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        self.assertEqual(
            violations,
            [],
            f"Foreign-key violations found: {violations[:10]}"
        )

    def test_ground_truth_is_not_in_operational_database(self):
        result = self.connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name LIKE '%ground_truth%'
        """).fetchall()

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
