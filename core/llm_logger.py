"""Thin wrapper around the Anthropic client that logs every call to the DB."""
import os

import anthropic
from dotenv import load_dotenv

from app.database import log_llm_call

load_dotenv()

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Price per single token for each model family (input, output).
# Keys are prefixes — matched with startswith() so date-suffixed IDs like
# "claude-haiku-4-5-20251001" still resolve correctly.
_PRICE_PER_TOKEN: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5":  (1.00 / 1_000_000, 5.00 / 1_000_000),
    "claude-sonnet-4-6": (3.00 / 1_000_000, 15.00 / 1_000_000),
    "claude-opus-4-8":   (5.00 / 1_000_000, 25.00 / 1_000_000),
}


def _compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    for prefix, (in_price, out_price) in _PRICE_PER_TOKEN.items():
        if model.startswith(prefix):
            return input_tokens * in_price + output_tokens * out_price
    return 0.0  # unknown model — log $0 rather than crash


def tracked_call(
    prompt_type: str,
    model: str,
    max_tokens: int,
    messages: list,
) -> anthropic.types.Message:
    """Call Claude and log the result (tokens, cost, outcome) to the DB."""
    try:
        response = _client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
        )
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost_usd = _compute_cost(model, input_tokens, output_tokens)
        log_llm_call(prompt_type, model, input_tokens, output_tokens, cost_usd, "success")
        return response
    except Exception as e:
        log_llm_call(prompt_type, model, 0, 0, 0.0, "error", str(e))
        raise
