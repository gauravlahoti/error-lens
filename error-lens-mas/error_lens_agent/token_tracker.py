"""Token usage tracking for ErrorLens agents.

Attaches to LlmAgent via after_model_callback. Accumulates token counts and
estimated cost in session state so any downstream agent or prompt can read them.

Usage:
    from error_lens_agent.token_tracker import make_token_tracker
    agent = LlmAgent(..., after_model_callback=make_token_tracker("gemini-2.5-flash"))
"""

from typing import Optional

# ── Cost table — USD per 1M tokens ───────────────────────────────────────────
# Sources: Google AI pricing page + Anthropic pricing page (April 2026)
COST_PER_1M: dict[str, dict[str, float]] = {
    # Gemini models
    "gemini-2.5-flash":                    {"input": 0.075,  "output": 0.30},
    "gemini-2.5-flash-lite":               {"input": 0.02,   "output": 0.08},
    "gemini-2.5-pro":                      {"input": 1.25,   "output": 10.00},
    # Anthropic models (via LiteLLM)
    "anthropic/claude-sonnet-4-5":         {"input": 3.00,   "output": 15.00},
    "anthropic/claude-haiku-4-5-20251001": {"input": 0.80,   "output": 4.00},
    "anthropic/claude-opus-4-6":           {"input": 15.00,  "output": 75.00},
}


def make_token_tracker(model_name: str):
    """Return an after_model_callback that accumulates token usage in session state.

    State keys written:
        _total_input_tokens  (int)   — cumulative prompt tokens this session
        _total_output_tokens (int)   — cumulative completion tokens this session
        _estimated_cost_usd  (float) — cumulative estimated cost in USD
        _models_used         (list)  — unique model names seen this session
        _cost_summary        (str)   — pre-formatted one-liner for prompt injection
    """

    def _track(callback_context, llm_response) -> Optional[object]:
        usage = getattr(llm_response, "usage_metadata", None)
        if not usage:
            return None

        in_tok  = getattr(usage, "prompt_token_count",     0) or 0
        out_tok = getattr(usage, "candidates_token_count", 0) or 0

        state = callback_context.state
        total_in   = state.get("_total_input_tokens",  0) + in_tok
        total_out  = state.get("_total_output_tokens", 0) + out_tok
        state["_total_input_tokens"]  = total_in
        state["_total_output_tokens"] = total_out

        rates      = COST_PER_1M.get(model_name, {"input": 0.0, "output": 0.0})
        call_cost  = (in_tok * rates["input"] + out_tok * rates["output"]) / 1_000_000
        total_cost = state.get("_estimated_cost_usd", 0.0) + call_cost
        state["_estimated_cost_usd"] = total_cost

        # Track unique models (list is immutable in ADK state — replace, not mutate)
        models = list(state.get("_models_used", []))
        if model_name not in models:
            models.append(model_name)
            state["_models_used"] = models

        # Pre-formatted summary for prompt interpolation via {_cost_summary?}
        state["_cost_summary"] = (
            f"{total_in:,} in + {total_out:,} out tokens · "
            f"~${total_cost:.4f} USD · "
            f"Model: {', '.join(models)}"
        )

        return None

    return _track
