from datetime import datetime

from src.api.services.deterministic_engine.field_mappings import FieldMapper
from src.api.services.deterministic_engine.models.intent import (
    AggregateFunction,
    DimensionField,
    Filter,
    FilterOperator,
    MetricField,
    QueryAction,
    QueryIntent,
)
from src.api.services.deterministic_engine.query_builder import QueryBuilder
from src.api.services.deterministic_engine.intent_sanitizer import sanitize_intent
from src.api.services.deterministic_engine.validator import QueryValidator


def test_compare_with_secondary_grouping_builds_compound_id():
    builder = QueryBuilder()
    intent = QueryIntent(
        action=QueryAction.COMPARE,
        metric=MetricField.SPENDING,
        aggregate_function=AggregateFunction.SUM,
        group_by=DimensionField.DEPARTMENT,
        group_by_secondary=DimensionField.FISCAL_YEAR_START,
    )

    pipeline = builder.build(intent)

    group_stage = pipeline[0]["$group"]
    expected_id = {
        "primary": f"${FieldMapper.get_mongo_field(DimensionField.DEPARTMENT)}",
        "secondary": f"${FieldMapper.get_mongo_field(DimensionField.FISCAL_YEAR_START)}",
    }
    assert group_stage["_id"] == expected_id

    sort_stage = next(stage["$sort"] for stage in pipeline if "$sort" in stage)
    assert sort_stage == {"value": -1}


def test_trend_defaults_to_fiscal_year_start_and_sorts_ascending():
    builder = QueryBuilder()
    intent = QueryIntent(
        action=QueryAction.TREND,
        metric=MetricField.SPENDING,
    )

    pipeline = builder.build(intent)

    group_stage = pipeline[0]["$group"]
    expected_group = f"${FieldMapper.get_mongo_field(DimensionField.FISCAL_YEAR_START)}"
    assert group_stage["_id"] == expected_group

    sort_stage = next(stage["$sort"] for stage in pipeline if "$sort" in stage)
    assert sort_stage == {"_id": 1}


def test_between_date_filter_coerces_to_datetime_range():
    builder = QueryBuilder()
    intent = QueryIntent(
        action=QueryAction.LIST,
        filters=[
            Filter(
                field=DimensionField.PURCHASE_DATE,
                operator=FilterOperator.BETWEEN,
                value=["2014-01-01", "2014-12-31"],
            )
        ],
    )

    pipeline = builder.build(intent)

    match_stage = pipeline[0]["$match"]
    field = FieldMapper.get_mongo_field(DimensionField.PURCHASE_DATE)
    condition = match_stage[field]

    assert isinstance(condition["$gte"], datetime)
    assert isinstance(condition["$lte"], datetime)


def test_validator_rejects_invalid_grouping():
    validator = QueryValidator()

    compare_missing_group = QueryIntent(action=QueryAction.COMPARE)
    valid, error = validator.validate_intent(compare_missing_group)
    assert not valid
    assert "group_by" in error

    secondary_without_primary = QueryIntent(
        action=QueryAction.AGGREGATE,
        group_by_secondary=DimensionField.SUPPLIER,
    )
    valid, error = validator.validate_intent(secondary_without_primary)
    assert not valid
    assert "group_by" in error

    secondary_same_as_primary = QueryIntent(
        action=QueryAction.AGGREGATE,
        group_by=DimensionField.SUPPLIER,
        group_by_secondary=DimensionField.SUPPLIER,
    )
    valid, error = validator.validate_intent(secondary_same_as_primary)
    assert not valid
    assert "group_by_secondary" in error


def test_sanitizer_keeps_purchase_order_grouping_only_when_explicit():
    intent = QueryIntent(
        action=QueryAction.TOP_N,
        metric=MetricField.SPENDING,
        group_by=DimensionField.PURCHASE_ORDER_NUMBER,
    )

    implicit = sanitize_intent("What are the top 5 purchase orders by total price?", intent)
    assert implicit.group_by is None

    explicit = sanitize_intent(
        "Top 5 purchase orders per purchase order number by total price",
        intent,
    )
    assert explicit.group_by == DimensionField.PURCHASE_ORDER_NUMBER
