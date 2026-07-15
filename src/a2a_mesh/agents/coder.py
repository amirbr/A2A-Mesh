"""Coder agent — system prompt and default config for a code-writing GenericAgent.

The Coder is not a separate execution path: it's a `GenericAgent` configured with the
`file_read` / `file_write` / `run_tests` / `git_diff` built-in tools (see `agents/tools.py`
and `GenericAgent._process_with_tools`). This module just defines what "a Coder" means.
"""

from a2a_mesh.agents.base import AgentConfig, SkillConfig

CODER_SYSTEM_PROMPT = (
    "You are a software engineer agent. You implement the requested change directly in the "
    "task workspace using your tools: file_read to inspect existing files, file_write to "
    "create or edit files, run_tests to verify your change works, and git_diff to review what "
    "you changed. Always run the tests before giving your final answer. Keep changes minimal "
    "and scoped to exactly what was asked."
)

CODER_TOOLS = ["file_read", "file_write", "run_tests", "git_diff"]


def build_coder_config(
    name: str = "coder",
    provider: str = "anthropic",
    model: str = "claude-opus-4-8",
) -> AgentConfig:
    """Build the default `AgentConfig` for a Coder agent.

    Args:
        name: Agent name (must be unique within the owning company).
        provider: LLM provider — "anthropic", "ollama", "openai", etc.
        model: Provider-specific model identifier.

    Returns:
        An `AgentConfig` ready to pass into `POST /v1/agents` or `GenericAgent` directly.
    """
    return AgentConfig(
        name=name,
        display_name="Coder",
        description="Writes and tests code from a task description.",
        provider=provider,
        model=model,
        system_prompt=CODER_SYSTEM_PROMPT,
        tools=CODER_TOOLS,
        skills=[
            SkillConfig(
                id="write-code",
                name="Write Code",
                description="Implements a coding task end-to-end and verifies it with tests.",
                tags=["coding"],
            )
        ],
    )
