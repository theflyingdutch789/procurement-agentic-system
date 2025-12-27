# Demo Day Cheatsheet (Keep This Open!)

## Quick Commands
```bash
# Start everything
make start

# Check status
make status

# View logs
make logs

# MongoDB shell
docker exec -it procurement_mongodb mongosh -u admin -p changeme_secure_password government_procurement
```

## MongoDB Compass URI
```
mongodb://admin:changeme_secure_password@localhost:27017/government_procurement?authSource=admin
```

## URLs
- **Web UI**: http://localhost:5000
- **API Docs**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/api/health

---

## Demo Queries (Natural Language → MongoDB)

### Query 1: Count
**Ask:** "How many purchase orders are in the database?"

**MongoDB:**
```javascript
db.purchase_orders.countDocuments()
// Result: 346,018
```

---

### Query 2: Total Spending
**Ask:** "What is the total spending across all fiscal years?"

**MongoDB:**
```javascript
db.purchase_orders.aggregate([
  { $group: { _id: null, total: { $sum: "$item.total_price" } } }
])
```

---

### Query 3: Top Departments
**Ask:** "Which are the top 5 departments by spending?"

**MongoDB:**
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

---

### Query 4: Spending by Year
**Ask:** "What is the spending breakdown by fiscal year?"

**MongoDB:**
```javascript
db.purchase_orders.aggregate([
  { $group: {
      _id: "$dates.fiscal_year",
      total: { $sum: "$item.total_price" }
  }},
  { $sort: { _id: 1 } }
])
```

---

### Query 5: Top Suppliers
**Ask:** "Who are the top 5 suppliers?"

**MongoDB:**
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

---

### Query 6: IT vs Non-IT
**Ask:** "Compare IT vs Non-IT spending"

**MongoDB:**
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

## Architecture One-Liner

"User asks question → Flask sends to FastAPI → AI Agent sends to GPT to generate MongoDB pipeline → Executes pipeline → GPT summarizes results → Returns human answer"

---

## Key Numbers to Remember
- **346,018** documents
- **4** fiscal years (2012-2015)
- **~$2.5 billion** total spending
- **4** acquisition types (IT Goods, IT Services, NON-IT Goods, NON-IT Services)

---

## If Something Breaks

```bash
# Restart everything
make restart

# Check what's wrong
make logs
```

---

## Aggregation Pipeline Stages Explained

| Stage | Purpose | Example |
|-------|---------|---------|
| `$match` | Filter documents | `{ $match: { "dates.fiscal_year": "2013-2014" } }` |
| `$group` | Group & aggregate | `{ $group: { _id: "$dept", total: { $sum: "$price" } } }` |
| `$sort` | Order results | `{ $sort: { total: -1 } }` |
| `$limit` | Take top N | `{ $limit: 5 }` |
| `$project` | Select fields | `{ $project: { name: 1, price: 1 } }` |

---

## You've Got This! 🚀
