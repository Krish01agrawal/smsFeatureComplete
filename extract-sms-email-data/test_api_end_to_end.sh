#!/bin/bash

# API End-to-End Testing Script
# =============================

API_BASE="http://localhost:8001"
USER_ID="68d14ae0ed81ad7946e00a2f"  # Use existing user ID from our tests

echo "🚀 Starting API End-to-End Testing"
echo "=================================="

# Step 1: Health Check
echo "📡 Testing API Health..."
curl -X GET "$API_BASE/health" | jq '.'

echo -e "\n"

# Step 2: Process SMS Data
echo "📱 Processing SMS Data..."
curl -X POST "$API_BASE/api/v1/sms/process" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER_ID'",
    "sms_data": [
      {
        "sender": "VM-HDFCBK",
        "body": "Rs:15000.00 credited to A/c *1234 on 22/09/25. Avl Bal: Rs:75000.00. Ref: 111222333",
        "date": "2025-09-22T08:30:00.000Z",
        "type": "SmsMessageKind.received"
      },
      {
        "sender": "AX-SBIPSG", 
        "body": "A/c *5678 debited for Rs:8500.00 on 22/09/25. Avl Bal: Rs:66500.00. Ref: 444555666",
        "date": "2025-09-22T14:15:00.000Z",
        "type": "SmsMessageKind.received"
      },
      {
        "sender": "VM-ICICIB",
        "body": "Rs:12000.00 credited to A/c *9999 on 22/09/25. Avl Bal: Rs:78500.00. Ref: 777888999", 
        "date": "2025-09-22T16:45:00.000Z",
        "type": "SmsMessageKind.received"
      }
    ],
    "batch_size": 5,
    "model": "qwen3:8b",
    "create_indexes": true
  }' | jq '.'

echo -e "\n"

# Step 3: Get Financial Analytics
echo "📊 Getting Financial Analytics..."
curl -X POST "$API_BASE/api/v1/analytics/financial" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER_ID'",
    "period": "last_month"
  }' | jq '.'

echo -e "\n"

# Step 4: Get Income Analytics
echo "💰 Getting Income Analytics..."
curl -X GET "$API_BASE/api/v1/analytics/income/$USER_ID?period=last_month" | jq '.'

echo -e "\n"

# Step 5: Get Expense Analytics  
echo "💸 Getting Expense Analytics..."
curl -X GET "$API_BASE/api/v1/analytics/expenses/$USER_ID?period=last_month" | jq '.'

echo -e "\n"

# Step 6: Get User Transactions
echo "📋 Getting User Transactions..."
curl -X GET "$API_BASE/api/v1/users/$USER_ID/transactions?limit=10" | jq '.'

echo -e "\n"

# Step 7: Get User Summary
echo "👤 Getting User Summary..."
curl -X GET "$API_BASE/api/v1/users/$USER_ID/summary" | jq '.'

echo -e "\n"
echo "✅ API End-to-End Testing Complete!"
