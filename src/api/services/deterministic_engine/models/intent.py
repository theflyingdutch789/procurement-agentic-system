"""
Structured intent models for deterministic query building.
"""

from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field


class QueryAction(str, Enum):
    """What type of query the user wants."""

    LIST = "list"
    COUNT = "count"
    TOP_N = "top_n"
    BOTTOM_N = "bottom_n"
    AGGREGATE = "aggregate"
    SINGLE_VALUE = "single"
    COMPARE = "compare"
    TREND = "trend"


class MetricField(str, Enum):
    """Measurable fields (for aggregation)."""

    SPENDING = "spending"
    QUANTITY = "quantity"
    UNIT_PRICE = "unit_price"
    ORDER_COUNT = "order_count"


class DimensionField(str, Enum):
    """Groupable/filterable fields."""

    DEPARTMENT = "department"
    DEPARTMENT_NAME = "department_name"
    SUPPLIER = "supplier"
    SUPPLIER_CODE = "supplier_code"
    FISCAL_YEAR = "fiscal_year"
    FISCAL_YEAR_START = "fiscal_year_start"
    PURCHASE_DATE = "purchase_date"
    CREATION_DATE = "creation_date"
    ACQUISITION_TYPE = "acquisition_type"
    ACQUISITION_SUB_TYPE = "acquisition_sub_type"
    ACQUISITION_METHOD = "acquisition_method"
    ACQUISITION_SUB_METHOD = "acquisition_sub_method"
    ITEM_NAME = "item_name"
    ITEM_DESCRIPTION = "item_description"
    PURCHASE_ORDER_NUMBER = "purchase_order_number"
    REQUISITION_NUMBER = "requisition_number"
    LPA_NUMBER = "lpa_number"
    SUPPLIER_ZIP = "supplier_zip"
    CLASSIFICATION = "classification"
    CLASSIFICATION_FAMILY = "classification_family"
    CLASSIFICATION_CLASS = "classification_class"
    CLASSIFICATION_COMMODITY = "classification_commodity"
    CAL_CARD = "cal_card"


class FilterOperator(str, Enum):
    """Filter comparison operators."""

    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_OR_EQUAL = "gte"
    LESS_OR_EQUAL = "lte"
    IN = "in"
    NOT_IN = "nin"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    BETWEEN = "between"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class AggregateFunction(str, Enum):
    """Aggregation functions."""

    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"


class SortOrder(str, Enum):
    """Sort direction."""

    ASC = "asc"
    DESC = "desc"


class Filter(BaseModel):
    """A single filter condition."""

    field: DimensionField
    operator: FilterOperator
    value: Optional[Union[str, int, float, bool, List[Union[str, int, float, bool]]]] = None

    class Config:
        use_enum_values = True


class QueryIntent(BaseModel):
    """
    Structured representation of user's query intent.
    This is what the AI extracts from natural language.
    """

    action: QueryAction

    metric: Optional[MetricField] = None
    aggregate_function: AggregateFunction = AggregateFunction.SUM

    group_by: Optional[DimensionField] = None
    group_by_secondary: Optional[DimensionField] = None

    filters: List[Filter] = Field(default_factory=list)

    sort_by: Optional[Union[MetricField, DimensionField]] = None
    sort_order: SortOrder = SortOrder.DESC

    limit: int = Field(default=10, ge=1, le=1000)

    select_fields: List[DimensionField] = Field(default_factory=list)

    is_ambiguous: bool = False
    ambiguity_reason: Optional[str] = None
    suggested_interpretations: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True
