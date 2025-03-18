// Initialize replica set
rs.initiate({
  _id: "rs0",
  members: [{ _id: 0, host: "localhost:27017" }],
});

// Wait for the replica set to initialize
sleep(1000);

// Switch to the ecommerce_logs database
db = db.getSiblingDB("ecommerce_logs");

// Create collections
db.createCollection("system_logs");
db.createCollection("application_logs");
db.createCollection("access_logs");
db.createCollection("error_logs");
db.createCollection("performance_logs");
db.createCollection("audit_logs");

// Create indexes
db.system_logs.createIndex({ timestamp: 1 });
db.system_logs.createIndex({ level: 1 });
db.system_logs.createIndex({ service: 1 });

db.application_logs.createIndex({ timestamp: 1 });
db.application_logs.createIndex({ level: 1 });
db.application_logs.createIndex({ component: 1 });

db.access_logs.createIndex({ timestamp: 1 });
db.access_logs.createIndex({ user_id: 1 });
db.access_logs.createIndex({ endpoint: 1 });

db.error_logs.createIndex({ timestamp: 1 });
db.error_logs.createIndex({ error_type: 1 });
db.error_logs.createIndex({ service: 1 });

db.performance_logs.createIndex({ timestamp: 1 });
db.performance_logs.createIndex({ service: 1 });
db.performance_logs.createIndex({ metric: 1 });

db.audit_logs.createIndex({ timestamp: 1 });
db.audit_logs.createIndex({ user_id: 1 });
db.audit_logs.createIndex({ action: 1 });

// Create TTL indexes for automatic data cleanup
db.system_logs.createIndex({ timestamp: 1 }, { expireAfterSeconds: 7776000 }); // 90 days
db.application_logs.createIndex(
  { timestamp: 1 },
  { expireAfterSeconds: 7776000 }
);
db.access_logs.createIndex({ timestamp: 1 }, { expireAfterSeconds: 15552000 }); // 180 days
db.error_logs.createIndex({ timestamp: 1 }, { expireAfterSeconds: 15552000 });
db.performance_logs.createIndex(
  { timestamp: 1 },
  { expireAfterSeconds: 7776000 }
);
db.audit_logs.createIndex({ timestamp: 1 }, { expireAfterSeconds: 31536000 }); // 365 days

// Create roles
db.createRole({
  role: "logsReader",
  privileges: [
    {
      resource: { db: "ecommerce_logs", collection: "" },
      actions: ["find", "listCollections"],
    },
  ],
  roles: [],
});

db.createRole({
  role: "logsWriter",
  privileges: [
    {
      resource: { db: "ecommerce_logs", collection: "" },
      actions: ["insert", "update"],
    },
  ],
  roles: [],
});

// Create users
db.createUser({
  user: process.env.MONGO_USER,
  pwd: process.env.MONGO_PASSWORD,
  roles: [
    { role: "readWrite", db: "ecommerce_logs" },
    { role: "logsReader", db: "ecommerce_logs" },
    { role: "logsWriter", db: "ecommerce_logs" },
  ],
});

// Create views
db.createView("error_summary", "error_logs", [
  {
    $group: {
      _id: {
        error_type: "$error_type",
        service: "$service",
        day: { $dateToString: { format: "%Y-%m-%d", date: "$timestamp" } },
      },
      count: { $sum: 1 },
      first_occurrence: { $min: "$timestamp" },
      last_occurrence: { $max: "$timestamp" },
      error_messages: { $addToSet: "$message" },
    },
  },
]);

db.createView("performance_metrics", "performance_logs", [
  {
    $group: {
      _id: {
        service: "$service",
        metric: "$metric",
        hour: {
          $dateToString: {
            format: "%Y-%m-%d %H:00:00",
            date: "$timestamp",
          },
        },
      },
      avg_value: { $avg: "$value" },
      min_value: { $min: "$value" },
      max_value: { $max: "$value" },
      count: { $sum: 1 },
    },
  },
]);

db.createView("user_activity", "access_logs", [
  {
    $group: {
      _id: {
        user_id: "$user_id",
        day: { $dateToString: { format: "%Y-%m-%d", date: "$timestamp" } },
      },
      total_requests: { $sum: 1 },
      endpoints: { $addToSet: "$endpoint" },
      first_access: { $min: "$timestamp" },
      last_access: { $max: "$timestamp" },
    },
  },
]);
