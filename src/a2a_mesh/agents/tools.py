"""Built-in tools available to any agent via the tool-calling loop.

Each tool operates on a per-task `Workspace` (a sandboxed directory) so agents can read,
write, and test files without touching anything outside their own task. `execute_builtin_tool`
never raises — failures come back as an `"Error: ..."` string so the model can see what went
wrong and react, instead of the whole task crashing.
"""

import asyncio
import logging
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TOOL_TIMEOUT_SECONDS = 30
TOOL_OUTPUT_MAX_CHARS = 4000


class Workspace:
    """A sandboxed directory a task's tools are confined to."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def resolve(self, relative_path: str) -> Path:
        """Resolve a path relative to the workspace root, rejecting any escape."""
        candidate = (self.root / relative_path).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError(f"path '{relative_path}' escapes the workspace")
        return candidate


async def file_read(workspace: Workspace, args: dict[str, Any]) -> str:
    """Read a file's contents from the workspace."""
    path = workspace.resolve(args["path"])
    if not path.is_file():
        return f"Error: '{args['path']}' does not exist"
    return path.read_text()


async def file_write(workspace: Workspace, args: dict[str, Any]) -> str:
    """Write content to a file in the workspace, creating parent directories as needed."""
    path = workspace.resolve(args["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    content = args["content"]
    path.write_text(content)
    return f"Wrote {len(content)} bytes to {args['path']}"


async def run_tests(workspace: Workspace, args: dict[str, Any]) -> str:
    """Run pytest inside the workspace and return combined stdout/stderr (tail only)."""
    target = args.get("path", ".")
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "pytest", target, "-q",
        cwd=workspace.root,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=TOOL_TIMEOUT_SECONDS)
    except TimeoutError:
        process.kill()
        return "Error: test run timed out"
    return stdout.decode(errors="replace")[-TOOL_OUTPUT_MAX_CHARS:]


async def git_diff(workspace: Workspace, args: dict[str, Any]) -> str:
    """Return `git diff` output for the workspace."""
    process = await asyncio.create_subprocess_exec(
        "git", "diff",
        cwd=workspace.root,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await process.communicate()
    return stdout.decode(errors="replace") or "(no changes)"


BUILTIN_TOOLS: dict[str, Callable[[Workspace, dict[str, Any]], Awaitable[str]]] = {
    "file_read": file_read,
    "file_write": file_write,
    "run_tests": run_tests,
    "git_diff": git_diff,
}

BUILTIN_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "file_read": {
        "type": "function",
        "function": {
            "name": "file_read",
            "description": "Read a file's contents from the task workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace root"},
                },
                "required": ["path"],
            },
        },
    },
    "file_write": {
        "type": "function",
        "function": {
            "name": "file_write",
            "description": "Write content to a file in the task workspace, creating dirs as needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace root"},
                    "content": {"type": "string", "description": "Full file content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    "run_tests": {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run pytest inside the task workspace and return the output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File or directory to test, relative to the workspace root. "
                        "Defaults to the whole workspace.",
                    },
                },
                "required": [],
            },
        },
    },
    "git_diff": {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Show the current uncommitted diff in the task workspace.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
}


async def execute_builtin_tool(workspace: Workspace, name: str, args: dict[str, Any]) -> str:
    """Dispatch a built-in tool call by name; never raises — returns an error string instead."""
    tool = BUILTIN_TOOLS.get(name)
    if tool is None:
        return f"Error: unknown tool '{name}'"
    try:
        return await tool(workspace, args)
    except KeyError as exc:
        return f"Error: missing required argument {exc}"
    except (OSError, ValueError) as exc:
        return f"Error: {exc}"
