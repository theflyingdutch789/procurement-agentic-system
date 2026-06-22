# MongoDB Query Examples (Questions -> MQL)

Use these examples to test the dataset directly in MongoDB.

Setup:
```
use government_procurement
```

## Basics

1) Q: How many purchase order line items are there?
```javascript
db.purchase_orders.countDocuments({})
```

2) Q: What is the total spending overall?
```javascript
db.purchase_orders.aggregate([
  { $group: { _id: null, total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } } } },
  { $project: { _id: 0, total_spending: 1 } }
])
```

3) Q: Total spending in calendar year 2014 (by creation date)?
```javascript
db.purchase_orders.aggregate([
  {
    $match: {
      "dates.creation": {
        $gte: ISODate("2014-01-01T00:00:00Z"),
        $lt: ISODate("2015-01-01T00:00:00Z")
      }
    }
  },
  { $group: { _id: null, total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } } } },
  { $project: { _id: 0, total_spending: 1 } }
])
```

4) Q: Spending by fiscal year start?
```javascript
db.purchase_orders.aggregate([
  { $group: { _id: "$dates.fiscal_year_start", total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } } } },
  { $sort: { _id: 1 } }
])
```

## Rankings

5) Q: Top 5 departments by total spending?
```javascript
db.purchase_orders.aggregate([
  { $group: { _id: "$department.normalized_name", total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } } } },
  { $sort: { total_spending: -1 } },
  { $limit: 5 }
])
```

6) Q: Top 10 suppliers by total spending?
```javascript
db.purchase_orders.aggregate([
  { $group: { _id: "$supplier.name", total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } } } },
  { $sort: { total_spending: -1 } },
  { $limit: 10 }
])
```

7) Q: Top 5 line items by total price (no grouping)?
```javascript
db.purchase_orders.find(
  { "item.total_price": { $ne: null } },
  { purchase_order_number: 1, "supplier.name": 1, "item.name": 1, "item.total_price": 1, _id: 0 }
).sort({ "item.total_price": -1 }).limit(5)
```

8) Q: Top 5 purchase orders by total spending (grouped by PO)?
```javascript
db.purchase_orders.aggregate([
  {
    $group: {
      _id: "$purchase_order_number",
      total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } },
      line_items: { $sum: 1 }
    }
  },
  { $sort: { total_spending: -1 } },
  { $limit: 5 }
])
```

## Averages and Counts

9) Q: Average unit price by acquisition type?
```javascript
db.purchase_orders.aggregate([
  { $group: { _id: "$acquisition.type", avg_unit_price: { $avg: "$item.unit_price" } } },
  { $sort: { avg_unit_price: -1 } }
])
```

10) Q: Count of purchase orders by acquisition method?
```javascript
db.purchase_orders.aggregate([
  { $group: { _id: "$acquisition.method", order_count: { $sum: 1 } } },
  { $sort: { order_count: -1 } }
])
```

11) Q: IT vs NON-IT spending comparison?
```javascript
db.purchase_orders.aggregate([
  { $match: { "acquisition.type": { $in: ["IT Goods", "IT Services", "NON-IT Goods", "NON-IT Services"] } } },
  { $group: { _id: "$acquisition.type", total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } } } },
  { $sort: { total_spending: -1 } }
])
```

12) Q: How many CalCard purchases in fiscal year 2014?
```javascript
db.purchase_orders.aggregate([
  { $match: { cal_card: true, "dates.fiscal_year_start": 2014 } },
  { $count: "cal_card_orders" }
])
```

## Filters and Search

13) Q: Top 5 suppliers that are Small Business?
```javascript
db.purchase_orders.aggregate([
  { $match: { "supplier.qualifications": "Small Business" } },
  { $group: { _id: "$supplier.name", total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } } } },
  { $sort: { total_spending: -1 } },
  { $limit: 5 }
])
```

14) Q: Spending by UNSPSC segment?
```javascript
db.purchase_orders.aggregate([
  { $group: { _id: "$classification.unspsc.segment.title", total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } } } },
  { $sort: { total_spending: -1 } },
  { $limit: 10 }
])
```

15) Q: Purchases over $100k from suppliers in ZIP 94105?
```javascript
db.purchase_orders.find(
  { "item.total_price": { $gte: 100000 }, "supplier.zip_code": "94105" },
  { purchase_order_number: 1, "supplier.name": 1, "item.total_price": 1, _id: 0 }
).sort({ "item.total_price": -1 }).limit(10)
```

16) Q: Text search for "software" in descriptions and names?
```javascript
db.purchase_orders.aggregate([
  { $match: { $text: { $search: "software" } } },
  { $project: { score: { $meta: "textScore" }, "item.description": 1, "supplier.name": 1, _id: 0 } },
  { $sort: { score: -1 } },
  { $limit: 5 }
])
```

17) Q: Show negative total_price line items (returns/credits)?
```javascript
db.purchase_orders.find(
  { "item.total_price": { $lt: 0 } },
  { purchase_order_number: 1, "item.total_price": 1, _id: 0 }
).limit(10)
```

## Time Series

18) Q: Spending by quarter (based on creation date)?
```javascript
db.purchase_orders.aggregate([
  {
    $project: {
      year: { $year: "$dates.creation" },
      quarter: { $ceil: { $divide: [{ $month: "$dates.creation" }, 3] } },
      amount: { $ifNull: ["$item.total_price", 0] }
    }
  },
  {
    $group: {
      _id: { year: "$year", quarter: "$quarter" },
      total_spending: { $sum: "$amount" }
    }
  },
  { $sort: { "_id.year": 1, "_id.quarter": 1 } }
])
```

## Geo Query (if geospatial index is enabled)

19) Q: Purchases from suppliers within 25 miles of Sacramento?
```javascript
db.purchase_orders.aggregate([
  {
    $geoNear: {
      near: { type: "Point", coordinates: [-121.4944, 38.5816] },
      distanceField: "distance_meters",
      maxDistance: 40233,
      spherical: true
    }
  },
  { $limit: 5 },
  { $project: { purchase_order_number: 1, "supplier.name": 1, distance_meters: 1, _id: 0 } }
])
```

## Advanced Analytics

20) Q: Top 5 departments by YoY growth rate from FY2013 to FY2014?
```javascript
db.purchase_orders.aggregate([
  {
    $group: {
      _id: "$department.normalized_name",
      spend_2013: {
        $sum: {
          $cond: [
            { $eq: ["$dates.fiscal_year_start", 2013] },
            { $ifNull: ["$item.total_price", 0] },
            0
          ]
        }
      },
      spend_2014: {
        $sum: {
          $cond: [
            { $eq: ["$dates.fiscal_year_start", 2014] },
            { $ifNull: ["$item.total_price", 0] },
            0
          ]
        }
      }
    }
  },
  {
    $project: {
      spend_2013: 1,
      spend_2014: 1,
      yoy_growth: {
        $cond: [
          { $gt: ["$spend_2013", 0] },
          { $divide: [{ $subtract: ["$spend_2014", "$spend_2013"] }, "$spend_2013"] },
          null
        ]
      }
    }
  },
  { $sort: { yoy_growth: -1 } },
  { $limit: 5 }
])
```

## IT Spend

21) Q: Total IT spending by fiscal year?
```javascript
db.purchase_orders.aggregate([
  { $match: { "acquisition.type": { $in: ["IT Goods", "IT Services"] } } },
  { $group: { _id: "$dates.fiscal_year_start", total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } } } },
  { $sort: { _id: 1 } }
])
```

22) Q: Top 5 IT suppliers by total spending?
```javascript
db.purchase_orders.aggregate([
  { $match: { "acquisition.type": { $in: ["IT Goods", "IT Services"] } } },
  { $group: { _id: "$supplier.name", total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } } } },
  { $sort: { total_spending: -1 } },
  { $limit: 5 }
])
```

23) Q: IT vs NON-IT spending by department?
```javascript
db.purchase_orders.aggregate([
  { $match: { "acquisition.type": { $in: ["IT Goods", "IT Services", "NON-IT Goods", "NON-IT Services"] } } },
  {
    $group: {
      _id: { dept: "$department.normalized_name", type: "$acquisition.type" },
      total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } }
    }
  },
  { $sort: { "_id.dept": 1, total_spending: -1 } },
  { $limit: 20 }
])
```

24) Q: Average unit price for IT Goods vs IT Services?
```javascript
db.purchase_orders.aggregate([
  { $match: { "acquisition.type": { $in: ["IT Goods", "IT Services"] } } },
  { $group: { _id: "$acquisition.type", avg_unit_price: { $avg: "$item.unit_price" } } },
  { $sort: { avg_unit_price: -1 } }
])
```

## Supplier Diversity

25) Q: Total spending by supplier qualification (e.g., Small Business)?
```javascript
db.purchase_orders.aggregate([
  { $unwind: "$supplier.qualifications" },
  { $group: { _id: "$supplier.qualifications", total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } } } },
  { $sort: { total_spending: -1 } }
])
```

26) Q: Top 5 Small Business suppliers by spending?
```javascript
db.purchase_orders.aggregate([
  { $match: { "supplier.qualifications": "Small Business" } },
  { $group: { _id: "$supplier.name", total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } } } },
  { $sort: { total_spending: -1 } },
  { $limit: 5 }
])
```

27) Q: Diversity spend share by qualification (percentage of total)?
```javascript
db.purchase_orders.aggregate([
  { $facet: {
    totals: [
      { $group: { _id: null, grand_total: { $sum: { $ifNull: ["$item.total_price", 0] } } } }
    ],
    by_qual: [
      { $unwind: "$supplier.qualifications" },
      { $group: { _id: "$supplier.qualifications", total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } } } }
    ]
  }},
  { $unwind: "$totals" },
  { $unwind: "$by_qual" },
  {
    $project: {
      qualification: "$by_qual._id",
      total_spending: "$by_qual.total_spending",
      share: { $divide: ["$by_qual.total_spending", "$totals.grand_total"] }
    }
  },
  { $sort: { share: -1 } }
])
```

28) Q: IT spending by supplier qualification?
```javascript
db.purchase_orders.aggregate([
  { $match: { "acquisition.type": { $in: ["IT Goods", "IT Services"] } } },
  { $unwind: "$supplier.qualifications" },
  { $group: { _id: "$supplier.qualifications", total_spending: { $sum: { $ifNull: ["$item.total_price", 0] } } } },
  { $sort: { total_spending: -1 } }
])
```
