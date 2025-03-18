#!/bin/bash

# Wait for Elasticsearch to start
until curl -s http://localhost:9200 >/dev/null; do
    sleep 1
done

# Set up index templates
curl -X PUT "localhost:9200/_template/logs_template" -H 'Content-Type: application/json' -d'
{
  "index_patterns": ["logs-*"],
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1,
    "index.lifecycle.name": "logs_policy",
    "index.lifecycle.rollover_alias": "logs"
  },
  "mappings": {
    "properties": {
      "@timestamp": { "type": "date" },
      "level": { "type": "keyword" },
      "service": { "type": "keyword" },
      "message": { "type": "text" },
      "trace_id": { "type": "keyword" },
      "span_id": { "type": "keyword" },
      "user_id": { "type": "keyword" },
      "request_id": { "type": "keyword" },
      "duration_ms": { "type": "float" },
      "status_code": { "type": "integer" },
      "error": {
        "properties": {
          "type": { "type": "keyword" },
          "message": { "type": "text" },
          "stack_trace": { "type": "text" }
        }
      },
      "metadata": {
        "properties": {
          "host": { "type": "keyword" },
          "environment": { "type": "keyword" },
          "version": { "type": "keyword" }
        }
      }
    }
  }
}'

# Create ILM policy
curl -X PUT "localhost:9200/_ilm/policy/logs_policy" -H 'Content-Type: application/json' -d'
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_size": "50GB",
            "max_age": "1d"
          },
          "set_priority": {
            "priority": 100
          }
        }
      },
      "warm": {
        "min_age": "2d",
        "actions": {
          "set_priority": {
            "priority": 50
          },
          "shrink": {
            "number_of_shards": 1
          },
          "forcemerge": {
            "max_num_segments": 1
          }
        }
      },
      "cold": {
        "min_age": "7d",
        "actions": {
          "set_priority": {
            "priority": 0
          },
          "freeze": {}
        }
      },
      "delete": {
        "min_age": "30d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}'

# Create search templates
curl -X PUT "localhost:9200/_scripts/error_search" -H 'Content-Type: application/json' -d'
{
  "script": {
    "lang": "mustache",
    "source": {
      "query": {
        "bool": {
          "must": [
            { "match": { "level": "error" } },
            { "range": { "@timestamp": { "gte": "{{start_time}}", "lte": "{{end_time}}" } } }
          ],
          "filter": [
            { "term": { "service": "{{service}}" } }
          ]
        }
      },
      "sort": [
        { "@timestamp": "desc" }
      ],
      "size": "{{size}}"
    }
  }
}'

# Create performance search template
curl -X PUT "localhost:9200/_scripts/performance_search" -H 'Content-Type: application/json' -d'
{
  "script": {
    "lang": "mustache",
    "source": {
      "query": {
        "bool": {
          "must": [
            { "range": { "duration_ms": { "gte": "{{threshold}}" } } },
            { "range": { "@timestamp": { "gte": "{{start_time}}", "lte": "{{end_time}}" } } }
          ]
        }
      },
      "aggs": {
        "avg_duration": { "avg": { "field": "duration_ms" } },
        "max_duration": { "max": { "field": "duration_ms" } },
        "by_service": {
          "terms": { "field": "service" },
          "aggs": {
            "avg_duration": { "avg": { "field": "duration_ms" } }
          }
        }
      }
    }
  }
}'

# Create user activity search template
curl -X PUT "localhost:9200/_scripts/user_activity" -H 'Content-Type: application/json' -d'
{
  "script": {
    "lang": "mustache",
    "source": {
      "query": {
        "bool": {
          "must": [
            { "term": { "user_id": "{{user_id}}" } },
            { "range": { "@timestamp": { "gte": "{{start_time}}", "lte": "{{end_time}}" } } }
          ]
        }
      },
      "sort": [
        { "@timestamp": "desc" }
      ],
      "size": "{{size}}"
    }
  }
}'

# Create initial indices
curl -X PUT "localhost:9200/logs-000001" -H 'Content-Type: application/json' -d'
{
  "aliases": {
    "logs": {
      "is_write_index": true
    }
  }
}'

# Set up Kibana index patterns
curl -X POST "localhost:5601/api/saved_objects/index-pattern/logs-*" -H 'kbn-xsrf: true' -H 'Content-Type: application/json' -d'
{
  "attributes": {
    "title": "logs-*",
    "timeFieldName": "@timestamp"
  }
}' 