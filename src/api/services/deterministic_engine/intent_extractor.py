"""AI-powered intent extraction using structured output."""

import json
from typing import Optional

from openai import OpenAI

from .models.intent import QueryIntent
from ..shared.openai_response_text import extract_openai_response_text


INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["list", "count", "top_n", "bottom_n", "aggregate", "single", "compare", "trend"],
        },
        "metric": {
            "type": "string",
            "enum": ["spending", "quantity", "unit_price", "order_count"],
        },
        "aggregate_function": {
            "type": "string",
            "enum": ["sum", "avg", "min", "max", "count", "count_distinct"],
            "default": "sum",
        },
        "group_by": {
            "type": "string",
            "enum": [
                "department",
                "department_name",
                "supplier",
                "supplier_code",
                "fiscal_year",
                "fiscal_year_start",
                "purchase_date",
                "creation_date",
                "acquisition_type",
                "acquisition_sub_type",
                "acquisition_method",
                "acquisition_sub_method",
                "item_name",
                "item_description",
                "purchase_order_number",
                "requisition_number",
                "lpa_number",
                "supplier_zip",
                "classification",
                "classification_family",
                "classification_class",
                "classification_commodity",
                "cal_card",
            ],
        },
        "group_by_secondary": {
            "type": "string",
            "enum": [
                "department",
                "department_name",
                "supplier",
                "supplier_code",
                "fiscal_year",
                "fiscal_year_start",
                "purchase_date",
                "creation_date",
                "acquisition_type",
                "acquisition_sub_type",
                "acquisition_method",
                "acquisition_sub_method",
                "item_name",
                "item_description",
                "purchase_order_number",
                "requisition_number",
                "lpa_number",
                "supplier_zip",
                "classification",
                "classification_family",
                "classification_class",
                "classification_commodity",
                "cal_card",
            ],
        },
        "filters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "operator": {
                        "type": "string",
                        "enum": [
                            "eq",
                            "ne",
                            "gt",
                            "lt",
                            "gte",
                            "lte",
                            "in",
                            "nin",
                            "contains",
                            "starts_with",
                            "between",
                            "is_null",
                            "is_not_null",
                        ],
                    },
                    "value": {},
                },
                "required": ["field", "operator"],
            },
        },
        "sort_by": {
            "type": "string",
            "enum": [
                "spending",
                "quantity",
                "unit_price",
                "order_count",
                "department",
                "department_name",
                "supplier",
                "supplier_code",
                "fiscal_year",
                "fiscal_year_start",
                "purchase_date",
                "creation_date",
                "acquisition_type",
                "acquisition_sub_type",
                "acquisition_method",
                "acquisition_sub_method",
                "item_name",
                "item_description",
                "purchase_order_number",
                "requisition_number",
                "lpa_number",
                "supplier_zip",
                "classification",
                "classification_family",
                "classification_class",
                "classification_commodity",
                "cal_card",
            ],
        },
        "sort_order": {
            "type": "string",
            "enum": ["asc", "desc"],
            "default": "desc",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 1000,
            "default": 10,
        },
        "select_fields": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "department",
                    "department_name",
                    "supplier",
                    "supplier_code",
                    "fiscal_year",
                    "fiscal_year_start",
                    "purchase_date",
                    "creation_date",
                    "acquisition_type",
                    "acquisition_sub_type",
                    "acquisition_method",
                    "acquisition_sub_method",
                    "item_name",
                    "item_description",
                    "purchase_order_number",
                    "requisition_number",
                    "lpa_number",
                    "supplier_zip",
                    "classification",
                    "classification_family",
                    "classification_class",
                    "classification_commodity",
                    "cal_card",
                ],
            },
        },
        "is_ambiguous": {"type": "boolean", "default": False},
        "ambiguity_reason": {"type": "string"},
        "suggested_interpretations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["action"],
}


EXTRACTION_PROMPT = """You are an intent extractor for a procurement database query system.

Your job is to understand what the user wants and return a structured intent object.
Do NOT generate database queries. Only extract the user's intent.

CRITICAL FORMAT RULES:
- "metric" must be a simple STRING, one of: "spending", "quantity", "unit_price", "order_count"
- "aggregate_function" must be a simple STRING, one of: "sum", "avg", "min", "max", "count"
- "action" must be a simple STRING, one of: "list", "count", "top_n", "bottom_n", "aggregate", "single", "compare", "trend"
- Do NOT nest objects inside these fields - they must be plain strings!

==============================================================================
CRITICAL DATA MODEL - YOU MUST UNDERSTAND THIS TO DETECT AMBIGUITY
==============================================================================

This database stores California state government procurement data (2012-2015).

KEY INSIGHT: Each document in the database represents ONE LINE ITEM, not one purchase order!

A single Purchase Order (PO) can have MULTIPLE line items, each stored as a separate document.
Example:
  PO #4500123456 for Department of Defense:
  ├─ Document 1: {purchase_order_number: "4500123456", item: "Laptop", total_price: 60000}
  ├─ Document 2: {purchase_order_number: "4500123456", item: "Monitor", total_price: 30000}
  └─ Document 3: {purchase_order_number: "4500123456", item: "Keyboard", total_price: 2500}

  To get "total PO value", you must SUM all line items with the same purchase_order_number.

FIELDS AVAILABLE:
  METRICS (for aggregation/ranking):
  - spending (item.total_price) - dollar amount of this line item
  - quantity - number of units in this line item
  - unit_price - price per unit
  - order_count - count of records

  DIMENSIONS (for grouping/filtering):
  - department / department_name - government department
  - supplier / supplier_code - vendor information
  - fiscal_year (string: "2013-2014") / fiscal_year_start (integer: 2013)
  - purchase_date / creation_date - dates
  - acquisition_type - "IT Goods", "IT Services", "NON-IT Goods", "NON-IT Services"
  - item_name / item_description - what was purchased
  - purchase_order_number - PO identifier (multiple docs can share same PO number!)
  - classification / classification_family / classification_class - UNSPSC categories
  - supplier_zip, cal_card, etc.

==============================================================================
AMBIGUITY DETECTION - THIS IS YOUR MOST IMPORTANT RESPONSIBILITY
==============================================================================

You MUST detect ambiguity when the user's question could reasonably be interpreted
in MULTIPLE WAYS given the data model above. When ambiguous, set:
  - is_ambiguous: true
  - ambiguity_reason: Clear explanation of why it's ambiguous
  - suggested_interpretations: 2-3 specific, actionable rephrased queries
    IMPORTANT: Preserve specific details from the original query (numbers, filters, etc.)
    Example: If user asks "top 5 purchase orders", suggestions should say "top 5" not "top N"

COMMON AMBIGUITY PATTERNS (but think beyond these!):

1. PURCHASE ORDER vs LINE ITEM AMBIGUITY:
   "Top 5 purchase orders by price" is AMBIGUOUS because:
   - Could mean: Top 5 individual line items by their price
   - Could mean: Top 5 POs by total value (sum all line items per PO)
   User must clarify: "top 5 line items by price" OR "top 5 POs by total value (sum per PO)"

2. MISSING METRIC AMBIGUITY:
   "Largest orders" / "Top items" / "Biggest purchases" is AMBIGUOUS because:
   - Largest by spending? By quantity? By unit price?
   User must specify the metric.

3. TIME PERIOD AMBIGUITY:
   "Year 2014" is AMBIGUOUS because:
   - Calendar year 2014? Or fiscal year 2013-2014 (starts July 2013)?

4. AGGREGATION LEVEL AMBIGUITY:
   "Average order value" is AMBIGUOUS because:
   - Average line item value? Or average PO value (sum of line items per PO, then average)?

5. COMPARISON AMBIGUITY:
   "Compare spending" is AMBIGUOUS because:
   - Compare what? Departments? Fiscal years? Suppliers?

6. DUPLICATE/SIMILARITY AMBIGUITY:
   "Show duplicate orders" is AMBIGUOUS because:
   - Same PO number? Same item name? Same price? Same supplier?

WHEN TO NOT FLAG AMBIGUITY:
- If the user's query is clear and specific (e.g., "total spending by department in fiscal year 2014")
- If the user explicitly states their intent (e.g., "sum all line items per PO")
- If clarification phrases are present like:
  * "individual line items" / "each line item" / "line items by price"
  * "per purchase order" / "group by PO" / "sum per PO" / "total value per PO"
  * "by spending" / "by quantity" / "by price" / "by total value"

==============================================================================
EXTRACTION RULES
==============================================================================

1. "Top N X by Y" -> action=top_n, group_by=X, metric=Y
2. "How many" -> action=count
3. "Total/sum of" -> action=single, aggregate_function=sum
4. "Average" -> aggregate_function=avg
5. For fiscal year numeric comparisons, prefer fiscal_year_start
6. "Fiscal year 2014" refers to fiscal year starting in 2013 (2013-2014)
7. "by X and Y" -> group_by=X, group_by_secondary=Y
8. "between 2013 and 2015" -> operator=between

Return ONLY the JSON object matching the schema."""


class IntentExtractor:
    """Extract structured query intent from natural language."""

    def __init__(self, client: OpenAI, model: str = "gpt-5"):
        self.client = client
        self.model = model

    def set_model_name(self, model: str) -> None:
        self.model = model

    def extract(self, question: str, conversation_context: Optional[str] = None) -> QueryIntent:
        prompt = EXTRACTION_PROMPT
        if conversation_context:
            prompt += f"\n\nPREVIOUS CONTEXT:\n{conversation_context}"

        prompt += f"\n\nUSER QUESTION: {question}"

        if self._supports_chat_schema():
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0,
                )

                content = response.choices[0].message.content
                if not content:
                    raise ValueError("No intent content returned by model")

                intent_data = json.loads(content)
                return QueryIntent(**intent_data)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("Chat completions failed: %s", e)
                pass

        response = self.client.responses.create(
            model=self.model,
            input=prompt + "\n\nReturn ONLY the JSON object matching the schema.",
            text={"verbosity": "low"},
            max_output_tokens=1200,
        )
        output_text = extract_openai_response_text(response, require_content=True)
        json_obj = self._extract_json_object(output_text)
        intent_data = json.loads(json_obj)
        return QueryIntent(**intent_data)

    def _extract_json_object(self, source_text: str) -> str:
        start_idx = source_text.find("{")
        end_idx = source_text.rfind("}")
        if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
            raise ValueError("Failed to parse JSON object from model output")
        return source_text[start_idx : end_idx + 1]

    def _supports_chat_schema(self) -> bool:
        # Always use chat completions API - it's more reliable
        return True
