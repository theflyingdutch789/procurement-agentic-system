"""Ambiguity detection for query clarification."""

from typing import List, Optional, Tuple

from .models.intent import QueryAction, QueryIntent


# Pattern 1: Purchase Order Grouping Ambiguity
PO_CONCEPT_PHRASES = (
    "purchase order",
    "purchase orders",
    "po ",
    "pos ",
    "p.o.",
    " po",
    " pos",
)

EXPLICIT_PO_GROUPING = (
    "per purchase order",
    "group by po",
    "grouped by po",
    "by po number",
    "by purchase order number",
    "sum of each po",
    "sum each po",
    "total per po",
    "total for each po",
    "grouped by purchase order",
    "group by purchase order",
    "per po number",
    "each purchase order",
    # Clarification responses - these indicate user has made a clear choice
    "sum all line items per po",
    "sum all line items",
    "total value",
    "by total value",
    "individual line items",
    "line items by price",
    # MAX option clarification responses
    "highest single line item",
    "max line item",
    "per purchase_order_number",
    "highest line item price",
    "max total_price per",
)

# Phrases that indicate user wants individual line items (NOT grouped by PO)
EXPLICIT_LINE_ITEMS = (
    "individual line items",
    "line items by price",
    "single line items",
    "each line item",
)

# Pattern 2: Missing Metric Ambiguity
# Phrases that explicitly state the ranking metric
EXPLICIT_METRIC_PHRASES = (
    "by spending",
    "by price",
    "by total price",
    "by quantity",
    "by unit price",
    "by count",
    "by order count",
    "by number of orders",
    "by value",
    "by amount",
    "by total",
    "by cost",
    "by volume",
)

# Phrases that clearly imply a specific metric (no ambiguity)
IMPLIED_METRIC_PHRASES = (
    "most expensive",      # implies price
    "least expensive",     # implies price
    "cheapest",            # implies price
    "highest spending",    # implies spending
    "lowest spending",     # implies spending
    "highest price",       # implies price
    "lowest price",        # implies price
    "most orders",         # implies count
    "fewest orders",       # implies count
    "most purchased",      # implies quantity
    "largest quantity",    # implies quantity
    "smallest quantity",   # implies quantity
)


def detect_ambiguity(
    question: str, intent: QueryIntent
) -> Tuple[bool, Optional[str], List[str]]:
    """
    Check if the query is ambiguous and needs clarification.

    Returns:
        (is_ambiguous, reason, suggested_interpretations)
    """
    text = question.lower()
    action = intent.action
    if isinstance(action, str):
        try:
            action = QueryAction(action)
        except ValueError:
            return (False, None, [])

    # Pattern 1: Purchase Order Grouping Ambiguity
    if action in {QueryAction.TOP_N, QueryAction.BOTTOM_N}:
        mentions_po = any(p in text for p in PO_CONCEPT_PHRASES)
        has_explicit_grouping = any(p in text for p in EXPLICIT_PO_GROUPING)

        if mentions_po and not has_explicit_grouping:
            # Preserve the user's requested limit in suggestions
            limit = intent.limit if intent.limit else 10
            return (
                True,
                (
                    "Your question mentions 'purchase orders' but it's unclear whether you want:\n"
                    "- Top individual line items by price, OR\n"
                    "- Top purchase orders by total value (sum of all line items in each PO)"
                ),
                [
                    f"Show top {limit} individual line items by price",
                    f"Show top {limit} purchase orders by total value (sum all line items per PO)",
                ],
            )

    # Pattern 2: Missing Metric Ambiguity for TOP_N/BOTTOM_N queries
    # If user asks for "top X" or "bottom X" without specifying what metric to rank by
    if action in {QueryAction.TOP_N, QueryAction.BOTTOM_N}:
        has_explicit_metric = any(p in text for p in EXPLICIT_METRIC_PHRASES)
        has_implied_metric = any(p in text for p in IMPLIED_METRIC_PHRASES)

        # If no explicit or implied metric, ask for clarification
        if not has_explicit_metric and not has_implied_metric:
            limit = intent.limit if intent.limit else 10
            action_word = "top" if action == QueryAction.TOP_N else "bottom"
            return (
                True,
                f"I need to clarify what metric you'd like to rank the {action_word} {limit} by:",
                [
                    f"{action_word.capitalize()} {limit} by total spending",
                    f"{action_word.capitalize()} {limit} by order count",
                    f"{action_word.capitalize()} {limit} by quantity",
                ],
            )

    return (False, None, [])
