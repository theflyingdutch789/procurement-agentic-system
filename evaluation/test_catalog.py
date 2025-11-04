"""
Reference catalogue of evaluation test cases.
"""

from __future__ import annotations

from typing import List

from .models import TestCase


def load_test_cases() -> List[TestCase]:
    """Return the ordered list of evaluation test cases (easy -> ultra)."""
    return [
        # BASIC
        TestCase(
            id="basic_001",
            category="basic",
            difficulty="easy",
            question="How many total purchase order line items are in the database?",
            expected_type="count",
            description="Simple total document count.",
            ground_truth_query=[
                {"$count": "total_purchase_orders"}
            ],
        ),
        TestCase(
            id="basic_002",
            category="basic",
            difficulty="easy",
            question="What is the total spending across all fiscal years?",
            expected_type="aggregation",
            description="Sum of item.total_price.",
            ground_truth_query=[
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": {"$ifNull": ["$item.total_price", 0]}},
                    }
                }
            ],
        ),
        TestCase(
            id="basic_003",
            category="basic",
            difficulty="easy",
            question="List each fiscal year present in the dataset.",
            expected_type="list",
            description="Distinct fiscal years.",
            ground_truth_query=[
                {"$match": {"dates.fiscal_year": {"$ne": None}}},
                {"$group": {"_id": "$dates.fiscal_year"}},
                {"$sort": {"_id": 1}},
            ],
        ),
        # INTERMEDIATE
        TestCase(
            id="intermediate_001",
            category="intermediate",
            difficulty="medium",
            question="What is the total spending for each fiscal year?",
            expected_type="aggregation",
            description="Group by fiscal year.",
            ground_truth_query=[
                {
                    "$group": {
                        "_id": "$dates.fiscal_year",
                        "total_spending": {
                            "$sum": {"$ifNull": ["$item.total_price", 0]}
                        },
                    }
                },
                {"$sort": {"_id": 1}},
            ],
        ),
        TestCase(
            id="intermediate_002",
            category="intermediate",
            difficulty="medium",
            question="Which department spent the most overall?",
            expected_type="aggregation",
            description="Top department by spend.",
            ground_truth_query=[
                {"$match": {"department.normalized_name": {"$ne": None}}},
                {
                    "$group": {
                        "_id": "$department.normalized_name",
                        "total_spending": {
                            "$sum": {"$ifNull": ["$item.total_price", 0]}
                        },
                    }
                },
                {"$sort": {"total_spending": -1}},
                {"$limit": 1},
            ],
        ),
        TestCase(
            id="intermediate_003",
            category="intermediate",
            difficulty="medium",
            question="How many transactions used CalCard?",
            expected_type="count",
            description="CalCard boolean filter.",
            ground_truth_query=[
                {"$match": {"cal_card": True}},
                {"$count": "total"},
            ],
        ),
        TestCase(
            id="intermediate_004",
            category="intermediate",
            difficulty="medium",
            question="What are the top 5 suppliers by total spending?",
            expected_type="list",
            description="Supplier ranking.",
            ground_truth_query=[
                {"$match": {"supplier.name": {"$ne": None}}},
                {
                    "$group": {
                        "_id": "$supplier.name",
                        "total_spending": {
                            "$sum": {"$ifNull": ["$item.total_price", 0]}
                        },
                        "transaction_count": {"$sum": 1},
                    }
                },
                {"$sort": {"total_spending": -1}},
                {"$limit": 5},
            ],
        ),
        # ADVANCED
        TestCase(
            id="advanced_001",
            category="advanced",
            difficulty="hard",
            question="For fiscal year 2013-2014, what percentage of spending went to the top 10 suppliers?",
            expected_type="aggregation",
            description="Facet + percentage calculation.",
            ground_truth_query=[
                {"$match": {"dates.fiscal_year": "2013-2014"}},
                {
                    "$facet": {
                        "totals": [
                            {
                                "$group": {
                                    "_id": None,
                                    "grand_total": {
                                        "$sum": {"$ifNull": ["$item.total_price", 0]}
                                    },
                                }
                            }
                        ],
                        "top10": [
                            {
                                "$group": {
                                    "_id": "$supplier.name",
                                    "supplier_total": {
                                        "$sum": {"$ifNull": ["$item.total_price", 0]}
                                    },
                                }
                            },
                            {"$sort": {"supplier_total": -1}},
                            {"$limit": 10},
                            {
                                "$group": {
                                    "_id": None,
                                    "top10_total": {"$sum": "$supplier_total"},
                                }
                            },
                        ],
                    }
                },
                {
                    "$project": {
                        "grand_total": {"$arrayElemAt": ["$totals.grand_total", 0]},
                        "top10_total": {"$arrayElemAt": ["$top10.top10_total", 0]},
                        "top10_share": {
                            "$cond": [
                                {"$gt": [{"$arrayElemAt": ["$totals.grand_total", 0]}, 0]},
                                {
                                    "$divide": [
                                        {"$arrayElemAt": ["$top10.top10_total", 0]},
                                        {"$arrayElemAt": ["$totals.grand_total", 0]},
                                    ]
                                },
                                None,
                            ]
                        },
                    }
                },
            ],
            tolerance=0.02,
        ),
        TestCase(
            id="advanced_002",
            category="advanced",
            difficulty="hard",
            question="Compare spending in 2013-2014 vs 2014-2015 for the Health Care Services department.",
            expected_type="comparison",
            description="Year-over-year department comparison.",
            ground_truth_query=[
                {
                    "$match": {
                        "department.normalized_name": "Health Care Services",
                        "dates.fiscal_year": {"$in": ["2013-2014", "2014-2015"]},
                    }
                },
                {
                    "$group": {
                        "_id": "$dates.fiscal_year",
                        "total_spending": {
                            "$sum": {"$ifNull": ["$item.total_price", 0]}
                        },
                    }
                },
                {"$sort": {"_id": 1}},
            ],
        ),
        TestCase(
            id="advanced_003",
            category="advanced",
            difficulty="hard",
            question="Find purchases over $1M in fiscal year 2014-2015, grouped by supplier with transaction counts.",
            expected_type="aggregation",
            description="High-value purchase breakdown.",
            ground_truth_query=[
                {
                    "$match": {
                        "dates.fiscal_year": "2014-2015",
                        "item.total_price": {"$gt": 1_000_000},
                    }
                },
                {
                    "$group": {
                        "_id": "$supplier.name",
                        "total_spending": {
                            "$sum": {"$ifNull": ["$item.total_price", 0]}
                        },
                        "transaction_count": {"$sum": 1},
                    }
                },
                {"$sort": {"total_spending": -1}},
                {"$limit": 20},
            ],
        ),
        TestCase(
            id="advanced_004",
            category="advanced",
            difficulty="hard",
            question="What is the average transaction value for IT Goods versus IT Services in fiscal year 2013-2014?",
            expected_type="aggregation",
            description="Conditional aggregation by acquisition type.",
            ground_truth_query=[
                {
                    "$match": {
                        "dates.fiscal_year": "2013-2014",
                        "acquisition.type": {"$in": ["IT Goods", "IT Services"]},
                    }
                },
                {
                    "$group": {
                        "_id": "$acquisition.type",
                        "avg_value": {"$avg": {"$ifNull": ["$item.total_price", 0]}},
                        "transaction_count": {"$sum": 1},
                    }
                },
            ],
        ),
        TestCase(
            id="advanced_005",
            category="advanced",
            difficulty="hard",
            question="Which IT Services suppliers in 2013-2014 had the highest average order value (min 25 transactions)?",
            expected_type="aggregation",
            description="Average order value with threshold.",
            ground_truth_query=[
                {
                    "$match": {
                        "dates.fiscal_year": "2013-2014",
                        "acquisition.type": "IT Services",
                        "supplier.name": {"$ne": None},
                    }
                },
                {
                    "$group": {
                        "_id": "$supplier.name",
                        "transaction_count": {"$sum": 1},
                        "total_spending": {
                            "$sum": {"$ifNull": ["$item.total_price", 0]}
                        },
                        "avg_order_value": {
                            "$avg": {"$ifNull": ["$item.total_price", 0]}
                        },
                    }
                },
                {"$match": {"transaction_count": {"$gte": 25}}},
                {"$sort": {"avg_order_value": -1}},
                {"$limit": 10},
            ],
        ),
        TestCase(
            id="advanced_006",
            category="advanced",
            difficulty="hard",
            question="Which departments grew spending by at least 15% between fiscal years 2012-2013 and 2014-2015?",
            expected_type="aggregation",
            description="Growth calculation with percentage change.",
            ground_truth_query=[
                {"$match": {"department.normalized_name": {"$ne": None}}},
                {
                    "$group": {
                        "_id": {
                            "department": "$department.normalized_name",
                            "fiscal_year": "$dates.fiscal_year",
                        },
                        "total_spending": {
                            "$sum": {"$ifNull": ["$item.total_price", 0]}
                        },
                    }
                },
                {
                    "$group": {
                        "_id": "$_id.department",
                        "first_year_spending": {
                            "$sum": {
                                "$cond": [
                                    {"$eq": ["$_id.fiscal_year", "2012-2013"]},
                                    "$total_spending",
                                    0,
                                ]
                            }
                        },
                        "last_year_spending": {
                            "$sum": {
                                "$cond": [
                                    {"$eq": ["$_id.fiscal_year", "2014-2015"]},
                                    "$total_spending",
                                    0,
                                ]
                            }
                        },
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "department": "$_id",
                        "first_year_spending": 1,
                        "last_year_spending": 1,
                        "growth_percent": {
                            "$cond": [
                                {"$gt": ["$first_year_spending", 0]},
                                {
                                    "$multiply": [
                                        {
                                            "$divide": [
                                                {
                                                    "$subtract": [
                                                        "$last_year_spending",
                                                        "$first_year_spending",
                                                    ]
                                                },
                                                "$first_year_spending",
                                            ]
                                        },
                                        100,
                                    ]
                                },
                                None,
                            ]
                        },
                    }
                },
                {"$match": {"growth_percent": {"$gte": 15}}},
                {"$sort": {"growth_percent": -1}},
                {"$limit": 10},
            ],
            tolerance=0.05,
        ),
        # EXPERT
        TestCase(
            id="expert_001",
            category="expert",
            difficulty="hard",
            question="For each acquisition type in fiscal year 2013-2014, return total spend, line count, and avg transaction value.",
            expected_type="aggregation",
            description="Multi-metric aggregation with sort.",
            ground_truth_query=[
                {"$match": {"dates.fiscal_year": "2013-2014"}},
                {
                    "$group": {
                        "_id": "$acquisition.type",
                        "total_spending": {
                            "$sum": {"$ifNull": ["$item.total_price", 0]}
                        },
                        "transaction_count": {"$sum": 1},
                        "avg_transaction_value": {
                            "$avg": {"$ifNull": ["$item.total_price", 0]}
                        },
                    }
                },
                {"$sort": {"total_spending": -1}},
            ],
        ),
        TestCase(
            id="expert_002",
            category="expert",
            difficulty="hard",
            question="Which suppliers have the largest net refunds (negative spend)? Return top 5.",
            expected_type="list",
            description="Negative spend detection.",
            ground_truth_query=[
                {
                    "$group": {
                        "_id": "$supplier.name",
                        "total_spending": {
                            "$sum": {"$ifNull": ["$item.total_price", 0]}
                        },
                        "transaction_count": {"$sum": 1},
                    }
                },
                {"$match": {"total_spending": {"$lt": 0}}},
                {"$sort": {"total_spending": 1}},
                {"$limit": 5},
            ],
        ),
        TestCase(
            id="expert_003",
            category="expert",
            difficulty="hard",
            question="Among departments with ≥500 CalCard transactions, list spend totals and average ticket size.",
            expected_type="aggregation",
            description="CalCard heavy usage analysis.",
            ground_truth_query=[
                {"$match": {"cal_card": True}},
                {
                    "$group": {
                        "_id": "$department.normalized_name",
                        "transaction_count": {"$sum": 1},
                        "total_spending": {
                            "$sum": {"$ifNull": ["$item.total_price", 0]}
                        },
                    }
                },
                {"$match": {"transaction_count": {"$gte": 500}}},
                {
                    "$addFields": {
                        "avg_transaction_value": {
                            "$cond": [
                                {"$gt": ["$transaction_count", 0]},
                                {
                                    "$divide": [
                                        "$total_spending",
                                        "$transaction_count",
                                    ]
                                },
                                None,
                            ]
                        }
                    }
                },
                {"$sort": {"transaction_count": -1}},
            ],
        ),
        # INSIGHT
        TestCase(
            id="insight_001",
            category="insight",
            difficulty="medium",
            question="Describe the overall spending trend and identify the highest and lowest fiscal years.",
            expected_type="semantic",
            description="Narrative trend analysis.",
            ground_truth_query=[
                {
                    "$group": {
                        "_id": "$dates.fiscal_year",
                        "total_spending": {
                            "$sum": {"$ifNull": ["$item.total_price", 0]}
                        },
                    }
                },
                {"$sort": {"total_spending": -1}},
            ],
        ),
        TestCase(
            id="insight_002",
            category="insight",
            difficulty="hard",
            question="Explain how CalCard usage compares to non-CalCard transactions across fiscal years in volume and spend.",
            expected_type="semantic",
            description="Payment method interpretation across years.",
            ground_truth_query=[
                {
                    "$group": {
                        "_id": {
                            "fiscal_year": "$dates.fiscal_year",
                            "cal_card": "$cal_card",
                        },
                        "total_spending": {
                            "$sum": {"$ifNull": ["$item.total_price", 0]}
                        },
                        "transaction_count": {"$sum": 1},
                    }
                },
                {"$sort": {"_id.fiscal_year": 1, "_id.cal_card": -1}},
            ],
        ),
        # ULTRA
        TestCase(
            id="ultra_001",
            category="ultra",
            difficulty="very_hard",
            question="Which departments increased spending by at least 25% in both 2013-2014 and 2014-2015 compared to the prior fiscal year, and what was the cumulative growth from 2012-2013 to 2014-2015?",
            expected_type="aggregation",
            description="Multi-year momentum analysis with chained growth thresholds and cumulative percentage change.",
            ground_truth_query=[
                {
                    "$match": {
                        "department.normalized_name": {"$ne": None},
                        "dates.fiscal_year": {
                            "$in": ["2012-2013", "2013-2014", "2014-2015"]
                        },
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "department": "$department.normalized_name",
                            "fiscal_year": "$dates.fiscal_year",
                        },
                        "total_spending": {
                            "$sum": {"$ifNull": ["$item.total_price", 0]}
                        },
                    }
                },
                {
                    "$group": {
                        "_id": "$_id.department",
                        "year_data": {
                            "$push": {
                                "year": "$_id.fiscal_year",
                                "total_spending": "$total_spending",
                            }
                        },
                    }
                },
                {
                    "$addFields": {
                        "totals_by_year": {
                            "$reduce": {
                                "input": "$year_data",
                                "initialValue": {"y2012": 0, "y2013": 0, "y2014": 0},
                                "in": {
                                    "y2012": {
                                        "$cond": [
                                            {"$eq": ["$$this.year", "2012-2013"]},
                                            "$$this.total_spending",
                                            "$$value.y2012",
                                        ]
                                    },
                                    "y2013": {
                                        "$cond": [
                                            {"$eq": ["$$this.year", "2013-2014"]},
                                            "$$this.total_spending",
                                            "$$value.y2013",
                                        ]
                                    },
                                    "y2014": {
                                        "$cond": [
                                            {"$eq": ["$$this.year", "2014-2015"]},
                                            "$$this.total_spending",
                                            "$$value.y2014",
                                        ]
                                    },
                                },
                            }
                        }
                    }
                },
                {
                    "$addFields": {
                        "spend_2012": "$totals_by_year.y2012",
                        "spend_2013": "$totals_by_year.y2013",
                        "spend_2014": "$totals_by_year.y2014",
                    }
                },
                {
                    "$addFields": {
                        "yoy_growth_2013": {
                            "$cond": [
                                {"$gt": ["$spend_2012", 0]},
                                {
                                    "$divide": [
                                        {"$subtract": ["$spend_2013", "$spend_2012"]},
                                        "$spend_2012",
                                    ]
                                },
                                None,
                            ]
                        },
                        "yoy_growth_2014": {
                            "$cond": [
                                {"$gt": ["$spend_2013", 0]},
                                {
                                    "$divide": [
                                        {"$subtract": ["$spend_2014", "$spend_2013"]},
                                        "$spend_2013",
                                    ]
                                },
                                None,
                            ]
                        },
                        "cumulative_growth": {
                            "$cond": [
                                {"$gt": ["$spend_2012", 0]},
                                {
                                    "$divide": [
                                        {"$subtract": ["$spend_2014", "$spend_2012"]},
                                        "$spend_2012",
                                    ]
                                },
                                None,
                            ]
                        },
                    }
                },
                {
                    "$match": {
                        "spend_2012": {"$gt": 0},
                        "spend_2013": {"$gt": 0},
                        "spend_2014": {"$gt": 0},
                        "yoy_growth_2013": {"$gte": 0.25},
                        "yoy_growth_2014": {"$gte": 0.25},
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "department": "$_id",
                        "spend_2012": 1,
                        "spend_2013": 1,
                        "spend_2014": 1,
                        "yoy_growth_2013": 1,
                        "yoy_growth_2014": 1,
                        "cumulative_growth": 1,
                    }
                },
                {"$sort": {"cumulative_growth": -1}},
                {"$limit": 10},
            ],
            tolerance=0.05,
            tags=["multi_year", "momentum"],
        ),
        TestCase(
            id="ultra_002",
            category="ultra",
            difficulty="very_hard",
            question="For IT Services purchases in fiscal year 2014-2015, what are the average, median, and 90th percentile transaction values, and how many transactions contributed? Include the median-to-mean ratio.",
            expected_type="aggregation",
            description="Distribution analysis using percentile aggregations with thresholds.",
            ground_truth_query=[
                {
                    "$match": {
                        "dates.fiscal_year": "2014-2015",
                        "acquisition.type": "IT Services",
                        "item.total_price": {"$ne": None},
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "transaction_count": {"$sum": 1},
                        "avg_value": {"$avg": "$item.total_price"},
                        "percentiles": {
                            "$percentile": {
                                "input": "$item.total_price",
                                "p": [0.5, 0.9],
                                "method": "approximate",
                            }
                        },
                        "total_spending": {"$sum": "$item.total_price"},
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "transaction_count": 1,
                        "avg_value": 1,
                        "median_value": {"$arrayElemAt": ["$percentiles", 0]},
                        "p90_value": {"$arrayElemAt": ["$percentiles", 1]},
                        "total_spending": 1,
                        "median_to_mean_ratio": {
                            "$cond": [
                                {"$gt": ["$avg_value", 0]},
                                {
                                    "$divide": [
                                        {"$arrayElemAt": ["$percentiles", 0]},
                                        "$avg_value",
                                    ]
                                },
                                None,
                            ]
                        },
                    }
                },
                {"$match": {"transaction_count": {"$gte": 500}}},
            ],
            tolerance=0.05,
            tags=["percentile", "distribution"],
        ),
        TestCase(
            id="ultra_003",
            category="ultra",
            difficulty="very_hard",
            question="Which suppliers have the highest ratio of CalCard spending to non-CalCard spending, considering only suppliers with at least $5M total spending and 200 transactions?",
            expected_type="aggregation",
            description="Complex ratio analysis requiring conditional sums and threshold filtering.",
            ground_truth_query=[
                {
                    "$group": {
                        "_id": "$supplier.name",
                        "total_spending": {
                            "$sum": {"$ifNull": ["$item.total_price", 0]}
                        },
                        "transaction_count": {"$sum": 1},
                        "calcard_spending": {
                            "$sum": {
                                "$cond": [
                                    {"$eq": ["$cal_card", True]},
                                    {"$ifNull": ["$item.total_price", 0]},
                                    0,
                                ]
                            }
                        },
                        "non_calcard_spending": {
                            "$sum": {
                                "$cond": [
                                    {"$eq": ["$cal_card", True]},
                                    0,
                                    {"$ifNull": ["$item.total_price", 0]},
                                ]
                            }
                        },
                    }
                },
                {
                    "$match": {
                        "_id": {"$ne": None},
                        "total_spending": {"$gte": 5_000_000},
                        "transaction_count": {"$gte": 200},
                        "non_calcard_spending": {"$gt": 0},
                    }
                },
                {
                    "$addFields": {
                        "calcard_to_non_ratio": {
                            "$divide": ["$calcard_spending", "$non_calcard_spending"]
                        },
                        "calcard_share": {
                            "$cond": [
                                {"$gt": ["$total_spending", 0]},
                                {
                                    "$divide": [
                                        "$calcard_spending",
                                        "$total_spending",
                                    ]
                                },
                                None,
                            ]
                        },
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "transaction_count": 1,
                        "total_spending": 1,
                        "calcard_spending": 1,
                        "non_calcard_spending": 1,
                        "calcard_to_non_ratio": 1,
                        "calcard_share": 1,
                    }
                },
                {"$sort": {"calcard_to_non_ratio": -1}},
                {"$limit": 10},
            ],
            tolerance=0.05,
            tags=["calcard", "ratio"],
        ),
    ]
