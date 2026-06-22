"""Deterministic MongoDB pipeline builder."""

from typing import Any, Dict, List, Optional, Tuple

from dateutil import parser as date_parser

from .field_mappings import FieldMapper
from .models.intent import (
    AggregateFunction,
    DimensionField,
    Filter,
    FilterOperator,
    MetricField,
    QueryAction,
    QueryIntent,
    SortOrder,
)


class QueryBuilder:
    """Builds MongoDB aggregation pipelines from structured intent."""

    DATE_FIELDS = {"dates.purchase", "dates.creation"}

    def build(self, intent: QueryIntent) -> List[Dict[str, Any]]:
        """Build MongoDB aggregation pipeline from intent."""
        if intent.is_ambiguous:
            raise ValueError(f"Cannot build query: {intent.ambiguity_reason}")

        action = intent.action
        if isinstance(action, str):
            action = QueryAction(action)

        builder_method = {
            QueryAction.LIST: self._build_list,
            QueryAction.COUNT: self._build_count,
            QueryAction.TOP_N: self._build_top_n,
            QueryAction.BOTTOM_N: self._build_bottom_n,
            QueryAction.AGGREGATE: self._build_aggregate,
            QueryAction.COMPARE: self._build_compare,
            QueryAction.TREND: self._build_trend,
            QueryAction.SINGLE_VALUE: self._build_single_value,
        }.get(action)

        if not builder_method:
            raise ValueError(f"Unsupported action: {intent.action}")

        return builder_method(intent)

    def _build_list(self, intent: QueryIntent) -> List[Dict[str, Any]]:
        pipeline: List[Dict[str, Any]] = []

        if intent.filters:
            pipeline.append({"$match": self._build_match(intent.filters)})

        sort_field = self._get_sort_field(intent, default="item.total_price")
        sort_order = intent.sort_order
        if isinstance(sort_order, str):
            sort_order = SortOrder(sort_order)
        sort_dir = 1 if sort_order == SortOrder.ASC else -1
        pipeline.append({"$sort": {sort_field: sort_dir}})

        pipeline.append({"$limit": intent.limit})

        if intent.select_fields:
            pipeline.append({"$project": self._build_projection(intent.select_fields)})

        return pipeline

    def _build_count(self, intent: QueryIntent) -> List[Dict[str, Any]]:
        pipeline: List[Dict[str, Any]] = []

        if intent.filters:
            pipeline.append({"$match": self._build_match(intent.filters)})

        pipeline.append({"$count": "count"})

        return pipeline

    def _build_top_n(self, intent: QueryIntent) -> List[Dict[str, Any]]:
        if not intent.group_by:
            return self._build_ranked_list(intent, descending=True)

        pipeline: List[Dict[str, Any]] = []

        if intent.filters:
            pipeline.append({"$match": self._build_match(intent.filters)})

        pipeline.extend(self._build_group_stages(intent))

        pipeline.append({"$sort": {"value": -1}})
        pipeline.append({"$limit": intent.limit})

        return pipeline

    def _build_bottom_n(self, intent: QueryIntent) -> List[Dict[str, Any]]:
        if not intent.group_by:
            return self._build_ranked_list(intent, descending=False)

        pipeline = self._build_top_n(intent)
        for stage in pipeline:
            if "$sort" in stage:
                for field in stage["$sort"]:
                    stage["$sort"][field] = 1
        return pipeline

    def _build_aggregate(self, intent: QueryIntent) -> List[Dict[str, Any]]:
        if not intent.group_by:
            raise ValueError("Aggregate action requires group_by")

        pipeline: List[Dict[str, Any]] = []

        if intent.filters:
            pipeline.append({"$match": self._build_match(intent.filters)})

        pipeline.extend(self._build_group_stages(intent))

        pipeline.append({"$sort": self._build_group_sort(intent)})
        pipeline.append({"$limit": intent.limit})

        return pipeline

    def _build_compare(self, intent: QueryIntent) -> List[Dict[str, Any]]:
        if not intent.group_by:
            raise ValueError("Compare action requires group_by")

        pipeline: List[Dict[str, Any]] = []

        if intent.filters:
            pipeline.append({"$match": self._build_match(intent.filters)})

        pipeline.extend(self._build_group_stages(intent))
        pipeline.append({"$sort": self._build_group_sort(intent)})
        pipeline.append({"$limit": intent.limit})

        return pipeline

    def _build_trend(self, intent: QueryIntent) -> List[Dict[str, Any]]:
        effective_intent = intent
        if not intent.group_by:
            effective_intent = intent.model_copy(deep=True)
            effective_intent.group_by = DimensionField.FISCAL_YEAR_START

        pipeline: List[Dict[str, Any]] = []

        if effective_intent.filters:
            pipeline.append({"$match": self._build_match(effective_intent.filters)})

        pipeline.extend(self._build_group_stages(effective_intent))
        pipeline.append(
            {
                "$sort": self._build_group_sort(
                    effective_intent,
                    default_sort_order=SortOrder.ASC,
                    prefer_group=True,
                )
            }
        )
        pipeline.append({"$limit": effective_intent.limit})

        return pipeline

    def _build_single_value(self, intent: QueryIntent) -> List[Dict[str, Any]]:
        pipeline: List[Dict[str, Any]] = []

        if intent.filters:
            pipeline.append({"$match": self._build_match(intent.filters)})

        pipeline.extend(self._build_group_stages(intent, group_all=True))
        pipeline.append({"$limit": 1})

        return pipeline

    def _build_ranked_list(self, intent: QueryIntent, descending: bool) -> List[Dict[str, Any]]:
        pipeline: List[Dict[str, Any]] = []

        if intent.filters:
            pipeline.append({"$match": self._build_match(intent.filters)})

        metric_field = intent.metric or MetricField.SPENDING
        sort_field = FieldMapper.get_mongo_field(metric_field)
        if sort_field == "__COUNT__":
            sort_field = "item.total_price"

        sort_dir = -1 if descending else 1
        pipeline.append({"$sort": {sort_field: sort_dir}})
        pipeline.append({"$limit": intent.limit})

        if intent.select_fields:
            pipeline.append({"$project": self._build_projection(intent.select_fields)})

        return pipeline

    def _build_match(self, filters: List[Filter]) -> Dict[str, Any]:
        clauses: List[Dict[str, Any]] = []
        for filt in filters:
            mongo_field = FieldMapper.get_mongo_field(filt.field)
            value = self._normalize_filter_value(mongo_field, filt.value)
            condition = self._filter_to_condition(filt, value)
            clauses.append({mongo_field: condition})

        if not clauses:
            return {}
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}

    def _filter_to_condition(self, filt: Filter, value: Any) -> Any:
        operator = filt.operator
        if isinstance(operator, str):
            operator = FilterOperator(operator)

        op_map = {
            FilterOperator.EQUALS: lambda v: v,
            FilterOperator.NOT_EQUALS: lambda v: {"$ne": v},
            FilterOperator.GREATER_THAN: lambda v: {"$gt": v},
            FilterOperator.LESS_THAN: lambda v: {"$lt": v},
            FilterOperator.GREATER_OR_EQUAL: lambda v: {"$gte": v},
            FilterOperator.LESS_OR_EQUAL: lambda v: {"$lte": v},
            FilterOperator.IN: lambda v: {"$in": v if isinstance(v, list) else [v]},
            FilterOperator.NOT_IN: lambda v: {"$nin": v if isinstance(v, list) else [v]},
            FilterOperator.CONTAINS: lambda v: {"$regex": v, "$options": "i"},
            FilterOperator.STARTS_WITH: lambda v: {"$regex": f"^{v}", "$options": "i"},
            FilterOperator.BETWEEN: self._build_between_condition,
            FilterOperator.IS_NULL: lambda v: None,
            FilterOperator.IS_NOT_NULL: lambda v: {"$ne": None},
        }

        return op_map[operator](value)

    def _build_between_condition(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, (list, tuple)) and len(value) == 2:
            start, end = value
            return {"$gte": start, "$lte": end}
        raise ValueError("Between operator requires a 2-item list")

    def _normalize_filter_value(self, mongo_field: str, value: Any) -> Any:
        if mongo_field in self.DATE_FIELDS:
            return self._coerce_date(value)
        return value

    def _coerce_date(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self._coerce_date(item) for item in value]
        if isinstance(value, str):
            try:
                return date_parser.parse(value)
            except (ValueError, TypeError):
                return value
        return value

    def _build_group_stages(self, intent: QueryIntent, group_all: bool = False) -> List[Dict[str, Any]]:
        group_id = self._build_group_id(intent, group_all=group_all)

        metric = intent.metric or MetricField.SPENDING
        metric_field = FieldMapper.get_mongo_field(metric)

        accumulator, needs_distinct_size = self._build_accumulator(
            intent.aggregate_function,
            metric_field,
            metric,
        )

        stages: List[Dict[str, Any]] = [
            {
                "$group": {
                    "_id": group_id,
                    "value": accumulator,
                    "count": {"$sum": 1},
                }
            }
        ]

        if needs_distinct_size:
            stages.append({"$addFields": {"value": {"$size": "$value"}}})

        return stages

    def _build_group_id(self, intent: QueryIntent, group_all: bool = False) -> Any:
        if group_all:
            return None

        if not intent.group_by:
            raise ValueError("Grouping requires group_by")

        primary_field = FieldMapper.get_mongo_field(intent.group_by)
        if intent.group_by_secondary:
            secondary_field = FieldMapper.get_mongo_field(intent.group_by_secondary)
            return {"primary": f"${primary_field}", "secondary": f"${secondary_field}"}
        return f"${primary_field}"

    def _build_group_sort(
        self,
        intent: QueryIntent,
        *,
        default_field: str = "value",
        default_sort_order: SortOrder = SortOrder.DESC,
        prefer_group: bool = False,
    ) -> Dict[str, int]:
        sort_order = intent.sort_order
        if isinstance(sort_order, str):
            sort_order = SortOrder(sort_order)

        if intent.sort_by:
            sort_dir = 1 if sort_order == SortOrder.ASC else -1
            if intent.group_by_secondary and intent.sort_by == intent.group_by_secondary:
                return {"_id.secondary": sort_dir}
            if intent.sort_by == intent.group_by:
                if intent.group_by_secondary:
                    return {"_id.primary": sort_dir}
                return {"_id": sort_dir}
            return {default_field: sort_dir}

        sort_dir = 1 if default_sort_order == SortOrder.ASC else -1
        if prefer_group:
            if intent.group_by_secondary:
                return {"_id.primary": sort_dir, "_id.secondary": sort_dir}
            return {"_id": sort_dir}
        return {default_field: sort_dir}

    def _build_accumulator(
        self,
        func: AggregateFunction,
        field: Optional[str],
        metric: MetricField,
    ) -> Tuple[Dict[str, Any], bool]:
        if metric == MetricField.ORDER_COUNT or metric == MetricField.ORDER_COUNT.value:
            return {"$sum": 1}, False

        if isinstance(func, str):
            func = AggregateFunction(func)

        if func == AggregateFunction.COUNT:
            return {"$sum": 1}, False

        if func == AggregateFunction.COUNT_DISTINCT:
            return {"$addToSet": f"${field}"}, True

        field_ref = {"$ifNull": [f"${field}", 0]} if field else 0

        func_map = {
            AggregateFunction.SUM: "$sum",
            AggregateFunction.AVG: "$avg",
            AggregateFunction.MIN: "$min",
            AggregateFunction.MAX: "$max",
        }

        return {func_map[func]: field_ref}, False

    def _get_sort_field(self, intent: QueryIntent, default: str) -> str:
        if intent.sort_by:
            mongo_field = FieldMapper.get_mongo_field(intent.sort_by)
            if mongo_field == "__COUNT__":
                raise ValueError("ORDER_COUNT is not a valid sort field for list queries")
            return mongo_field
        return default

    def _build_projection(self, fields: List) -> Dict[str, int]:
        projection = {"_id": 0}
        for field in fields:
            mongo_field = FieldMapper.get_mongo_field(field)
            if mongo_field == "__COUNT__":
                continue
            projection[mongo_field] = 1
        return projection
