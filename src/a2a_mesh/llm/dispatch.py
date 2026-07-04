"""LLM dispatch — unified completion interface via LiteLLM.

Supported providers (value of the agent's `provider` field):
  - "anthropic" → Claude models (e.g. "claude-opus-4-8")
  - "ollama"    → local models (e.g. "llama3.2")
  - "openai"    → OpenAI models (e.g. "gpt-4o")

Any provider LiteLLM supports can be added by the caller without code changes here —
just pass the right provider name and model string.
"""

import logging

import litellm

from a2a_mesh.config import settings

logger = logging.getLogger(__name__)

litellm.suppress_debug_info = True
litellm.anthropic_key = settings.anthropic_api_key


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
