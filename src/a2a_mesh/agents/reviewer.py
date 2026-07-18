"""Reviewer agent — system prompt and default config for a code-reviewing GenericAgent.

The Reviewer is a `GenericAgent` with no tools: it reviews whatever code text the previous
pipeline step (the Coder) handed it and returns a structured verdict as JSON, which
`orchestrator/engine.py`'s `loop_until` logic parses to decide whether to loop back to the
Coder or move on.
"""

from a2a_mesh.agents.base import AgentConfig, SkillConfig

REVIEWER_SYSTEM_PROMPT = (
    "You are a code review agent. You will be given a task description and the code written "
    "for it. Review the code for correctness, obvious bugs, and whether it actually satisfies "
    "the task. Respond with ONLY a JSON object — no markdown code fences, no other text — "
    'matching exactly this shape: {"approved": true or false, "feedback": "<why, or what '
    'needs to change>"}. Set "approved" to true only if the code is correct and complete.'
)


def build_reviewer_config(
    name: str = "reviewer",
    provider: str = "anthropic",
    model: str = "claude-opus-4-8",
) -> AgentConfig:
    """Build the default `AgentConfig` for a Reviewer agent.

    Args:
        name: Agent name (must be unique within the owning company).
        provider: LLM provider — "anthropic", "ollama", "openai", etc.
        model: Provider-specific model identifier.

    Returns:
        An `AgentConfig` ready to pass into `POST /v1/agents` or `GenericAgent` directly.
    """
    return AgentConfig(
        name=name,
        display_name="Reviewer",
        description="Reviews code against the task it was written for and scores it.",
        provider=provider,
        model=model,
        system_prompt=REVIEWER_SYSTEM_PROMPT,
        skills=[
            SkillConfig(
                id="review-code",
                name="Review Code",
                description="Approves or rejects code with feedback, as JSON.",
                tags=["code-review"],
            )
        ],
    )
