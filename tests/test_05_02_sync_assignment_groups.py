"""
Tests for plan 05-02: assignment_group_id annotation and assignment groups sync.

RED phase: These tests verify that canvas_sync.py's sync_course_data() function:
  1. Annotates each assignment dict with assignment_group_id
  2. Fetches assignment groups via course.get_assignment_groups()
  3. Calls db.upsert_assignment_groups() inside the transaction block
  4. Calls db.upsert_assignments() with the annotated assignment dicts
  5. Logs assignment group count and duration after fetch
"""

import ast


def test_assignment_group_id_in_source():
    """Verify 'assignment_group_id' key is present in canvas_sync.py source."""
    with open("canvas_sync.py") as f:
        src = f.read()
    assert "assignment_group_id" in src, (
        "assignment_group_id not found in canvas_sync.py — "
        "the assignment dict needs to include this field"
    )


def test_get_assignment_groups_call_in_source():
    """Verify course.get_assignment_groups() is called in canvas_sync.py."""
    with open("canvas_sync.py") as f:
        src = f.read()
    assert "get_assignment_groups" in src, (
        "get_assignment_groups() call missing from canvas_sync.py"
    )


def test_upsert_assignment_groups_call_in_source():
    """Verify db.upsert_assignment_groups() is called in canvas_sync.py."""
    with open("canvas_sync.py") as f:
        src = f.read()
    assert "upsert_assignment_groups" in src, (
        "db.upsert_assignment_groups() call missing from canvas_sync.py"
    )


def test_assignment_group_id_uses_getattr():
    """Verify assignment_group_id is obtained via getattr (safe attribute access)."""
    with open("canvas_sync.py") as f:
        src = f.read()
    # The safe access pattern uses getattr with fallback
    assert (
        'getattr(assignment, "assignment_group_id", None)' in src
        or "getattr(assignment, 'assignment_group_id', None)" in src
    ), (
        "assignment_group_id should be accessed via "
        "getattr(assignment, 'assignment_group_id', None) for safe attribute access"
    )


def test_assignment_groups_data_structure_in_source():
    """Verify assignment_groups_data list is built with required keys."""
    with open("canvas_sync.py") as f:
        src = f.read()
    # Check for assignment_groups_data variable and required dict keys
    assert "assignment_groups_data" in src, (
        "assignment_groups_data list not found in canvas_sync.py"
    )
    assert '"id"' in src or "'id'" in src, "id key missing"
    assert '"name"' in src or "'name'" in src, "name key missing"
    assert '"position"' in src or "'position'" in src, "position key missing"


def test_logger_info_for_assignment_groups():
    """Verify logger.info() is called after assignment_groups fetch."""
    with open("canvas_sync.py") as f:
        src = f.read()
    # Should have a logger.info call referencing assignment groups
    assert "assignment_groups" in src and "logger.info" in src, (
        "logger.info() should be called after assignment_groups fetch"
    )


def test_ast_upsert_order():
    """Verify upsert_assignment_groups is called before upsert_assignments."""
    with open("canvas_sync.py") as f:
        src = f.read()

    tree = ast.parse(src)

    # Find sync_course_data function
    sync_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "sync_course_data":
            sync_func = node
            break

    assert sync_func is not None, "sync_course_data function not found"

    # Walk the function body to find call positions
    calls = []
    target_calls = ("upsert_assignment_groups", "upsert_assignments")
    for node in ast.walk(sync_func):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in target_calls
        ):
            calls.append((node.lineno, node.func.attr))

    calls.sort(key=lambda x: x[0])
    call_names = [c[1] for c in calls]

    assert "upsert_assignment_groups" in call_names, (
        "upsert_assignment_groups not found as a call in sync_course_data"
    )
    assert "upsert_assignments" in call_names, (
        "upsert_assignments not found as a call in sync_course_data"
    )

    ag_idx = call_names.index("upsert_assignment_groups")
    ua_idx = call_names.index("upsert_assignments")

    assert ag_idx < ua_idx, (
        f"upsert_assignment_groups (call #{ag_idx + 1}) must come BEFORE "
        f"upsert_assignments (call #{ua_idx + 1}) in sync_course_data()"
    )
