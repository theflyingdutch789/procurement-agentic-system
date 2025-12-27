# MongoDB for SQL Developers - Crash Course

## The Mental Shift

| SQL | MongoDB |
|-----|---------|
| Database | Database |
| Table | Collection |
| Row | Document |
| Column | Field |
| JOIN | Embedded documents or $lookup |
| WHERE | $match |
| GROUP BY | $group |
| ORDER BY | $sort |
| LIMIT | $limit |
| SELECT | $project |

---

## Connect to MongoDB

```bash
docker exec -it procurement_mongodb mongosh -u admin -p changeme_secure_password government_procurement
```

You're now in the `government_procurement` database.

---

## Part 1: Basic Queries (SQL SELECT → MongoDB find)

### See all collections (like SHOW TABLES)
```javascript
show collections
```

### Count documents (SELECT COUNT(*))
```sql
-- SQL
SELECT COUNT(*) FROM purchase_orders;
```
```javascript
// MongoDB
db.purchase_orders.countDocuments()
```

### Get one document (SELECT * ... LIMIT 1)
```sql
-- SQL
SELECT * FROM purchase_orders LIMIT 1;
```
```javascript
// MongoDB
db.purchase_orders.findOne()
```

### Get multiple documents (SELECT * ... LIMIT 5)
```sql
-- SQL
SELECT * FROM purchase_orders LIMIT 5;
```
```javascript
// MongoDB
db.purchase_orders.find().limit(5)
```

### Pretty print results
```javascript
db.purchase_orders.find().limit(5).pretty()
```

---

## Part 2: Filtering (SQL WHERE → MongoDB find with filter)

### Simple equality
```sql
-- SQL
SELECT * FROM purchase_orders WHERE fiscal_year = '2013-2014';
```
```javascript
// MongoDB - Note: nested field uses dot notation!
db.purchase_orders.find({ "dates.fiscal_year": "2013-2014" }).limit(5)
```

### Greater than
```sql
-- SQL
SELECT * FROM purchase_orders WHERE total_price > 100000;
```
```javascript
// MongoDB
db.purchase_orders.find({ "item.total_price": { $gt: 100000 } }).limit(5)
```

### Multiple conditions (AND)
```sql
-- SQL
SELECT * FROM purchase_orders
WHERE fiscal_year = '2013-2014' AND total_price > 10000;
```
```javascript
// MongoDB
db.purchase_orders.find({
  "dates.fiscal_year": "2013-2014",
  "item.total_price": { $gt: 10000 }
}).limit(5)
```

### OR condition
```sql
-- SQL
SELECT * FROM purchase_orders
WHERE fiscal_year = '2013-2014' OR fiscal_year = '2014-2015';
```
```javascript
// MongoDB
db.purchase_orders.find({
  $or: [
    { "dates.fiscal_year": "2013-2014" },
    { "dates.fiscal_year": "2014-2015" }
  ]
}).limit(5)
```

### IN clause
```sql
-- SQL
SELECT * FROM purchase_orders
WHERE acquisition_type IN ('IT Goods', 'IT Services');
```
```javascript
// MongoDB
db.purchase_orders.find({
  "acquisition.type": { $in: ["IT Goods", "IT Services"] }
}).limit(5)
```

### LIKE (pattern matching)
```sql
-- SQL
SELECT * FROM purchase_orders WHERE supplier_name LIKE '%Microsoft%';
```
```javascript
// MongoDB (regex)
db.purchase_orders.find({
  "supplier.name": /Microsoft/i  // i = case insensitive
}).limit(5)
```

### IS NOT NULL
```sql
-- SQL
SELECT * FROM purchase_orders WHERE supplier_name IS NOT NULL;
```
```javascript
// MongoDB
db.purchase_orders.find({
  "supplier.name": { $ne: null }
}).limit(5)
```

---

## Part 3: Selecting Specific Fields (SQL SELECT columns → MongoDB projection)

```sql
-- SQL
SELECT department_name, supplier_name, total_price
FROM purchase_orders LIMIT 5;
```
```javascript
// MongoDB - 1 means include, 0 means exclude
db.purchase_orders.find(
  {},  // empty filter = all documents
  {
    "department.name": 1,
    "supplier.name": 1,
    "item.total_price": 1,
    _id: 0  // exclude _id
  }
).limit(5)
```

---

## Part 4: Sorting (SQL ORDER BY → MongoDB sort)

```sql
-- SQL
SELECT * FROM purchase_orders ORDER BY total_price DESC LIMIT 10;
```
```javascript
// MongoDB - 1 = ASC, -1 = DESC
db.purchase_orders.find()
  .sort({ "item.total_price": -1 })
  .limit(10)
```

### Multiple sort fields
```sql
-- SQL
SELECT * FROM purchase_orders
ORDER BY fiscal_year ASC, total_price DESC LIMIT 10;
```
```javascript
// MongoDB
db.purchase_orders.find()
  .sort({ "dates.fiscal_year": 1, "item.total_price": -1 })
  .limit(10)
```

---

## Part 5: Aggregation Pipeline (SQL GROUP BY → MongoDB aggregate)

This is where MongoDB shines! Aggregation pipelines process data in stages.

### Basic structure
```javascript
db.collection.aggregate([
  { $stage1: { ... } },
  { $stage2: { ... } },
  { $stage3: { ... } }
])
```

Data flows through each stage like a pipeline:
```
Documents → $match → $group → $sort → $limit → Results
```

---

### Simple COUNT with GROUP BY
```sql
-- SQL
SELECT fiscal_year, COUNT(*) as count
FROM purchase_orders
GROUP BY fiscal_year
ORDER BY fiscal_year;
```
```javascript
// MongoDB
db.purchase_orders.aggregate([
  { $group: {
      _id: "$dates.fiscal_year",  // GROUP BY field ($ means "value of field")
      count: { $sum: 1 }          // COUNT(*)
  }},
  { $sort: { _id: 1 } }           // ORDER BY
])
```

### SUM with GROUP BY
```sql
-- SQL
SELECT fiscal_year, SUM(total_price) as total_spending
FROM purchase_orders
GROUP BY fiscal_year
ORDER BY fiscal_year;
```
```javascript
// MongoDB
db.purchase_orders.aggregate([
  { $group: {
      _id: "$dates.fiscal_year",
      total_spending: { $sum: "$item.total_price" }
  }},
  { $sort: { _id: 1 } }
])
```

### AVG with GROUP BY
```sql
-- SQL
SELECT department_name, AVG(total_price) as avg_order
FROM purchase_orders
GROUP BY department_name
ORDER BY avg_order DESC
LIMIT 10;
```
```javascript
// MongoDB
db.purchase_orders.aggregate([
  { $group: {
      _id: "$department.normalized_name",
      avg_order: { $avg: "$item.total_price" }
  }},
  { $sort: { avg_order: -1 } },
  { $limit: 10 }
])
```

### Multiple aggregations
```sql
-- SQL
SELECT
  department_name,
  COUNT(*) as order_count,
  SUM(total_price) as total_spending,
  AVG(total_price) as avg_order
FROM purchase_orders
GROUP BY department_name
ORDER BY total_spending DESC
LIMIT 5;
```
```javascript
// MongoDB
db.purchase_orders.aggregate([
  { $group: {
      _id: "$department.normalized_name",
      order_count: { $sum: 1 },
      total_spending: { $sum: "$item.total_price" },
      avg_order: { $avg: "$item.total_price" }
  }},
  { $sort: { total_spending: -1 } },
  { $limit: 5 }
])
```

---

### Filter THEN Group (WHERE + GROUP BY → $match + $group)
```sql
-- SQL
SELECT supplier_name, SUM(total_price) as total
FROM purchase_orders
WHERE fiscal_year = '2014-2015'
GROUP BY supplier_name
ORDER BY total DESC
LIMIT 5;
```
```javascript
// MongoDB - $match comes BEFORE $group
db.purchase_orders.aggregate([
  { $match: { "dates.fiscal_year": "2014-2015" } },  // WHERE
  { $group: {
      _id: "$supplier.name",
      total: { $sum: "$item.total_price" }
  }},
  { $sort: { total: -1 } },
  { $limit: 5 }
])
```

---

### HAVING clause (filter after grouping)
```sql
-- SQL
SELECT supplier_name, COUNT(*) as order_count
FROM purchase_orders
GROUP BY supplier_name
HAVING COUNT(*) > 1000
ORDER BY order_count DESC;
```
```javascript
// MongoDB - use $match AFTER $group for HAVING
db.purchase_orders.aggregate([
  { $group: {
      _id: "$supplier.name",
      order_count: { $sum: 1 }
  }},
  { $match: { order_count: { $gt: 1000 } } },  // HAVING
  { $sort: { order_count: -1 } }
])
```

---

## Part 6: Aggregation Operators Cheatsheet

### Grouping Operators
| SQL | MongoDB |
|-----|---------|
| COUNT(*) | { $sum: 1 } |
| SUM(field) | { $sum: "$field" } |
| AVG(field) | { $avg: "$field" } |
| MIN(field) | { $min: "$field" } |
| MAX(field) | { $max: "$field" } |
| COUNT(DISTINCT field) | { $addToSet: "$field" } then $size |

### Comparison Operators (in $match)
| SQL | MongoDB |
|-----|---------|
| = | { field: value } or { $eq: value } |
| != | { $ne: value } |
| > | { $gt: value } |
| >= | { $gte: value } |
| < | { $lt: value } |
| <= | { $lte: value } |
| IN | { $in: [values] } |
| NOT IN | { $nin: [values] } |
| BETWEEN | { $gte: low, $lte: high } |

---

## Part 7: Practice Exercises (Do All of These!)

### Exercise 1: Basic Count
**Task:** Count orders where CalCard was used
```javascript
// Your turn! (cal_card is a boolean field)
db.purchase_orders.countDocuments({ cal_card: true })
```

### Exercise 2: Filtering
**Task:** Find 5 orders from "Corrections and Rehabilitation" department
```javascript
db.purchase_orders.find({
  "department.normalized_name": "CORRECTIONS AND REHABILITATION"
}).limit(5)
```

### Exercise 3: Simple Aggregation
**Task:** Get total spending for fiscal year 2014-2015
```javascript
db.purchase_orders.aggregate([
  { $match: { "dates.fiscal_year": "2014-2015" } },
  { $group: { _id: null, total: { $sum: "$item.total_price" } } }
])
```

### Exercise 4: Group By with Count and Sum
**Task:** For each acquisition type, get count and total spending
```javascript
db.purchase_orders.aggregate([
  { $group: {
      _id: "$acquisition.type",
      count: { $sum: 1 },
      total_spending: { $sum: "$item.total_price" }
  }},
  { $sort: { total_spending: -1 } }
])
```

### Exercise 5: Top N Query
**Task:** Find top 10 largest single orders
```javascript
db.purchase_orders.find({}, {
  "po_number": 1,
  "supplier.name": 1,
  "item.total_price": 1,
  "department.name": 1
})
.sort({ "item.total_price": -1 })
.limit(10)
```

### Exercise 6: Complex Aggregation
**Task:** For each department in 2013-2014, get order count and avg order value,
show only departments with more than 500 orders, sorted by avg value
```javascript
db.purchase_orders.aggregate([
  { $match: { "dates.fiscal_year": "2013-2014" } },
  { $group: {
      _id: "$department.normalized_name",
      order_count: { $sum: 1 },
      avg_value: { $avg: "$item.total_price" }
  }},
  { $match: { order_count: { $gt: 500 } } },
  { $sort: { avg_value: -1 } }
])
```

---

## Part 8: The 6 Demo Queries You MUST Master

### Query 1: Total Count
```javascript
db.purchase_orders.countDocuments()
// Expected: 346018
```

### Query 2: Total Spending
```javascript
db.purchase_orders.aggregate([
  { $group: { _id: null, total: { $sum: "$item.total_price" } } }
])
```

### Query 3: Spending by Fiscal Year
```javascript
db.purchase_orders.aggregate([
  { $group: {
      _id: "$dates.fiscal_year",
      total: { $sum: "$item.total_price" }
  }},
  { $sort: { _id: 1 } }
])
```

### Query 4: Top 5 Departments
```javascript
db.purchase_orders.aggregate([
  { $group: {
      _id: "$department.normalized_name",
      total: { $sum: "$item.total_price" }
  }},
  { $sort: { total: -1 } },
  { $limit: 5 }
])
```

### Query 5: Top 5 Suppliers
```javascript
db.purchase_orders.aggregate([
  { $group: {
      _id: "$supplier.name",
      total: { $sum: "$item.total_price" },
      orders: { $sum: 1 }
  }},
  { $sort: { total: -1 } },
  { $limit: 5 }
])
```

### Query 6: Spending by Acquisition Type
```javascript
db.purchase_orders.aggregate([
  { $group: {
      _id: "$acquisition.type",
      total: { $sum: "$item.total_price" },
      count: { $sum: 1 }
  }},
  { $sort: { total: -1 } }
])
```

---

## Part 9: Common Mistakes to Avoid

### 1. Forgetting the $ in aggregation
```javascript
// WRONG
{ $group: { _id: "dates.fiscal_year" } }

// RIGHT - $ means "value of this field"
{ $group: { _id: "$dates.fiscal_year" } }
```

### 2. Wrong dot notation for nested fields
```javascript
// WRONG
{ $match: { fiscal_year: "2013-2014" } }

// RIGHT - use dot notation for nested fields
{ $match: { "dates.fiscal_year": "2013-2014" } }
```

### 3. Forgetting _id in $group is required
```javascript
// WRONG
{ $group: { total: { $sum: "$item.total_price" } } }

// RIGHT - _id is required (use null for no grouping)
{ $group: { _id: null, total: { $sum: "$item.total_price" } } }
```

### 4. Order of pipeline stages matters!
```javascript
// Filter THEN group (like WHERE before GROUP BY)
// WRONG order - groups all then filters (wrong result)
[
  { $group: { _id: "$dept", total: { $sum: "$price" } } },
  { $match: { "dates.fiscal_year": "2013-2014" } }  // Too late!
]

// RIGHT order
[
  { $match: { "dates.fiscal_year": "2013-2014" } },  // Filter first
  { $group: { _id: "$dept", total: { $sum: "$price" } } }
]
```

---

## Part 10: Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                    MONGODB QUICK REFERENCE                   │
├─────────────────────────────────────────────────────────────┤
│ FIND (SELECT)                                                │
│   db.collection.find({ filter }, { projection })            │
│   db.collection.findOne({ filter })                         │
│   db.collection.countDocuments({ filter })                  │
├─────────────────────────────────────────────────────────────┤
│ MODIFIERS                                                    │
│   .limit(n)     - limit results                             │
│   .sort({ field: 1 })  - sort ASC                           │
│   .sort({ field: -1 }) - sort DESC                          │
│   .pretty()     - format output                             │
├─────────────────────────────────────────────────────────────┤
│ AGGREGATE (GROUP BY)                                         │
│   db.collection.aggregate([                                 │
│     { $match: { filter } },      // WHERE                   │
│     { $group: { _id: "$field",   // GROUP BY                │
│                 sum: { $sum: "$x" },                        │
│                 avg: { $avg: "$x" },                        │
│                 count: { $sum: 1 } } },                     │
│     { $sort: { field: -1 } },    // ORDER BY                │
│     { $limit: 10 }               // LIMIT                   │
│   ])                                                        │
├─────────────────────────────────────────────────────────────┤
│ COMPARISON OPERATORS                                         │
│   $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin                │
├─────────────────────────────────────────────────────────────┤
│ NESTED FIELDS: Use dot notation                             │
│   "dates.fiscal_year"                                       │
│   "item.total_price"                                        │
│   "supplier.name"                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Your Learning Path Today

1. **Connect to MongoDB** (5 min)
   ```bash
   docker exec -it procurement_mongodb mongosh -u admin -p changeme_secure_password government_procurement
   ```

2. **Run basic queries** (15 min)
   - `db.purchase_orders.countDocuments()`
   - `db.purchase_orders.findOne()`
   - `db.purchase_orders.find().limit(5)`

3. **Practice filtering** (15 min)
   - Copy queries from Part 2, modify them

4. **Master aggregation** (30 min)
   - Work through Part 5 examples one by one
   - Type them manually, don't copy-paste!

5. **Do the exercises** (20 min)
   - Part 7 exercises

6. **Memorize the 6 demo queries** (20 min)
   - Part 8 - practice until you can type from memory

---

## Pro Tip: Learn by Exploration

```javascript
// See one full document to understand the schema
db.purchase_orders.findOne()

// See all unique values for a field
db.purchase_orders.distinct("dates.fiscal_year")
db.purchase_orders.distinct("acquisition.type")
db.purchase_orders.distinct("department.normalized_name")
```

Now go practice! The only way to learn is by typing these queries yourself.
