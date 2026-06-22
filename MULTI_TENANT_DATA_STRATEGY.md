# Multi-Tenant Data Strategy (Procurement Platforms)

This document outlines how to scale the deterministic + AI hybrid approach to
multi-tenant procurement data where each client has different schemas, formats,
and naming conventions.

## Why Prompt-Only Is Not Enough

- Prompt engineering can help interpret messy data, but it cannot enforce a
  stable contract or guarantee correctness.
- LLMs are probabilistic; they may hallucinate fields or mis-handle edge cases.
- Compliance and auditability require deterministic, validated transformations.

The solution is a **semantic mapping layer** that normalizes every tenant into a
canonical schema, while using LLMs only where they are reliable and safe.

## High-Level Strategy

1. Canonical schema for procurement data (your "source of truth").
2. Per-tenant mapping configs from raw fields to canonical fields.
3. Deterministic query builder targets the canonical schema.
4. AI fallback when mapping coverage is incomplete or ambiguous.
5. Continuous profiling and mapping refinement.

## Canonical Schema (Example)

Keep a small, stable schema that your deterministic engine supports:

- purchase_order_number
- requisition_number
- supplier.name
- supplier.code
- department.name / department.normalized_name
- item.name / item.description / item.quantity / item.unit_price / item.total_price
- dates.purchase / dates.creation / dates.fiscal_year_start
- acquisition.type / acquisition.method
- classification.unspsc.segment.title

## Tenant Mapping Registry

Each tenant has a mapping config that translates raw fields into the canonical
schema. This can be stored in a database and versioned.

Example (JSON):
```json
{
  "tenant_id": "acme-corp",
  "version": "2025-01-01",
  "fields": {
    "PO_ID": "purchase_order_number",
    "VendorName": "supplier.name",
    "VendorID": "supplier.code",
    "Dept": "department.name",
    "LineTotal": "item.total_price",
    "LineQty": "item.quantity",
    "LineUnitPrice": "item.unit_price",
    "PurchaseDate": "dates.purchase",
    "CreatedAt": "dates.creation"
  },
  "types": {
    "LineTotal": "number",
    "PurchaseDate": "date"
  },
  "synonyms": {
    "supplier": ["vendor", "contractor"],
    "department": ["dept", "division"]
  }
}
```

## Ingestion and Normalization

- Raw data is ingested per tenant.
- A normalization job maps raw fields into canonical fields.
- Types are coerced (date, number, bool).
- Validation runs to confirm required fields exist and types are correct.
- Results are stored in a canonical collection with tenant_id partitioning.

This makes the deterministic engine reliable and fast.

## Query Flow in Multi-Tenant Mode

```
User Query
  |
  v
Intent Extractor (uses tenant schema + synonyms)
  |
  v
Deterministic Builder (canonical fields)
  |
  +--> If mapping coverage OK: run deterministic pipeline
  |
  +--> If mapping missing/ambiguous: AI fallback with context
```

## Where to Plug In (This Codebase)

- `src/api/services/deterministic_engine/field_mappings.py`
  - Replace static mappings with a registry-backed lookup.
- `src/api/services/deterministic_engine/intent_extractor.py`
  - Provide tenant-specific schema and synonym hints.
- `src/api/services/deterministic_engine/query_builder.py`
  - Use canonical fields only; no tenant-specific logic here.
- `src/api/services/deterministic_engine/validator.py`
  - Validate that all fields are mapped and typed.

## How LLMs Help Safely

Use LLMs for:
- Initial mapping suggestions (one-time setup per tenant).
- Intent extraction with strict schema.
- Fallback queries when deterministic mapping fails.

Do not use LLMs as the only source of truth.

## Rollout Plan

1. Build a canonical schema v1.
2. Create mapping configs for 2-3 pilot tenants.
3. Add ingestion normalization with validation.
4. Track mapping coverage and fallback rates.
5. Expand schema gradually only when multiple tenants need a field.

## Metrics to Track

- Mapping coverage (% queries fully deterministic)
- Fallback rate (% queries routed to AI)
- Validation failures (schema/type errors)
- Latency (deterministic vs fallback)
- Cost per query

## Summary

Deterministic querying scales in multi-tenant environments **only** when
you normalize data to a canonical schema and maintain a mapping registry.
LLMs remain powerful for intent extraction and fallback, but they should not
replace the semantic layer.
