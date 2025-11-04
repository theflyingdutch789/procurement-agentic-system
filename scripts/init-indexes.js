// MongoDB Index Initialization Script
// This script creates optimized indexes for LLM text-to-query performance
// Run automatically on MongoDB container startup

const dbName = 'government_procurement';
const collectionName = 'purchase_orders';

// Switch to the database
db = db.getSiblingDB(dbName);

print(`Initializing indexes for ${dbName}.${collectionName}...`);

// Create the collection if it doesn't exist
db.createCollection(collectionName);

// 1. Compound indexes for common query patterns
print('Creating compound indexes...');

db[collectionName].createIndex(
  { 'dates.fiscal_year': 1, 'department.name': 1 },
  { name: 'idx_fiscal_year_department', background: true }
);

db[collectionName].createIndex(
  { 'acquisition.type': 1, 'dates.creation': -1 },
  { name: 'idx_acquisition_type_date', background: true }
);

db[collectionName].createIndex(
  { 'supplier.name': 1, 'item.total_price': -1 },
  { name: 'idx_supplier_price', background: true }
);

db[collectionName].createIndex(
  { 'dates.creation': -1 },
  { name: 'idx_creation_date', background: true }
);

db[collectionName].createIndex(
  { 'dates.fiscal_year': 1, 'acquisition.type': 1 },
  { name: 'idx_fiscal_acquisition', background: true }
);

// 2. Text index for natural language search
print('Creating text search index...');

db[collectionName].createIndex(
  {
    'item.name': 'text',
    'item.description': 'text',
    'supplier.name': 'text',
    'department.name': 'text'
  },
  {
    name: 'idx_text_search',
    weights: {
      'item.name': 10,
      'item.description': 5,
      'supplier.name': 3,
      'department.name': 2
    },
    default_language: 'english',
    background: true
  }
);

// 3. Geospatial index for location queries
print('Creating geospatial index...');

db[collectionName].createIndex(
  { 'supplier.location': '2dsphere' },
  { name: 'idx_supplier_location', sparse: true, background: true }
);

// 4. Single field indexes
print('Creating single field indexes...');

db[collectionName].createIndex(
  { 'purchase_order_number': 1 },
  { name: 'idx_po_number', sparse: true, background: true }
);

db[collectionName].createIndex(
  { 'supplier.code': 1 },
  { name: 'idx_supplier_code', background: true }
);

db[collectionName].createIndex(
  { 'item.total_price': 1 },
  { name: 'idx_total_price', background: true }
);

db[collectionName].createIndex(
  { 'cal_card': 1 },
  { name: 'idx_cal_card', background: true }
);

db[collectionName].createIndex(
  { 'classification.unspsc.segment.title': 1 },
  { name: 'idx_segment_title', background: true }
);

db[collectionName].createIndex(
  { 'classification.unspsc.family.title': 1 },
  { name: 'idx_family_title', background: true }
);

db[collectionName].createIndex(
  { 'department.normalized_name': 1 },
  { name: 'idx_dept_normalized', background: true }
);

db[collectionName].createIndex(
  { 'supplier.qualifications': 1 },
  { name: 'idx_supplier_quals', background: true }
);

// 5. Sparse indexes for optional fields
print('Creating sparse indexes...');

db[collectionName].createIndex(
  { 'dates.purchase': 1 },
  { name: 'idx_purchase_date', sparse: true, background: true }
);

db[collectionName].createIndex(
  { 'lpa_number': 1 },
  { name: 'idx_lpa_number', sparse: true, background: true }
);

// Display created indexes
print('\nIndexes created successfully:');
const indexes = db[collectionName].getIndexes();
indexes.forEach(index => {
  print(`  - ${index.name}: ${JSON.stringify(index.key)}`);
});

print(`\nTotal indexes: ${indexes.length}`);
print('Index initialization complete!');
