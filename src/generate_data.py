
import argparse
import json
import random
from collections import Counter
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd


# ==================================================
# 1. CONFIGURATION
# ==================================================

DEFAULT_SEED = 20261022
START_DATE = date(2026, 11, 1)

SKILLS = [
    "Customer Support",
    "First Aid",
    "Technical Support",
    "Team Lead",
]

SHIFT_CONFIG = [
    {
        "shift_name": "Morning",
        "start_hour": 6,
        "duration_hours": 8,
        "short_code": "M",
    },
    {
        "shift_name": "Evening",
        "start_hour": 14,
        "duration_hours": 8,
        "short_code": "E",
    },
    {
        "shift_name": "Night",
        "start_hour": 22,
        "duration_hours": 8,
        "short_code": "N",
    },
]

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ==================================================
# 2. HELPER FUNCTIONS
# ==================================================

def make_timestamp(day, hour=9):
    return datetime.combine(day, time(hour=hour)).isoformat()


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic workforce scheduling data."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Generate the full assessment dataset.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Random seed for reproducible data.",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)

    if args.full:
        employee_count = 2000
        team_count = 100
        number_of_days = 90
        leave_count = 5000
        required_per_shift = 3
        swap_count = 200
        mode = "full"
    else:
        employee_count = 50
        team_count = 4
        number_of_days = 14
        leave_count = 15
        required_per_shift = 2
        swap_count = 10
        mode = "development"

    dates = [
        START_DATE + timedelta(days=i)
        for i in range(number_of_days)
    ]

    assignment_counter = 1

    def new_assignment_id():
        nonlocal assignment_counter
        result = f"ASN-{assignment_counter:06d}"
        assignment_counter += 1
        return result

    # ==================================================
    # 3. TEAMS
    # ==================================================

    starter_team_names = [
        "Support",
        "Operations",
        "Engineering",
        "Sales",
    ]

    teams = []

    for i in range(1, team_count + 1):
        team_name = (
            starter_team_names[i - 1]
            if not args.full
            else f"Team {i:03d}"
        )

        teams.append({
            "team_id": f"TEAM-{i:03d}",
            "team_name": team_name,
        })

    team_ids = [team["team_id"] for team in teams]

    # ==================================================
    # 4. EMPLOYEES
    # ==================================================

    employees = []

    for i in range(1, employee_count + 1):
        employees.append({
            "employee_id": f"EMP-{i:06d}",
            "employee_name": f"Employee {i:04d}",
            "team_id": team_ids[(i - 1) % team_count],
            "weekly_hours_cap": 40,
            "active": True,
        })

    employees_by_id = {
        employee["employee_id"]: employee
        for employee in employees
    }

    team_members = {team_id: [] for team_id in team_ids}

    for employee in employees:
        team_members[employee["team_id"]].append(
            employee["employee_id"]
        )

    # ==================================================
    # 5. SKILLS
    # ==================================================

    skills = [
        {
            "skill_id": f"SKL-{i:03d}",
            "skill_name": skill,
        }
        for i, skill in enumerate(SKILLS, start=1)
    ]

    employee_skill_sets = {
        employee["employee_id"]: set()
        for employee in employees
    }

    for team_id in team_ids:
        members = team_members[team_id]
        guaranteed_count = min(5, len(members))

        for skill in SKILLS:
            selected = rng.sample(members, guaranteed_count)

            for employee_id in selected:
                employee_skill_sets[employee_id].add(skill)

    for employee in employees:
        employee_id = employee["employee_id"]
        current_skills = employee_skill_sets[employee_id]

        while len(current_skills) < 2:
            current_skills.add(rng.choice(SKILLS))

        extra_skills = [
            skill for skill in SKILLS
            if skill not in current_skills
        ]

        if extra_skills:
            additional_count = rng.randint(
                0, min(2, len(extra_skills))
            )

            current_skills.update(
                rng.sample(extra_skills, additional_count)
            )

    employee_skills = []

    for employee_id, skill_set in employee_skill_sets.items():
        for skill in sorted(skill_set):
            employee_skills.append({
                "employee_id": employee_id,
                "skill_name": skill,
            })

    # ==================================================
    # 6. SHIFT TEMPLATES
    # ==================================================

    shift_templates = []

    for shift in SHIFT_CONFIG:
        shift_templates.append({
            "shift_template_id": f"TPL-{shift['short_code']}",
            "shift_name": shift["shift_name"],
            "start_time": f"{shift['start_hour']:02d}:00",
            "duration_hours": shift["duration_hours"],
        })

    # ==================================================
    # 7. COVERAGE REQUIREMENTS
    # ==================================================

    coverage_requirements = []

    for team_index, team_id in enumerate(team_ids):
        for shift_index, shift in enumerate(SHIFT_CONFIG):
            required_skill = SKILLS[
                (team_index + shift_index) % len(SKILLS)
            ]

            coverage_requirements.append({
                "coverage_id": (
                    f"COV-{team_id}-{shift['short_code']}"
                ),
                "team_id": team_id,
                "shift_name": shift["shift_name"],
                "required_employees": required_per_shift,
                "required_skill": required_skill,
            })

    requirement_lookup = {
        (row["team_id"], row["shift_name"]): row
        for row in coverage_requirements
    }

    # ==================================================
    # 8. LEAVE REQUESTS
    # ==================================================

    leave_requests = []

    for i in range(1, leave_count + 1):
        employee_id = rng.choice([
            employee["employee_id"] for employee in employees
        ])

        leave_start = rng.choice(dates)

        duration_days = rng.choices(
            [1, 2, 3],
            weights=[60, 30, 10],
            k=1,
        )[0]

        leave_end = min(
            leave_start + timedelta(days=duration_days - 1),
            dates[-1],
        )

        status = rng.choices(
            ["PENDING", "APPROVED", "REJECTED"],
            weights=[25, 45, 30],
            k=1,
        )[0]

        requested_at = make_timestamp(
            leave_start - timedelta(days=7), 10
        )

        decided_at = ""

        if status != "PENDING":
            decided_at = make_timestamp(
                leave_start - timedelta(days=2), 11
            )

        leave_requests.append({
            "leave_id": f"LVE-2026-{i:06d}",
            "employee_id": employee_id,
            "start_date": leave_start.isoformat(),
            "end_date": leave_end.isoformat(),
            "leave_type": rng.choice(
                ["ANNUAL", "SICK", "PERSONAL"]
            ),
            "status": status,
            "requested_at": requested_at,
            "decided_at": decided_at,
        })

    def approved_leave_dates():
        result = {}

        for leave in leave_requests:
            if leave["status"] == "APPROVED":
                result.setdefault(
                    leave["employee_id"], []
                ).append((
                    date.fromisoformat(leave["start_date"]),
                    date.fromisoformat(leave["end_date"]),
                ))

        return result

    approved_leaves = approved_leave_dates()

    def is_on_approved_leave(employee_id, day):
        return any(
            start <= day <= end
            for start, end in approved_leaves.get(employee_id, [])
        )

    # ==================================================
    # 9. SYNTHETIC HOLIDAY CALENDAR
    # ==================================================

    holiday_calendar = []

    for i, day_index in enumerate(
        range(6, number_of_days, 21),
        start=1,
    ):
        holiday_calendar.append({
            "holiday_id": f"HOL-{i:03d}",
            "holiday_date": dates[day_index].isoformat(),
            "holiday_name": f"Synthetic Test Holiday {i}",
            "region": "ALL",
            "source_type": "SYNTHETIC_TEST_DATA",
        })

    # ==================================================
    # 10. BASELINE SCHEDULE
    # ==================================================

    assignments = []
    assigned_on_date = set()
    weekly_hours = {}
    last_shift_end = {}
    employee_shift_count = {}

    for day in dates:
        for team_id in team_ids:
            for shift in SHIFT_CONFIG:
                shift_name = shift["shift_name"]

                requirement = requirement_lookup[
                    (team_id, shift_name)
                ]

                required_skill = requirement["required_skill"]

                shift_start = datetime.combine(
                    day,
                    time(hour=shift["start_hour"]),
                )

                shift_end = shift_start + timedelta(
                    hours=shift["duration_hours"]
                )

                week_start = day - timedelta(days=day.weekday())
                candidates = []

                for employee_id in team_members[team_id]:
                    employee = employees_by_id[employee_id]

                    if not employee["active"]:
                        continue

                    if required_skill not in employee_skill_sets[employee_id]:
                        continue

                    if is_on_approved_leave(employee_id, day):
                        continue

                    if (employee_id, day) in assigned_on_date:
                        continue

                    # FIX: calculate weekly hours separately for each
                    # candidate, rather than keeping one shared key.
                    hours_key = (employee_id, week_start)

                    if (
                        weekly_hours.get(hours_key, 0)
                        + shift["duration_hours"]
                        > employee["weekly_hours_cap"]
                    ):
                        continue

                    previous_end = last_shift_end.get(employee_id)

                    if previous_end is not None:
                        if (
                            shift_start
                            < previous_end + timedelta(hours=10)
                        ):
                            continue

                    candidates.append(employee_id)

                rng.shuffle(candidates)

                candidates.sort(
                    key=lambda employee_id: (
                        weekly_hours.get(
                            (employee_id, week_start), 0
                        ),
                        employee_shift_count.get(employee_id, 0),
                    )
                )

                selected_count = 0

                for employee_id in candidates:
                    if (
                        selected_count
                        >= requirement["required_employees"]
                    ):
                        break

                    # FIX: use the selected employee's own weekly-hours key.
                    hours_key = (employee_id, week_start)
                    employee = employees_by_id[employee_id]

                    # Recheck the cap immediately before assigning.
                    if (
                        weekly_hours.get(hours_key, 0)
                        + shift["duration_hours"]
                        > employee["weekly_hours_cap"]
                    ):
                        continue

                    assignment = {
                        "assignment_id": new_assignment_id(),
                        "employee_id": employee_id,
                        "team_id": team_id,
                        "shift_template_id": (
                            f"TPL-{shift['short_code']}"
                        ),
                        "shift_date": day.isoformat(),
                        "shift_name": shift_name,
                        "start_hour": shift["start_hour"],
                        "duration_hours": shift["duration_hours"],
                        "shift_start": shift_start.isoformat(),
                        "shift_end": shift_end.isoformat(),
                        "status": "ASSIGNED",
                    }

                    assignments.append(assignment)

                    assigned_on_date.add((employee_id, day))

                    weekly_hours[hours_key] = (
                        weekly_hours.get(hours_key, 0)
                        + shift["duration_hours"]
                    )

                    last_shift_end[employee_id] = shift_end

                    employee_shift_count[employee_id] = (
                        employee_shift_count.get(employee_id, 0) + 1
                    )

                    selected_count += 1

    # ==================================================
    # 11. INJECT FIVE TEST ANOMALIES
    # ==================================================

    anomalies = []

    def record_anomaly(
        anomaly_id,
        anomaly_type,
        description,
        record_id,
        related_id="",
        expected_skill="",
    ):
        anomalies.append({
            "anomaly_id": anomaly_id,
            "anomaly_type": anomaly_type,
            "description": description,
            "record_id": record_id,
            "related_id": related_id,
            "expected_skill": expected_skill,
        })

    if not assignments:
        raise RuntimeError(
            "No shifts were generated. Check the schedule settings."
        )

    # ANOM-001: duplicate one assignment to create an overlap.
    original = assignments[0].copy()
    double_booking_employee_id = original["employee_id"]

    duplicate = original.copy()
    duplicate["assignment_id"] = new_assignment_id()
    assignments.append(duplicate)

    record_anomaly(
        "ANOM-001",
        "DOUBLE_BOOKING",
        "One employee has overlapping shift assignments.",
        duplicate["assignment_id"],
        original["assignment_id"],
    )

    # ANOM-002: approved leave overlaps a different employee's shift.
    leave_assignment = next(
        (
            assignment for assignment in assignments
            if assignment["employee_id"]
            != double_booking_employee_id
        ),
        None,
    )

    if leave_assignment is None:
        raise RuntimeError(
            "Could not find a separate leave anomaly assignment."
        )

    leave_anomaly_employee_id = leave_assignment["employee_id"]
    leave_id = "LVE-2026-999901"

    leave_requests.append({
        "leave_id": leave_id,
        "employee_id": leave_anomaly_employee_id,
        "start_date": leave_assignment["shift_date"],
        "end_date": leave_assignment["shift_date"],
        "leave_type": "ANNUAL",
        "status": "APPROVED",
        "requested_at": make_timestamp(
            date.fromisoformat(leave_assignment["shift_date"])
            - timedelta(days=7),
            10,
        ),
        "decided_at": make_timestamp(
            date.fromisoformat(leave_assignment["shift_date"])
            - timedelta(days=2),
            11,
        ),
    })

    record_anomaly(
        "ANOM-002",
        "APPROVED_LEAVE_OVERLAP",
        "Approved leave overlaps a scheduled shift.",
        leave_id,
        leave_assignment["assignment_id"],
    )

    # ANOM-003: remove a skill needed by exactly one assignment.
    assignment_skill_counts = Counter()

    for assignment in assignments:
        req = requirement_lookup[
            (assignment["team_id"], assignment["shift_name"])
        ]

        assignment_skill_counts[
            (assignment["employee_id"], req["required_skill"])
        ] += 1

    skill_anomaly_assignment = None
    missing_skill = None

    for assignment in assignments:
        employee_id = assignment["employee_id"]

        if employee_id in {
            double_booking_employee_id,
            leave_anomaly_employee_id,
        }:
            continue

        req = requirement_lookup[
            (assignment["team_id"], assignment["shift_name"])
        ]

        required_skill = req["required_skill"]

        if (
            required_skill in employee_skill_sets[employee_id]
            and assignment_skill_counts[
                (employee_id, required_skill)
            ] == 1
        ):
            skill_anomaly_assignment = assignment
            missing_skill = required_skill
            break

    if skill_anomaly_assignment is None:
        raise RuntimeError(
            "Could not find a unique assignment for the missing-skill anomaly."
        )

    skill_employee_id = skill_anomaly_assignment["employee_id"]

    employee_skill_sets[skill_employee_id].remove(missing_skill)

    employee_skills = [
        row for row in employee_skills
        if not (
            row["employee_id"] == skill_employee_id
            and row["skill_name"] == missing_skill
        )
    ]

    record_anomaly(
        "ANOM-003",
        "MISSING_REQUIRED_SKILL",
        "The assigned employee lacks the required shift skill.",
        skill_anomaly_assignment["assignment_id"],
        expected_skill=missing_skill,
    )

    # ANOM-004: deliberately inject six eight-hour shifts in one week.
    if number_of_days >= 14:
        overtime_dates = dates[8:14]

        morning_requirements = {
            team_id: requirement_lookup[
                (team_id, "Morning")
            ]["required_skill"]
            for team_id in team_ids
        }

        overtime_employee = None

        for employee in employees:
            employee_id = employee["employee_id"]
            morning_skill = morning_requirements[
                employee["team_id"]
            ]

            if morning_skill not in employee_skill_sets[employee_id]:
                continue

            if any(
                is_on_approved_leave(employee_id, day)
                for day in overtime_dates
            ):
                continue

            if employee_id in {
                double_booking_employee_id,
                leave_anomaly_employee_id,
                skill_employee_id,
            }:
                continue

            overtime_employee = employee
            break

        if overtime_employee is None:
            raise RuntimeError(
                "Could not find an employee for overtime test."
            )

        overtime_employee_id = overtime_employee["employee_id"]
        overtime_team_id = overtime_employee["team_id"]

        dates_to_replace = {
            dates[7].isoformat(),
            *(day.isoformat() for day in overtime_dates),
        }

        # Remove this employee's baseline assignments for the affected
        # dates before injecting the intentional overtime anomaly.
        assignments = [
            assignment for assignment in assignments
            if not (
                assignment["employee_id"] == overtime_employee_id
                and assignment["shift_date"] in dates_to_replace
            )
        ]

        for day in overtime_dates:
            shift_start = datetime.combine(day, time(hour=6))
            shift_end = shift_start + timedelta(hours=8)

            assignments.append({
                "assignment_id": new_assignment_id(),
                "employee_id": overtime_employee_id,
                "team_id": overtime_team_id,
                "shift_template_id": "TPL-M",
                "shift_date": day.isoformat(),
                "shift_name": "Morning",
                "start_hour": 6,
                "duration_hours": 8,
                "shift_start": shift_start.isoformat(),
                "shift_end": shift_end.isoformat(),
                "status": "ASSIGNED",
            })

        record_anomaly(
            "ANOM-004",
            "OVERTIME_CAP_EXCEEDED",
            "Employee has six eight-hour shifts in one week.",
            overtime_employee_id,
        )

    # ==================================================
    # 12. SWAP REQUESTS AND HISTORY
    # ==================================================

    swap_requests = []

    employee_ids = [
        employee["employee_id"] for employee in employees
    ]

    for i in range(1, swap_count + 1):
        requester, target = rng.sample(employee_ids, 2)

        status = rng.choices(
            ["PENDING", "APPROVED", "REJECTED"],
            weights=[35, 40, 25],
            k=1,
        )[0]

        requested_at = make_timestamp(
            START_DATE - timedelta(days=10), 9
        )

        decided_at = ""

        if status != "PENDING":
            decided_at = make_timestamp(
                START_DATE - timedelta(days=9), 12
            )

        swap_requests.append({
            "swap_id": f"SWP-2026-{i:06d}",
            "requesting_employee_id": requester,
            "target_employee_id": target,
            "status": status,
            "manager_approved": status == "APPROVED",
            "applied": False,
            "requested_at": requested_at,
            "decided_at": decided_at,
            "applied_at": "",
        })

    # ANOM-005: applied even though approval is pending.
    swap_requests[0]["status"] = "PENDING"
    swap_requests[0]["manager_approved"] = False
    swap_requests[0]["applied"] = True
    swap_requests[0]["applied_at"] = make_timestamp(
        START_DATE - timedelta(days=8), 15
    )

    record_anomaly(
        "ANOM-005",
        "UNAPPROVED_SWAP_APPLIED",
        "A shift swap was applied without manager approval.",
        swap_requests[0]["swap_id"],
    )

    swap_events = []
    swap_event_counter = 1

    def add_swap_event(
        swap_id,
        event_type,
        timestamp,
        actor,
        details,
    ):
        nonlocal swap_event_counter

        swap_events.append({
            "swap_event_id": f"SWPEVT-{swap_event_counter:06d}",
            "swap_id": swap_id,
            "event_type": event_type,
            "event_timestamp": timestamp,
            "actor": actor,
            "details": details,
        })

        swap_event_counter += 1

    for swap in swap_requests:
        add_swap_event(
            swap["swap_id"],
            "REQUESTED",
            swap["requested_at"],
            swap["requesting_employee_id"],
            "Swap request created.",
        )

        if swap["status"] == "APPROVED":
            add_swap_event(
                swap["swap_id"],
                "MANAGER_APPROVED",
                swap["decided_at"],
                "MANAGER",
                "Swap approved by manager.",
            )

        elif swap["status"] == "REJECTED":
            add_swap_event(
                swap["swap_id"],
                "MANAGER_REJECTED",
                swap["decided_at"],
                "MANAGER",
                "Swap rejected by manager.",
            )

        if swap["applied"]:
            add_swap_event(
                swap["swap_id"],
                "APPLIED",
                swap["applied_at"],
                "SYSTEM",
                "Swap applied to the schedule.",
            )

    # ==================================================
    # 13. ATTENDANCE EVENTS
    # ==================================================

    attendance_events = []

    for assignment in assignments:
        employee_id = assignment["employee_id"]
        assignment_id = assignment["assignment_id"]

        attendance_events.append({
            "attendance_id": f"ATT-{len(attendance_events) + 1:08d}",
            "employee_id": employee_id,
            "assignment_id": assignment_id,
            "event_type": "CLOCK_IN",
            "event_timestamp": assignment["shift_start"],
        })

        attendance_events.append({
            "attendance_id": f"ATT-{len(attendance_events) + 1:08d}",
            "employee_id": employee_id,
            "assignment_id": assignment_id,
            "event_type": "CLOCK_OUT",
            "event_timestamp": assignment["shift_end"],
        })

    # ==================================================
    # 14. EXPORT CSV FILES
    # ==================================================

    tables = {
        "teams": teams,
        "employees": employees,
        "skills": skills,
        "employee_skills": employee_skills,
        "shift_templates": shift_templates,
        "shift_assignments": assignments,
        "leave_requests": leave_requests,
        "holiday_calendar": holiday_calendar,
        "attendance_events": attendance_events,
        "coverage_requirements": coverage_requirements,
        "swap_requests": swap_requests,
        "swap_events": swap_events,
    }

    for table_name, rows in tables.items():
        pd.DataFrame(rows).to_csv(
            DATA_DIR / f"{table_name}.csv",
            index=False,
        )

    pd.DataFrame(
        anomalies,
        columns=[
            "anomaly_id",
            "anomaly_type",
            "description",
            "record_id",
            "related_id",
            "expected_skill",
        ],
    ).to_csv(
        DATA_DIR / "anomaly_ground_truth.csv",
        index=False,
    )

    metadata = {
        "seed": args.seed,
        "mode": mode,
        "start_date": START_DATE.isoformat(),
        "number_of_days": number_of_days,
        "employee_count_requested": employee_count,
        "team_count_requested": team_count,
        "leave_request_count_requested": leave_count,
        "required_employees_per_shift": required_per_shift,
        "anomalies_injected": len(anomalies),
        "data_type": "Synthetic test data",
        "note": (
            "Holiday entries are synthetic examples, "
            "not an official public holiday feed."
        ),
    }

    with open(
        DATA_DIR / "generation_metadata.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(metadata, file, indent=2)

    source_manifest = {
        "source_type": "Synthetic data generated locally",
        "seed": args.seed,
        "generator": "src/generate_data.py",
        "tables": {
            f"{table_name}.csv": "Synthetic records"
            for table_name in tables
        },
        "labels_file": "anomaly_ground_truth.csv",
        "labels_are_separate_from_input_tables": True,
    }

    with open(
        DATA_DIR / "source_manifest.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(source_manifest, file, indent=2)

    # ==================================================
    # 15. PRINT SUMMARY
    # ==================================================

    print("\nWorkforce data generated successfully!")
    print(f"Mode: {mode}")
    print(f"Seed: {args.seed}")
    print(f"Employees: {len(employees)}")
    print(f"Teams: {len(teams)}")
    print(f"Skills: {len(skills)}")
    print(f"Employee-skill records: {len(employee_skills)}")
    print(f"Shift assignments: {len(assignments)}")
    print(f"Leave requests: {len(leave_requests)}")
    print(f"Attendance events: {len(attendance_events)}")
    print(f"Coverage requirements: {len(coverage_requirements)}")
    print(f"Swap requests: {len(swap_requests)}")
    print(f"Swap history events: {len(swap_events)}")
    print(f"Holiday entries: {len(holiday_calendar)}")
    print(f"Labelled anomalies: {len(anomalies)}")
    print(f"Files saved in: {DATA_DIR}")


if __name__ == "__main__":
    main()
