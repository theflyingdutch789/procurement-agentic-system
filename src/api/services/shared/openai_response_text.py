"""Shared helpers for OpenAI response parsing."""

from typing import Any, Optional


def extract_openai_response_text(
    response: Any,
    *,
    logger: Optional[Any] = None,
    require_content: bool = False,
) -> str:
    """Extract concatenated text from OpenAI Responses API output."""
    if hasattr(response, "output_text") and response.output_text:
        text = response.output_text
        if logger:
            logger.info("Got output_text: %s", text[:200])
        return text

    output_text = ""
    items = getattr(response, "output", None)
    if items:
        for item in items:
            if hasattr(item, "content") and item.content and isinstance(item.content, str):
                output_text += item.content
            elif hasattr(item, "text"):
                output_text += item.text

    if output_text and logger:
        logger.info("Extracted from output items: %s", output_text[:200])

    if require_content and not output_text:
        raise ValueError("No output text returned by model")

    return output_text
