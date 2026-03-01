"""
Tests for plan 05-02 Task 2: GET /api/canvas/assignment-groups/{course_id} endpoint.

RED phase: Verifies that:
  - database.py has get_assignment_groups() query function
  - main.py has the /api/canvas/assignment-groups/{course_id} endpoint route
  - The endpoint returns {"groups": [...], "count": N}
  - The endpoint calls db.get_assignment_groups()
"""

import ast


def test_database_has_get_assignment_groups():
    """Verify get_assignment_groups function exists in database.py."""
    with open("database.py") as f:
        src = f.read()
    assert "def get_assignment_groups" in src, (
        "get_assignment_groups() function missing from database.py"
    )


def test_database_get_assignment_groups_queries_correct_table():
    """Verify get_assignment_groups queries assignment_groups table."""
    with open("database.py") as f:
        src = f.read()
    assert "assignment_groups" in src, (
        "assignment_groups table reference missing from database.py"
    )


def test_database_get_assignment_groups_orders_by_position():
    """Verify the query orders by position ASC."""
    with open("database.py") as f:
        src = f.read()
    # Check the function exists and uses ORDER BY
    assert "ORDER BY" in src or "order by" in src.lower(), (
        "get_assignment_groups should ORDER BY position"
    )


def test_main_has_assignment_groups_route():
    """Verify the /api/canvas/assignment-groups route exists in main.py."""
    with open("main.py") as f:
        src = f.read()
    assert "/api/canvas/assignment-groups" in src, (
        "Route /api/canvas/assignment-groups missing from main.py"
    )


def test_main_calls_db_get_assignment_groups():
    """Verify main.py calls db.get_assignment_groups()."""
    with open("main.py") as f:
        src = f.read()
    assert "get_assignment_groups" in src, (
        "db.get_assignment_groups() call missing from main.py"
    )


def test_endpoint_returns_groups_and_count():
    """Verify the endpoint returns dict with 'groups' and 'count' keys."""
    with open("main.py") as f:
        src = f.read()
    # Both "groups" and "count" should appear in the endpoint response
    assert '"groups"' in src or "'groups'" in src, (
        "Response should include 'groups' key"
    )
    assert '"count"' in src or "'count'" in src, "Response should include 'count' key"


def test_endpoint_has_try_except():
    """Verify the endpoint has try/except error handling with HTTPException 500."""
    with open("main.py") as f:
        src = f.read()
    assert "HTTP_500_INTERNAL_SERVER_ERROR" in src, (
        "Endpoint should raise HTTP 500 on database errors"
    )


def test_ast_endpoint_function_exists():
    """Verify the endpoint async function is defined in main.py via AST."""
    with open("main.py") as f:
        src = f.read()

    tree = ast.parse(src)

    # Find any async function containing 'assignment_groups' in its name
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and "assignment_group" in node.name:
            found = True
            break

    assert found, (
        "No async function with 'assignment_group' in name found in main.py; "
        "expected e.g. get_assignment_groups_endpoint()"
    )
