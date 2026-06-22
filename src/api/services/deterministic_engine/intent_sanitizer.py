"""Intent sanitization and deterministic ambiguity detection.

This module provides a hybrid approach to ambiguity detection:
1. The LLM may flag ambiguity during intent extraction
2. This sanitizer applies deterministic rules as a safety net for known patterns

The deterministic detector ensures consistent behavior for common ambiguity patterns
that the LLM might miss due to its non-deterministic nature.
"""

from __future__ import annotations

from typing import Optional

from .ambiguity_detector import detect_ambiguity
from .models.intent import DimensionField, QueryAction, QueryIntent


# Phrases that indicate user explicitly wants PO-level grouping
EXPLICIT_PO_PHRASES = (
    "purchase_order_number",
    "purchase order number",
    "group by purchase order",
    "grouped by purchase order",
    "per purchase order",
    "each purchase order",
    "by purchase order number",
    "by purchase order",
    "by po number",
    "po number",
    "po #",
    "po#",
    "by po",
    "per po",
    # Clarification responses that indicate PO-level grouping
    "sum per po",
    "total per po",
    "total value per po",
    "sum all line items per po",
    "sum all line items",
    "by total value",
)

# Phrases that indicate user explicitly wants line-item level
EXPLICIT_LINE_ITEM_PHRASES = (
    "individual line items",
    "line items by price",
    "each line item",
    "single line items",
)


def sanitize_intent(
    question: str,
    intent: QueryIntent,
    is_clarification_response: bool = False
) -> QueryIntent:
    """Normalize intent fields and apply deterministic ambiguity detection.

    This function:
    1. Checks for ambiguity using deterministic rules (safety net for LLM misses)
       - Skipped if is_clarification_response=True (user already answered clarification)
    2. Normalizes/cleans up intent fields for deterministic processing

    Args:
        question: The user's question
        intent: Extracted query intent from LLM
        is_clarification_response: If True, skip ambiguity detection (user responded to clarification)
    """
    if intent.is_ambiguous:
        return intent

    # Skip deterministic ambiguity detection if user is responding to clarification
    if not is_clarification_response:
        # Apply deterministic ambiguity detection as safety net
        is_ambiguous, reason, suggestions = detect_ambiguity(question, intent)
        if is_ambiguous:
            updated = intent.model_copy(deep=True)
            updated.is_ambiguous = True
            updated.ambiguity_reason = reason
            updated.suggested_interpretations = suggestions
            return updated

    updated = intent.model_copy(deep=True)

    action = updated.action
    if isinstance(action, str):
        try:
            action = QueryAction(action)
        except ValueError:
            return updated

    # If user explicitly requested line items, remove any PO grouping
    if _mentions_explicit_line_items(question):
        if _is_purchase_order_dimension(updated.group_by):
            updated.group_by = None
        if _is_purchase_order_dimension(updated.group_by_secondary):
            updated.group_by_secondary = None
        return updated

    # If user explicitly requested PO grouping, keep it
    if _mentions_explicit_po_grouping(question):
        return updated

    # Default behavior: if LLM set PO grouping without explicit request,
    # we trust the LLM's interpretation (it should have flagged ambiguity if unclear)
    return updated


def _mentions_explicit_po_grouping(question: str) -> bool:
    text = question.lower()
    return any(phrase in text for phrase in EXPLICIT_PO_PHRASES)


def _mentions_explicit_line_items(question: str) -> bool:
    text = question.lower()
    return any(phrase in text for phrase in EXPLICIT_LINE_ITEM_PHRASES)


def _is_purchase_order_dimension(value: Optional[object]) -> bool:
    if value is None:
        return False
    if isinstance(value, DimensionField):
        return value == DimensionField.PURCHASE_ORDER_NUMBER
    if isinstance(value, str):
        return value == DimensionField.PURCHASE_ORDER_NUMBER.value
    return False
