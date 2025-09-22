# Individual API Testing Commands
# ===============================

API_BASE="http://localhost:8001"
USER_ID="68d14ae0ed81ad7946e00a2f"  # Use existing user ID

# 1. Health Check
echo "📡 Health Check:"
curl -X GET "$API_BASE/health"

# 2. Process SMS Data
echo -e "\n\n📱 Process SMS Data:"
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
      }
    ],
    "batch_size": 5,
    "model": "qwen3:8b",
    "create_indexes": true
  }'

# 3. Financial Analytics
echo -e "\n\n📊 Financial Analytics:"
curl -X POST "$API_BASE/api/v1/analytics/financial" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER_ID'",
    "period": "last_month"
  }'

# 4. Income Analytics
echo -e "\n\n💰 Income Analytics:"
curl -X GET "$API_BASE/api/v1/analytics/income/$USER_ID?period=last_month"

# 5. Expense Analytics
echo -e "\n\n💸 Expense Analytics:"
curl -X GET "$API_BASE/api/v1/analytics/expenses/$USER_ID?period=last_month"

# 6. User Transactions
echo -e "\n\n📋 User Transactions:"
curl -X GET "$API_BASE/api/v1/users/$USER_ID/transactions?limit=5"

# 7. User Summary
echo -e "\n\n👤 User Summary:"
curl -X GET "$API_BASE/api/v1/users/$USER_ID/summary"
