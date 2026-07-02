"""In-process agent registry — tracks running agent instances."""

import logging

from a2a_mesh.agents.base import BaseAgent

logger = logging.getLogger(__name__)

# agent_id → BaseAgent instance
_registry: dict[str, BaseAgent] = {}


def register(agent_id: str, agent: BaseAgent) -> None:
    """Add a running agent to the registry."""
    _registry[agent_id] = agent
    logger.info("Registered agent %s (%s)", agent_id, agent.config.name)


def unregister(agent_id: str) -> None:
    """Remove an agent from the registry."""
    _registry.pop(agent_id, None)
    logger.info("Unregistered agent %s", agent_id)


def get(agent_id: str) -> BaseAgent | None:
    """Return the running agent instance, or None if not deployed."""
    return _registry.get(agent_id)


def list_running() -> list[str]:
    """Return all currently registered agent IDs."""
    return list(_registry.keys())
