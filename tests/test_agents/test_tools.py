"""Tests for the built-in tools: Workspace isolation and each tool function."""

from pathlib import Path

import pytest

from a2a_mesh.agents.tools import (
    BUILTIN_TOOL_SCHEMAS,
    Workspace,
    execute_builtin_tool,
    file_read,
    file_write,
    git_diff,
    run_tests,
)


@pytest.fixture()
def workspace(tmp_path: Path) -> Workspace:
    return Workspace(tmp_path)


# ── Workspace ────────────────────────────────────────────────────────────────

def test_workspace_resolve_stays_inside_root(workspace: Workspace) -> None:
    resolved = workspace.resolve("sub/file.txt")
    assert resolved == workspace.root / "sub" / "file.txt"


def test_workspace_resolve_rejects_parent_escape(workspace: Workspace) -> None:
    with pytest.raises(ValueError, match="escapes the workspace"):
        workspace.resolve("../outside.txt")


def test_workspace_resolve_rejects_absolute_escape(workspace: Workspace) -> None:
    with pytest.raises(ValueError, match="escapes the workspace"):
        workspace.resolve("/etc/passwd")


# ── file_read / file_write ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_file_write_then_file_read_round_trip(workspace: Workspace) -> None:
    write_result = await file_write(workspace, {"path": "app.py", "content": "print('hi')"})
    assert "app.py" in write_result

    read_result = await file_read(workspace, {"path": "app.py"})
    assert read_result == "print('hi')"


@pytest.mark.asyncio
async def test_file_write_creates_parent_dirs(workspace: Workspace) -> None:
    await file_write(workspace, {"path": "nested/dir/file.txt", "content": "x"})
    assert (workspace.root / "nested" / "dir" / "file.txt").read_text() == "x"


@pytest.mark.asyncio
async def test_file_read_missing_file_returns_error_string(workspace: Workspace) -> None:
    result = await file_read(workspace, {"path": "missing.txt"})
    assert result.startswith("Error:")


# ── run_tests ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_tests_reports_passing_test(workspace: Workspace) -> None:
    await file_write(
        workspace,
        {"path": "test_sample.py", "content": "def test_ok():\n    assert 1 + 1 == 2\n"},
    )
    result = await run_tests(workspace, {})
    assert "1 passed" in result


@pytest.mark.asyncio
async def test_run_tests_reports_failing_test(workspace: Workspace) -> None:
    await file_write(
        workspace,
        {"path": "test_sample.py", "content": "def test_bad():\n    assert 1 == 2\n"},
    )
    result = await run_tests(workspace, {})
    assert "1 failed" in result


# ── git_diff ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_git_diff_no_repo_returns_output(workspace: Workspace) -> None:
    result = await git_diff(workspace, {})
    assert isinstance(result, str)
    assert result != ""


# ── execute_builtin_tool dispatcher ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_builtin_tool_unknown_name(workspace: Workspace) -> None:
    result = await execute_builtin_tool(workspace, "not_a_tool", {})
    assert result == "Error: unknown tool 'not_a_tool'"


@pytest.mark.asyncio
async def test_execute_builtin_tool_missing_argument(workspace: Workspace) -> None:
    result = await execute_builtin_tool(workspace, "file_read", {})
    assert result.startswith("Error: missing required argument")


@pytest.mark.asyncio
async def test_execute_builtin_tool_path_escape_returns_error(workspace: Workspace) -> None:
    result = await execute_builtin_tool(workspace, "file_read", {"path": "../escape.txt"})
    assert result.startswith("Error:")
    assert "escapes" in result


def test_all_builtin_tools_have_schemas() -> None:
    from a2a_mesh.agents.tools import BUILTIN_TOOLS

    assert set(BUILTIN_TOOLS) == set(BUILTIN_TOOL_SCHEMAS)
