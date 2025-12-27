"""
Utility Functions for API

Includes natural language query parsing and helper functions.
"""

import re
from typing import Dict, Any


def parse_natural_language_query(query: str) -> Dict[str, Any]:
    """
    Parse natural language query into MongoDB query structure.

    This is a basic implementation. For production, integrate with an LLM
    or use a more sophisticated NLP parser.

    Args:
        query: Natural language query string

    Returns:
        Dictionary with 'filter', 'projection', and 'sort' keys
    """
    query_lower = query.lower()
    mongo_query: Dict[str, Any] = {
        "filter": {},
        "projection": None,
        "sort": None
    }

    # Extract price filters
    price_patterns = [
        (r'over\s+\$?([\d,]+)', lambda m: {"$gt": float(m.group(1).replace(",", ""))}),
        (r'above\s+\$?([\d,]+)', lambda m: {"$gt": float(m.group(1).replace(",", ""))}),
        (r'more than\s+\$?([\d,]+)', lambda m: {"$gt": float(m.group(1).replace(",", ""))}),
        (r'under\s+\$?([\d,]+)', lambda m: {"$lt": float(m.group(1).replace(",", ""))}),
        (r'below\s+\$?([\d,]+)', lambda m: {"$lt": float(m.group(1).replace(",", ""))}),
        (r'less than\s+\$?([\d,]+)', lambda m: {"$lt": float(m.group(1).replace(",", ""))}),
    ]

    for pattern, handler in price_patterns:
        match = re.search(pattern, query_lower)
        if match:
            mongo_query["filter"]["item.total_price"] = handler(match)
            break

    # Extract acquisition type
    if "it goods" in query_lower or "it equipment" in query_lower:
        mongo_query["filter"]["acquisition.type"] = "IT Goods"
    elif "it services" in query_lower or "it service" in query_lower:
        mongo_query["filter"]["acquisition.type"] = "IT Services"
    elif "non-it goods" in query_lower:
        mongo_query["filter"]["acquisition.type"] = "NON-IT Goods"
    elif "non-it services" in query_lower:
        mongo_query["filter"]["acquisition.type"] = "NON-IT Services"

    # Extract year/fiscal year
    year_match = re.search(r'\b(20\d{2})\b', query)
    if year_match:
        year = year_match.group(1)
        # Match fiscal years like "2013-2014" or "2014-2015"
        mongo_query["filter"]["dates.fiscal_year"] = {
            "$regex": year
        }

    # Extract department
    dept_patterns = [
        r'department of ([\w\s]+?)(?:\s+in|\s+during|\s+for|$)',
        r'by (?:the )?([\w\s]+?department)(?:\s+in|\s+during|$)',
    ]

    for pattern in dept_patterns:
        match = re.search(pattern, query_lower)
        if match:
            dept_name = match.group(1).strip()
            mongo_query["filter"]["department.name"] = {
                "$regex": dept_name,
                "$options": "i"
            }
            break

    # Extract supplier
    supplier_patterns = [
        r'from ([\w\s]+?)(?:\s+in|\s+during|$)',
        r'supplier ([\w\s]+?)(?:\s+in|\s+during|$)',
        r'vendor ([\w\s]+?)(?:\s+in|\s+during|$)',
    ]

    for pattern in supplier_patterns:
        match = re.search(pattern, query_lower)
        if match:
            supplier_name = match.group(1).strip()
            # Only add if it doesn't match department patterns
            if "department" not in supplier_name:
                mongo_query["filter"]["supplier.name"] = {
                    "$regex": supplier_name,
                    "$options": "i"
                }
            break

    # Handle "top N" queries
    top_match = re.search(r'top\s+(\d+)', query_lower)
    if top_match:
        limit = int(top_match.group(1))
        # Usually "top N" means sorted by spend
        mongo_query["sort"] = {"item.total_price": -1}

    # Handle sorting
    if "highest" in query_lower or "largest" in query_lower or "most expensive" in query_lower:
        mongo_query["sort"] = {"item.total_price": -1}
    elif "lowest" in query_lower or "smallest" in query_lower or "least expensive" in query_lower:
        mongo_query["sort"] = {"item.total_price": 1}
    elif "recent" in query_lower or "latest" in query_lower:
        mongo_query["sort"] = {"dates.creation": -1}
    elif "oldest" in query_lower:
        mongo_query["sort"] = {"dates.creation": 1}

    # Handle text search keywords
    search_terms = []
    if "furniture" in query_lower:
        search_terms.append("furniture")
    if "computer" in query_lower or "computers" in query_lower:
        search_terms.append("computer")
    if "software" in query_lower:
        search_terms.append("software")
    if "vehicle" in query_lower or "vehicles" in query_lower:
        search_terms.append("vehicle")

    if search_terms and "$text" not in str(mongo_query["filter"]):
        # Use text search if no other specific filters
        if len(mongo_query["filter"]) == 0:
            mongo_query["filter"]["$text"] = {"$search": " ".join(search_terms)}

    # If query is very simple and no filters matched, do text search
    if not mongo_query["filter"]:
        # Extract meaningful words (skip common words)
        skip_words = {"show", "me", "all", "find", "get", "list", "the", "a", "an", "in", "on", "for", "by"}
        words = [w for w in query_lower.split() if w not in skip_words and len(w) > 3]
        if words:
            mongo_query["filter"]["$text"] = {"$search": " ".join(words[:3])}

    return mongo_query
