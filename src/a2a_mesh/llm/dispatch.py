"""LLM dispatch — unified completion interface via LiteLLM.

Supported providers (value of the agent's `provider` field):
  - "anthropic" → Claude models (e.g. "claude-opus-4-8")
  - "ollama"    → local models (e.g. "llama3.2")
  - "openai"    → OpenAI models (e.g. "gpt-4o")

Any provider LiteLLM supports can be added by the caller without code changes here —
just pass the right provider name and model string.
"""

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import litellm

from a2a_mesh.config import settings

logger = logging.getLogger(__name__)

litellm.suppress_debug_info = True
litellm.anthropic_key = settings.anthropic_api_key
# Drop provider-unsupported params instead of raising. Needed because our default
# temperature (0.2) is rejected by some models — e.g. claude-opus-4-8 only accepts
# temperature=1 — and we want one agent config to work across every provider.
litellm.drop_params = True

MAX_TOOL_ITERATIONS = 5

ToolExecutor = Callable[[str, dict[str, Any]], Awaitable[str]]


def _to_litellm_model(provider: str, model: str) -> str:
    """Convert provider + model to the model string LiteLLM expects.

    Anthropic models are identified by name alone. All other providers
    use the "provider/model" prefix convention.
    """
    if provider == "anthropic":
        return model               # "claude-opus-4-8"
    return f"{provider}/{model}"   # "ollama/llama3.2", "openai/gpt-4o", …


async def complete(
    provider: str,
    system_prompt: str,
    user_message: str,
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    """Send a completion request to any LLM provider via LiteLLM.

    Args:
        provider: Provider name — "anthropic", "ollama", "openai", etc.
        system_prompt: Instructions that define the agent's behaviour.
        user_message: The user's input text.
        model: Provider-specific model identifier.
        temperature: Sampling temperature (0–1).
        max_tokens: Maximum tokens in the response.

    Returns:
        The assistant's text response.
    """
    litellm_model = _to_litellm_model(provider, model)
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})

    logger.info(
        "LLM request: provider=%s model=%s prompt_len=%d",
        provider, litellm_model, len(user_message),
    )

    response = await litellm.acompletion(
        model=litellm_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    text: str = response.choices[0].message.content
    logger.info("LLM response: provider=%s len=%d", provider, len(text))
    return text


async def run_with_tools(
    provider: str,
    system_prompt: str,
    user_message: str,
    model: str,
    tools: list[dict[str, Any]],
    tool_executor: ToolExecutor,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    max_iterations: int = MAX_TOOL_ITERATIONS,
) -> str:
    """Run a completion with tool-calling support, looping until a final text answer.

    Args:
        provider: Provider name — "anthropic", "ollama", "openai", etc.
        system_prompt: Instructions that define the agent's behaviour.
        user_message: The user's input text.
        model: Provider-specific model identifier.
        tools: OpenAI-style function tool schemas (LiteLLM function-calling format).
        tool_executor: Async callback invoked as `tool_executor(name, args)` for each
            tool call the model makes; must return the tool's result as a string.
        temperature: Sampling temperature (0-1).
        max_tokens: Maximum tokens per completion.
        max_iterations: Maximum number of tool-call round trips before giving up.

    Returns:
        The assistant's final text response.

    Raises:
        RuntimeError: If the model keeps calling tools past max_iterations without
            producing a final text answer.
    """
    litellm_model = _to_litellm_model(provider, model)
    messages: list[dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})

    for iteration in range(max_iterations):
        response = await litellm.acompletion(
            model=litellm_model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=temperature,
            max_tokens=max_tokens,
        )
        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None)

        if not tool_calls:
            text: str = message.content or ""
            logger.info(
                "Tool loop finished: provider=%s iterations=%d", provider, iteration + 1
            )
            return text

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls
                ],
            }
        )
        for tool_call in tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")
            logger.info("Tool call: name=%s args=%s", name, args)
            result = await tool_executor(name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    raise RuntimeError(
        f"Tool-calling loop exceeded max_iterations={max_iterations} without a final answer"
    )
