"""Prefixed ID generation for all entities."""

import secrets


def _generate(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def company_id() -> str:
    return _generate("co")


def user_id() -> str:
    return _generate("usr")


def agent_id() -> str:
    return _generate("agt")


def pipeline_id() -> str:
    return _generate("pip")


def run_id() -> str:
    return _generate("run")


def task_id() -> str:
    return _generate("tsk")


def api_key_id() -> str:
    return _generate("key")


def trust_id() -> str:
    return _generate("trust")
