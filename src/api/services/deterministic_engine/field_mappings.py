"""Semantic field mappings for the query engine."""

from typing import Dict

from .models.intent import DimensionField, MetricField


class FieldMapper:
    """Maps semantic field names to MongoDB field paths."""

    METRIC_MAPPINGS: Dict[MetricField, str] = {
        MetricField.SPENDING: "item.total_price",
        MetricField.QUANTITY: "item.quantity",
        MetricField.UNIT_PRICE: "item.unit_price",
        MetricField.ORDER_COUNT: "__COUNT__",
    }

    DIMENSION_MAPPINGS: Dict[DimensionField, str] = {
        DimensionField.DEPARTMENT: "department.normalized_name",
        DimensionField.DEPARTMENT_NAME: "department.name",
        DimensionField.SUPPLIER: "supplier.name",
        DimensionField.SUPPLIER_CODE: "supplier.code",
        DimensionField.FISCAL_YEAR: "dates.fiscal_year",
        DimensionField.FISCAL_YEAR_START: "dates.fiscal_year_start",
        DimensionField.PURCHASE_DATE: "dates.purchase",
        DimensionField.CREATION_DATE: "dates.creation",
        DimensionField.ACQUISITION_TYPE: "acquisition.type",
        DimensionField.ACQUISITION_SUB_TYPE: "acquisition.sub_type",
        DimensionField.ACQUISITION_METHOD: "acquisition.method",
        DimensionField.ACQUISITION_SUB_METHOD: "acquisition.sub_method",
        DimensionField.ITEM_NAME: "item.name",
        DimensionField.ITEM_DESCRIPTION: "item.description",
        DimensionField.PURCHASE_ORDER_NUMBER: "purchase_order_number",
        DimensionField.REQUISITION_NUMBER: "requisition_number",
        DimensionField.LPA_NUMBER: "lpa_number",
        DimensionField.SUPPLIER_ZIP: "supplier.zip_code",
        DimensionField.CLASSIFICATION: "classification.unspsc.segment.title",
        DimensionField.CLASSIFICATION_FAMILY: "classification.unspsc.family.title",
        DimensionField.CLASSIFICATION_CLASS: "classification.unspsc.class.title",
        DimensionField.CLASSIFICATION_COMMODITY: "classification.unspsc.commodity.title",
        DimensionField.CAL_CARD: "cal_card",
    }

    NULLABLE_METRICS = {MetricField.SPENDING, MetricField.QUANTITY, MetricField.UNIT_PRICE}

    @classmethod
    def get_mongo_field(cls, field) -> str:
        """Convert semantic field to MongoDB path."""
        if isinstance(field, MetricField) and field in cls.METRIC_MAPPINGS:
            return cls.METRIC_MAPPINGS[field]
        if isinstance(field, DimensionField) and field in cls.DIMENSION_MAPPINGS:
            return cls.DIMENSION_MAPPINGS[field]
        if isinstance(field, str):
            for metric_key, metric_value in cls.METRIC_MAPPINGS.items():
                if field == metric_key.value:
                    return metric_value
            for dim_key, dim_value in cls.DIMENSION_MAPPINGS.items():
                if field == dim_key.value:
                    return dim_value
        raise ValueError(f"Unknown field: {field}")

    @classmethod
    def needs_null_handling(cls, field: MetricField) -> bool:
        """Check if field needs $ifNull wrapper."""
        if isinstance(field, MetricField):
            return field in cls.NULLABLE_METRICS
        if isinstance(field, str):
            return any(field == metric.value for metric in cls.NULLABLE_METRICS)
        return False
