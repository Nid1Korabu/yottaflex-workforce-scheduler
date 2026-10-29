import json
from datetime import timedelta
from pathlib import Path

import pandas as pd


# ==================================================
# 1. CONFIGURATION
# ==================================================

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

checks = []


# ==================================================
# 2. HELPER FUNCTIONS
# ==================================================

def add_check(name, passed, details):
    """Record and display one validation result."""
    passed = bool(passed)
    status = "PASS" if passed else "FAIL"

    print(f"[{status}] {name}: {details}")

    checks.append({
        "check": name,
        "passed": passed,
        "details": str(details),
    })


def load_csv(filename):
    """Load a CSV file from the data folder."""
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Missing file: {path}"
        )

    return pd.read_csv(path)


def references_are_valid(frame, column, valid_values):
    """Check that every foreign key points to an existing record."""
    if frame.empty:
        return True

    return (
        frame[column].notna().all()
        and frame[column].isin(valid_values).all()
    )


def is_true(value):
    """Safely interpret Boolean values loaded from CSV."""
    return str(value).strip().lower() in {
        "true", "1", "yes"
    }


def as_date(value):
    """Convert a value into a Python date, or return None."""
    parsed = pd.to_datetime(value, errors="coerce")

    if pd.isna(parsed):
        return None

    return parsed.date()


# ==================================================
# 3. LOAD ALL GENERATED TABLES
# ==================================================

print("=" * 60)
print("WORKFORCE DATA VALIDATION")
print("=" * 60)

teams = load_csv("teams.csv")
employees = load_csv("employees.csv")
skills = load_csv("skills.csv")
employee_skills = load_csv("employee_skills.csv")
shift_templates = load_csv("shift_templates.csv")
assignments = load_csv("shift_assignments.csv")
leave_requests = load_csv("leave_requests.csv")
holiday_calendar = load_csv("holiday_calendar.csv")
attendance = load_csv("attendance_events.csv")
coverage_requirements = load_csv("coverage_requirements.csv")
swaps = load_csv("swap_requests.csv")
swap_events = load_csv("swap_events.csv")
ground_truth = load_csv("anomaly_ground_truth.csv")


# ==================================================
# 4. REQUIRED COLUMNS
# ==================================================

required_columns = {
    "teams": (
        teams,
        ["team_id", "team_name"],
    ),
    "employees": (
        employees,
        [
            "employee_id", "employee_name", "team_id",
            "weekly_hours_cap", "active",
        ],
    ),
    "skills": (
        skills,
        ["skill_id", "skill_name"],
    ),
    "employee_skills": (
        employee_skills,
        ["employee_id", "skill_name"],
    ),
    "shift_templates": (
        shift_templates,
        [
            "shift_template_id", "shift_name",
            "start_time", "duration_hours",
        ],
    ),
    "shift_assignments": (
        assignments,
        [
            "assignment_id", "employee_id", "team_id",
            "shift_template_id", "shift_date", "shift_name",
            "start_hour", "duration_hours",
            "shift_start", "shift_end", "status",
        ],
    ),
    "leave_requests": (
        leave_requests,
        [
            "leave_id", "employee_id", "start_date",
            "end_date", "leave_type", "status",
        ],
    ),
    "holiday_calendar": (
        holiday_calendar,
        [
            "holiday_id", "holiday_date",
            "holiday_name", "region", "source_type",
        ],
    ),
    "attendance_events": (
        attendance,
        [
            "attendance_id", "employee_id",
            "assignment_id", "event_type",
            "event_timestamp",
        ],
    ),
    "coverage_requirements": (
        coverage_requirements,
        [
            "coverage_id", "team_id", "shift_name",
            "required_employees", "required_skill",
        ],
    ),
    "swap_requests": (
        swaps,
        [
            "swap_id", "requesting_employee_id",
            "target_employee_id", "status",
            "manager_approved", "applied",
        ],
    ),
    "swap_events": (
        swap_events,
        [
            "swap_event_id", "swap_id",
            "event_type", "event_timestamp",
            "actor", "details",
        ],
    ),
    "anomaly_ground_truth": (
        ground_truth,
        [
            "anomaly_id", "anomaly_type",
            "description", "record_id",
            "related_id", "expected_skill",
        ],
    ),
}

missing_columns = []

for table_name, (frame, columns) in required_columns.items():
    missing = [
        column for column in columns
        if column not in frame.columns
    ]

    if missing:
        missing_columns.append(
            f"{table_name}: {', '.join(missing)}"
        )

add_check(
    "Required table columns",
    len(missing_columns) == 0,
    (
        "All required columns exist"
        if not missing_columns
        else "; ".join(missing_columns)
    ),
)

if missing_columns:
    raise ValueError(
        "Some required columns are missing. "
        "Fix the generator or CSV schema before continuing."
    )


# ==================================================
# 5. PRIMARY KEY AND DUPLICATE CHECKS
# ==================================================

primary_keys = [
    ("Team IDs", teams, ["team_id"]),
    ("Employee IDs", employees, ["employee_id"]),
    ("Skill IDs", skills, ["skill_id"]),
    (
        "Shift template IDs",
        shift_templates,
        ["shift_template_id"],
    ),
    (
        "Assignment IDs",
        assignments,
        ["assignment_id"],
    ),
    ("Leave IDs", leave_requests, ["leave_id"]),
    (
        "Holiday IDs",
        holiday_calendar,
        ["holiday_id"],
    ),
    (
        "Attendance IDs",
        attendance,
        ["attendance_id"],
    ),
    (
        "Coverage IDs",
        coverage_requirements,
        ["coverage_id"],
    ),
    ("Swap IDs", swaps, ["swap_id"]),
    (
        "Swap event IDs",
        swap_events,
        ["swap_event_id"],
    ),
    (
        "Anomaly IDs",
        ground_truth,
        ["anomaly_id"],
    ),
]

for name, frame, columns in primary_keys:
    duplicate_count = int(
        frame.duplicated(subset=columns).sum()
    )

    add_check(
        f"Unique {name}",
        duplicate_count == 0,
        (
            f"{len(frame) - duplicate_count} unique records; "
            f"{duplicate_count} duplicates"
        ),
    )


duplicate_employee_skills = int(
    employee_skills.duplicated(
        subset=["employee_id", "skill_name"]
    ).sum()
)

add_check(
    "Unique employee-skill pairs",
    duplicate_employee_skills == 0,
    f"{duplicate_employee_skills} duplicate pairs",
)


# ==================================================
# 6. FOREIGN KEY CHECKS
# ==================================================

team_ids = set(teams["team_id"].dropna())
employee_ids = set(employees["employee_id"].dropna())
skill_names = set(skills["skill_name"].dropna())
template_ids = set(
    shift_templates["shift_template_id"].dropna()
)
assignment_ids = set(assignments["assignment_id"].dropna())
swap_ids = set(swaps["swap_id"].dropna())

foreign_key_checks = [
    (
        "Employee team references",
        employees,
        "team_id",
        team_ids,
    ),
    (
        "Assignment employee references",
        assignments,
        "employee_id",
        employee_ids,
    ),
    (
        "Assignment team references",
        assignments,
        "team_id",
        team_ids,
    ),
    (
        "Assignment template references",
        assignments,
        "shift_template_id",
        template_ids,
    ),
    (
        "Employee-skill employee references",
        employee_skills,
        "employee_id",
        employee_ids,
    ),
    (
        "Employee-skill skill references",
        employee_skills,
        "skill_name",
        skill_names,
    ),
    (
        "Leave employee references",
        leave_requests,
        "employee_id",
        employee_ids,
    ),
    (
        "Attendance employee references",
        attendance,
        "employee_id",
        employee_ids,
    ),
    (
        "Attendance assignment references",
        attendance,
        "assignment_id",
        assignment_ids,
    ),
    (
        "Coverage team references",
        coverage_requirements,
        "team_id",
        team_ids,
    ),
    (
        "Coverage skill references",
        coverage_requirements,
        "required_skill",
        skill_names,
    ),
    (
        "Swap requester references",
        swaps,
        "requesting_employee_id",
        employee_ids,
    ),
    (
        "Swap target references",
        swaps,
        "target_employee_id",
        employee_ids,
    ),
    (
        "Swap event references",
        swap_events,
        "swap_id",
        swap_ids,
    ),
]

for name, frame, column, valid_values in foreign_key_checks:
    invalid_count = int(
        (
            frame[column].isna()
            | ~frame[column].isin(valid_values)
        ).sum()
    )

    add_check(
        name,
        invalid_count == 0,
        (
            "All references are valid"
            if invalid_count == 0
            else f"{invalid_count} invalid references"
        ),
    )


# Verify that the assignment team matches the employee's team.
employee_team_map = dict(zip(
    employees["employee_id"],
    employees["team_id"],
))

team_mismatches = assignments[
    assignments.apply(
        lambda row: employee_team_map.get(
            row["employee_id"]
        ) != row["team_id"],
        axis=1,
    )
]

add_check(
    "Employee and assignment team consistency",
    team_mismatches.empty,
    f"{len(team_mismatches)} mismatched assignments",
)


# ==================================================
# 7. DATE AND SHIFT VALIDATION
# ==================================================

assignment_dates = pd.to_datetime(
    assignments["shift_date"],
    errors="coerce",
)

shift_starts = pd.to_datetime(
    assignments["shift_start"],
    errors="coerce",
)

shift_ends = pd.to_datetime(
    assignments["shift_end"],
    errors="coerce",
)

shift_hours = pd.to_numeric(
    assignments["duration_hours"],
    errors="coerce",
)

invalid_assignment_dates = int(
    (
        assignment_dates.isna()
        | shift_starts.isna()
        | shift_ends.isna()
    ).sum()
)

add_check(
    "Valid assignment dates and timestamps",
    invalid_assignment_dates == 0,
    f"{invalid_assignment_dates} invalid records",
)

date_mismatches = 0
duration_mismatches = 0

for index in assignments.index:
    start = shift_starts.loc[index]
    end = shift_ends.loc[index]
    shift_day = assignment_dates.loc[index]
    hours = shift_hours.loc[index]

    if pd.isna(start) or pd.isna(end) or pd.isna(shift_day):
        continue

    if start.date() != shift_day.date():
        date_mismatches += 1

    if pd.isna(hours) or end <= start:
        duration_mismatches += 1
    elif abs((end - start).total_seconds() / 3600 - hours) > 0.001:
        duration_mismatches += 1

add_check(
    "Assignment dates match shift start",
    date_mismatches == 0,
    f"{date_mismatches} mismatches",
)

add_check(
    "Shift duration matches timestamps",
    duration_mismatches == 0,
    f"{duration_mismatches} mismatches",
)

leave_starts = pd.to_datetime(
    leave_requests["start_date"],
    errors="coerce",
)

leave_ends = pd.to_datetime(
    leave_requests["end_date"],
    errors="coerce",
)

invalid_leave_ranges = int(
    (
        leave_starts.isna()
        | leave_ends.isna()
        | (leave_ends < leave_starts)
    ).sum()
)

add_check(
    "Valid leave date ranges",
    invalid_leave_ranges == 0,
    f"{invalid_leave_ranges} invalid ranges",
)

holiday_dates = pd.to_datetime(
    holiday_calendar["holiday_date"],
    errors="coerce",
)

add_check(
    "Valid holiday dates",
    not holiday_dates.isna().any(),
    f"{int(holiday_dates.isna().sum())} invalid dates",
)

# Confirm that template names and shift durations are consistent.
template_by_id = shift_templates.set_index(
    "shift_template_id"
).to_dict("index")

template_mismatches = 0

for _, assignment in assignments.iterrows():
    template = template_by_id.get(
        assignment["shift_template_id"]
    )

    if template is None:
        continue

    if (
        template["shift_name"] != assignment["shift_name"]
        or float(template["duration_hours"])
        != float(assignment["duration_hours"])
    ):
        template_mismatches += 1

add_check(
    "Assignment and template consistency",
    template_mismatches == 0,
    f"{template_mismatches} mismatches",
)


# ==================================================
# 8. BUILD EMPLOYEE SKILL LOOKUP
# ==================================================

employee_skill_lookup = {}

for _, row in employee_skills.iterrows():
    employee_skill_lookup.setdefault(
        row["employee_id"], set()
    ).add(row["skill_name"])

requirement_lookup = {
    (row["team_id"], row["shift_name"]): row
    for _, row in coverage_requirements.iterrows()
}


# ==================================================
# 9. DETECT ACTUAL SHIFT OVERLAPS
# ==================================================

overlap_pairs = []

valid_assignments = assignments[
    shift_starts.notna() & shift_ends.notna()
].copy()

valid_assignments["_start"] = shift_starts.loc[
    valid_assignments.index
]
valid_assignments["_end"] = shift_ends.loc[
    valid_assignments.index
]

for employee_id, group in valid_assignments.groupby("employee_id"):
    group = group.sort_values("_start")
    records = list(group.to_dict("records"))

    for i, first in enumerate(records):
        for second in records[i + 1:]:
            # Sorted by start time, so later records cannot overlap
            # the first one once their start is at/after its end.
            if second["_start"] >= first["_end"]:
                break

            if (
                first["_start"] < second["_end"]
                and second["_start"] < first["_end"]
            ):
                overlap_pairs.append({
                    "employee_id": employee_id,
                    "assignment_id_1": first["assignment_id"],
                    "assignment_id_2": second["assignment_id"],
                })

add_check(
    "Overlapping assignments detected",
    len(overlap_pairs) > 0,
    f"{len(overlap_pairs)} actual overlapping assignment pairs",
)

# Verify the specific labelled double-booking, not just any overlap.
double_booking_label = ground_truth[
    ground_truth["anomaly_id"] == "ANOM-001"
]

labelled_double_booking_found = False

if not double_booking_label.empty:
    label = double_booking_label.iloc[0]
    target_id = label["record_id"]
    related_id = label["related_id"]

    labelled_double_booking_found = any(
        {
            pair["assignment_id_1"],
            pair["assignment_id_2"],
        } == {target_id, related_id}
        for pair in overlap_pairs
    )

add_check(
    "Labelled double-booking verified",
    labelled_double_booking_found,
    (
        "The labelled assignment overlaps its related assignment"
        if labelled_double_booking_found
        else "Could not verify the labelled assignment pair"
    ),
)


# ==================================================
# 10. APPROVED LEAVE OVERLAPS
# ==================================================

approved_leaves = leave_requests[
    leave_requests["status"] == "APPROVED"
]

leave_overlap_pairs = []

for _, leave in approved_leaves.iterrows():
    start_day = as_date(leave["start_date"])
    end_day = as_date(leave["end_date"])

    if start_day is None or end_day is None:
        continue

    matching_assignments = assignments[
        (assignments["employee_id"] == leave["employee_id"])
        & (assignment_dates.dt.date >= start_day)
        & (assignment_dates.dt.date <= end_day)
    ]

    for _, assignment in matching_assignments.iterrows():
        leave_overlap_pairs.append({
            "leave_id": leave["leave_id"],
            "assignment_id": assignment["assignment_id"],
            "employee_id": leave["employee_id"],
        })

add_check(
    "Approved leave overlaps detected",
    len(leave_overlap_pairs) > 0,
    f"{len(leave_overlap_pairs)} leave/assignment pairs",
)

leave_label = ground_truth[
    ground_truth["anomaly_id"] == "ANOM-002"
]

labelled_leave_overlap_found = False

if not leave_label.empty:
    label = leave_label.iloc[0]

    labelled_leave_overlap_found = any(
        pair["leave_id"] == label["record_id"]
        and pair["assignment_id"] == label["related_id"]
        for pair in leave_overlap_pairs
    )

add_check(
    "Labelled leave overlap verified",
    labelled_leave_overlap_found,
    (
        "The labelled approved leave overlaps its assignment"
        if labelled_leave_overlap_found
        else "Could not verify the labelled leave overlap"
    ),
)


# ==================================================
# 11. REQUIRED SKILL VALIDATION
# ==================================================

missing_skill_assignments = []

for _, assignment in assignments.iterrows():
    key = (
        assignment["team_id"],
        assignment["shift_name"],
    )
    requirement = requirement_lookup.get(key)

    if requirement is None:
        continue

    employee_id = assignment["employee_id"]
    required_skill = requirement["required_skill"]

    if required_skill not in employee_skill_lookup.get(
        employee_id, set()
    ):
        missing_skill_assignments.append({
            "assignment_id": assignment["assignment_id"],
            "employee_id": employee_id,
            "team_id": assignment["team_id"],
            "shift_name": assignment["shift_name"],
            "required_skill": required_skill,
        })

missing_skill_label = ground_truth[
    ground_truth["anomaly_id"] == "ANOM-003"
]

labelled_missing_skill_found = False

if not missing_skill_label.empty:
    label = missing_skill_label.iloc[0]
    target_assignment = assignments[
        assignments["assignment_id"] == label["record_id"]
    ]

    if not target_assignment.empty:
        assignment = target_assignment.iloc[0]

        requirement = requirement_lookup.get((
            assignment["team_id"],
            assignment["shift_name"],
        ))

        expected_skill = label["expected_skill"]

        labelled_missing_skill_found = (
            requirement is not None
            and requirement["required_skill"] == expected_skill
            and expected_skill not in employee_skill_lookup.get(
                assignment["employee_id"], set()
            )
        )

add_check(
    "Labelled missing-skill anomaly verified",
    labelled_missing_skill_found,
    (
        "The assigned employee lacks the specific required skill"
        if labelled_missing_skill_found
        else "The labelled assignment does not verify against its requirement"
    ),
)



# ==================================================
# 12. COVERAGE ANALYSIS
# ==================================================

coverage_rows = []
staffing_shortages = 0
skill_shortages = 0

if not assignments.empty and not assignment_dates.isna().all():
    first_day = assignment_dates.min().date()
    last_day = assignment_dates.max().date()

    schedule_dates = pd.date_range(
        start=first_day,
        end=last_day,
        freq="D",
    )

    # Convert each assignment date once.
    # Group assignments once instead of filtering the full table
    # for every team, shift, and date combination.
    coverage_assignments = assignments[
        ["team_id", "shift_name", "employee_id"]
    ].copy()

    coverage_assignments["_date"] = (
        assignment_dates.dt.strftime("%Y-%m-%d")
    )

    grouped_assignments = (
        coverage_assignments
        .groupby(
            ["team_id", "shift_name", "_date"],
            sort=False,
        )["employee_id"]
        .agg(set)
        .to_dict()
    )

    for requirement in coverage_requirements.itertuples(index=False):
        team_id = requirement.team_id
        shift_name = requirement.shift_name
        required_count = int(requirement.required_employees)
        required_skill = requirement.required_skill

        for day in schedule_dates:
            day_text = day.strftime("%Y-%m-%d")

            employee_ids_on_shift = grouped_assignments.get(
                (team_id, shift_name, day_text),
                set(),
            )

            skilled_employee_ids = {
                employee_id
                for employee_id in employee_ids_on_shift
                if required_skill
                in employee_skill_lookup.get(employee_id, set())
            }

            staffing_count = len(employee_ids_on_shift)
            skilled_count = len(skilled_employee_ids)

            staffing_gap = max(
                0, required_count - staffing_count
            )
            skill_gap = max(
                0, required_count - skilled_count
            )

            coverage_rows.append({
                "team_id": team_id,
                "shift_name": shift_name,
                "shift_date": day_text,
                "required_employees": required_count,
                "required_skill": required_skill,
                "assigned_employees": staffing_count,
                "qualified_employees": skilled_count,
                "staffing_gap": staffing_gap,
                "skill_gap": skill_gap,
                "staffing_met": staffing_count >= required_count,
                "skill_requirement_met": (
                    skilled_count >= required_count
                ),
            })

coverage_analysis = pd.DataFrame(coverage_rows)

coverage_analysis.to_csv(
    DATA_DIR / "coverage_analysis.csv",
    index=False,
)

if not coverage_analysis.empty:
    staffing_shortages = int(
        (~coverage_analysis["staffing_met"]).sum()
    )
    skill_shortages = int(
        (~coverage_analysis["skill_requirement_met"]).sum()
    )

add_check(
    "Coverage analysis generated",
    not coverage_analysis.empty,
    (
        f"{len(coverage_analysis)} team/shift/date combinations; "
        f"{staffing_shortages} staffing gaps; "
        f"{skill_shortages} skill gaps"
    ),
)


print("\nCOVERAGE ANALYSIS")
print(
    "Team/shift/date combinations checked:",
    len(coverage_analysis),
)
print("Combinations with staffing shortages:", staffing_shortages)
print("Combinations with skill shortages:", skill_shortages)
print("Detailed results saved to data/coverage_analysis.csv")


# ==================================================
# 13. WEEKLY OVERTIME VALIDATION
# ==================================================

assignments_for_hours = assignments.copy()

assignments_for_hours["_start"] = shift_starts
assignments_for_hours["_hours"] = pd.to_numeric(
    assignments_for_hours["duration_hours"],
    errors="coerce",
)

assignments_for_hours["_week_start"] = (
    assignments_for_hours["_start"].dt.normalize()
    - pd.to_timedelta(
        assignments_for_hours["_start"].dt.weekday,
        unit="D",
    )
)

weekly_hours = (
    assignments_for_hours
    .groupby(["employee_id", "_week_start"], dropna=True)["_hours"]
    .sum()
    .reset_index(name="scheduled_hours")
)

weekly_caps = dict(zip(
    employees["employee_id"],
    pd.to_numeric(
        employees["weekly_hours_cap"],
        errors="coerce",
    ),
))

weekly_hours["weekly_cap"] = weekly_hours[
    "employee_id"
].map(weekly_caps)

weekly_hours["over_cap"] = (
    weekly_hours["scheduled_hours"]
    > weekly_hours["weekly_cap"]
)

overtime_rows = weekly_hours[
    weekly_hours["over_cap"]
]

add_check(
    "Weekly overtime detected",
    not overtime_rows.empty,
    f"{len(overtime_rows)} employee-week records exceed their caps",
)

overtime_label = ground_truth[
    ground_truth["anomaly_id"] == "ANOM-004"
]

labelled_overtime_found = False

if not overtime_label.empty:
    overtime_employee_id = overtime_label.iloc[0]["record_id"]

    labelled_overtime_found = not overtime_rows[
        overtime_rows["employee_id"] == overtime_employee_id
    ].empty

add_check(
    "Labelled overtime anomaly verified",
    labelled_overtime_found,
    (
        "The labelled employee exceeds their weekly hours cap"
        if labelled_overtime_found
        else "The labelled employee does not exceed the weekly cap"
    ),
)


# ==================================================
# 14. ATTENDANCE RECONCILIATION
# ==================================================

valid_event_types = {"CLOCK_IN", "CLOCK_OUT"}

invalid_event_types = int(
    (~attendance["event_type"].isin(valid_event_types)).sum()
)

add_check(
    "Valid attendance event types",
    invalid_event_types == 0,
    f"{invalid_event_types} invalid event types",
)

attendance_lookup = {}

for _, event in attendance.iterrows():
    key = (
        event["assignment_id"],
        event["event_type"],
    )

    attendance_lookup.setdefault(key, []).append(event)

attendance_errors = []

for _, assignment in assignments.iterrows():
    assignment_id = assignment["assignment_id"]

    for event_type, expected_timestamp in [
        ("CLOCK_IN", assignment["shift_start"]),
        ("CLOCK_OUT", assignment["shift_end"]),
    ]:
        matching_events = attendance_lookup.get(
            (assignment_id, event_type), []
        )

        if len(matching_events) != 1:
            attendance_errors.append(
                f"{assignment_id}: expected exactly one {event_type}"
            )
            continue

        event = matching_events[0]

        if event["employee_id"] != assignment["employee_id"]:
            attendance_errors.append(
                f"{assignment_id}: employee mismatch for {event_type}"
            )

        event_timestamp = pd.to_datetime(
            event["event_timestamp"], errors="coerce"
        )
        expected = pd.to_datetime(
            expected_timestamp, errors="coerce"
        )

        if (
            pd.isna(event_timestamp)
            or pd.isna(expected)
            or event_timestamp != expected
        ):
            attendance_errors.append(
                f"{assignment_id}: timestamp mismatch for {event_type}"
            )

add_check(
    "Attendance reconciles with assignments",
    len(attendance_errors) == 0,
    (
        "Every assignment has matching clock-in and clock-out events"
        if not attendance_errors
        else f"{len(attendance_errors)} attendance errors"
    ),
)


# ==================================================
# 15. STATUS AND LIFECYCLE VALIDATION
# ==================================================

valid_leave_statuses = {
    "PENDING", "APPROVED", "REJECTED"
}

invalid_leave_statuses = int(
    (~leave_requests["status"].isin(valid_leave_statuses)).sum()
)

add_check(
    "Valid leave statuses",
    invalid_leave_statuses == 0,
    f"{invalid_leave_statuses} invalid statuses",
)

valid_swap_statuses = {
    "PENDING", "APPROVED", "REJECTED"
}

invalid_swap_statuses = int(
    (~swaps["status"].isin(valid_swap_statuses)).sum()
)

add_check(
    "Valid swap statuses",
    invalid_swap_statuses == 0,
    f"{invalid_swap_statuses} invalid statuses",
)

valid_assignment_statuses = {
    "ASSIGNED", "CANCELLED", "COMPLETED"
}

invalid_assignment_statuses = int(
    (~assignments["status"].isin(valid_assignment_statuses)).sum()
)

add_check(
    "Valid assignment statuses",
    invalid_assignment_statuses == 0,
    f"{invalid_assignment_statuses} invalid statuses",
)

valid_swap_event_types = {
    "REQUESTED",
    "MANAGER_APPROVED",
    "MANAGER_REJECTED",
    "APPLIED",
}

invalid_swap_event_types = int(
    (~swap_events["event_type"].isin(valid_swap_event_types)).sum()
)

add_check(
    "Valid swap history event types",
    invalid_swap_event_types == 0,
    f"{invalid_swap_event_types} invalid event types",
)

events_by_swap = {}

for _, event in swap_events.iterrows():
    events_by_swap.setdefault(event["swap_id"], set()).add(
        event["event_type"]
    )

lifecycle_errors = []

for _, swap in swaps.iterrows():
    swap_id = swap["swap_id"]
    event_types = events_by_swap.get(swap_id, set())

    if "REQUESTED" not in event_types:
        lifecycle_errors.append(
            f"{swap_id}: missing REQUESTED event"
        )

    if (
        swap["status"] == "APPROVED"
        and "MANAGER_APPROVED" not in event_types
    ):
        lifecycle_errors.append(
            f"{swap_id}: approved without approval event"
        )

    if (
        swap["status"] == "REJECTED"
        and "MANAGER_REJECTED" not in event_types
    ):
        lifecycle_errors.append(
            f"{swap_id}: rejected without rejection event"
        )

    if is_true(swap["applied"]) and "APPLIED" not in event_types:
        lifecycle_errors.append(
            f"{swap_id}: applied without an APPLIED event"
        )

add_check(
    "Swap lifecycle history",
    len(lifecycle_errors) == 0,
    (
        "Required lifecycle events are present"
        if not lifecycle_errors
        else f"{len(lifecycle_errors)} lifecycle errors"
    ),
)


# ==================================================
# 16. VERIFY UNAPPROVED SWAP ANOMALY
# ==================================================

swap_label = ground_truth[
    ground_truth["anomaly_id"] == "ANOM-005"
]

labelled_unapproved_swap_found = False

if not swap_label.empty:
    swap_id = swap_label.iloc[0]["record_id"]

    matching_swaps = swaps[
        swaps["swap_id"] == swap_id
    ]

    if not matching_swaps.empty:
        swap = matching_swaps.iloc[0]
        event_types = events_by_swap.get(swap_id, set())

        labelled_unapproved_swap_found = (
            swap["status"] == "PENDING"
            and not is_true(swap["manager_approved"])
            and is_true(swap["applied"])
            and "APPLIED" in event_types
            and "MANAGER_APPROVED" not in event_types
        )

add_check(
    "Labelled unapproved swap verified",
    labelled_unapproved_swap_found,
    (
        "Swap was applied without manager approval"
        if labelled_unapproved_swap_found
        else "Could not verify the labelled swap anomaly"
    ),
)


# ==================================================
# 17. VERIFY THE FIVE LABELLED ANOMALIES
# ==================================================

expected_anomaly_types = {
    "DOUBLE_BOOKING",
    "APPROVED_LEAVE_OVERLAP",
    "MISSING_REQUIRED_SKILL",
    "OVERTIME_CAP_EXCEEDED",
    "UNAPPROVED_SWAP_APPLIED",
}

actual_anomaly_types = set(
    ground_truth["anomaly_type"].dropna()
)

labels_are_valid = (
    len(ground_truth) == 5
    and ground_truth["anomaly_id"].nunique() == 5
    and actual_anomaly_types == expected_anomaly_types
)

add_check(
    "Five labelled anomaly categories",
    labels_are_valid,
    (
        f"{len(ground_truth)} labels across "
        f"{len(actual_anomaly_types)} categories"
    ),
)


# ==================================================
# 18. SAVE VALIDATION SUMMARY
# ==================================================

passed_count = sum(
    1 for check in checks if check["passed"]
)

failed_count = len(checks) - passed_count

summary = {
    "checks_passed": passed_count,
    "checks_failed": failed_count,
    "total_checks": len(checks),
    "overall_pass": failed_count == 0,
    "record_counts": {
        "teams": len(teams),
        "employees": len(employees),
        "skills": len(skills),
        "employee_skills": len(employee_skills),
        "shift_templates": len(shift_templates),
        "shift_assignments": len(assignments),
        "leave_requests": len(leave_requests),
        "holiday_calendar": len(holiday_calendar),
        "attendance_events": len(attendance),
        "coverage_requirements": len(coverage_requirements),
        "swap_requests": len(swaps),
        "swap_events": len(swap_events),
        "labelled_anomalies": len(ground_truth),
    },
    "detected_issues": {
        "overlapping_assignment_pairs": len(overlap_pairs),
        "approved_leave_overlap_pairs": len(leave_overlap_pairs),
        "missing_skill_assignments": len(missing_skill_assignments),
        "employee_weeks_over_cap": len(overtime_rows),
        "staffing_shortages": staffing_shortages,
        "skill_shortages": skill_shortages,
        "attendance_errors": len(attendance_errors),
    },
    "checks": checks,
}

summary_path = DATA_DIR / "validation_summary.json"

with open(
    summary_path,
    "w",
    encoding="utf-8",
) as file:
    json.dump(summary, file, indent=2, default=str)


# ==================================================
# 19. FINAL REPORT
# ==================================================

print("\n" + "=" * 60)
print("VALIDATION SUMMARY")
print("=" * 60)
print(f"Checks passed: {passed_count}")
print(f"Checks failed: {failed_count}")
print(f"Summary saved to: {summary_path}")
print("=" * 60)

if failed_count:
    print("Some checks need attention. Review the FAIL messages above.")
else:
    print("All validation checks passed.")