# 🚀 **SMS Financial Processing & Analytics API**

A comprehensive FastAPI service that provides SMS processing and financial analytics capabilities.

## 📋 **Table of Contents**

1. [Quick Start](#quick-start)
2. [API Endpoints](#api-endpoints)
3. [Request/Response Examples](#request-response-examples)
4. [Authentication](#authentication)
5. [Error Handling](#error-handling)
6. [Deployment](#deployment)

## 🚀 **Quick Start**

### **Installation**

```bash
# Install API dependencies
pip install -r requirements_api.txt

# Ensure your .env file is configured
cp .env.example .env  # Edit with your MongoDB credentials
```

### **Start the Server**

```bash
# Development mode (with auto-reload)
python3 api_server.py

# Production mode with Uvicorn
uvicorn api_server:app --host 0.0.0.0 --port 8000

# Production mode with Gunicorn
gunicorn api_server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### **Access Documentation**

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 🎯 **API Endpoints**

### **1. SMS Processing**

#### `POST /api/v1/sms/process`
Process SMS data through the complete pipeline.

**Features:**
- Validates SMS data format
- Runs complete processing pipeline
- Returns processing statistics
- Handles background processing

---

### **2. Financial Analytics**

#### `POST /api/v1/analytics/financial`
Get comprehensive financial analytics with custom date ranges.

#### `GET /api/v1/analytics/income/{user_id}`
Get detailed income analytics for a specific period.

#### `GET /api/v1/analytics/expenses/{user_id}`
Get detailed expense analytics and spending patterns.

---

### **3. Transaction Management**

#### `GET /api/v1/users/{user_id}/transactions`
Get paginated user transactions with filtering options.

#### `GET /api/v1/users/{user_id}/summary`
Get comprehensive user profile and financial overview.

---

### **4. System Endpoints**

#### `GET /health`
System health check and database connectivity.

#### `GET /`
API information and available endpoints.

## 📝 **Request/Response Examples**

### **1. Process SMS Data**

```bash
curl -X POST "http://localhost:8000/api/v1/sms/process" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_abc123_20241201_120000_xyz789",
    "sms_data": [
      {
        "sender": "VM-HDFCBK-S",
        "body": "A/c *1234 debited for Rs:500.00 on 01-Dec-2024 via UPI",
        "date": "2024-12-01T12:00:00Z",
        "type": "SmsMessageKind.received"
      },
      {
        "sender": "AX-SBIPSG",
        "body": "Rs.2000.00 credited to A/c *5678 on 01-Dec-2024 salary",
        "date": "2024-12-01T10:00:00Z",
        "type": "SmsMessageKind.received"
      }
    ],
    "batch_size": 5,
    "model": "qwen3:8b",
    "create_indexes": false,
    "skip_date_conversion": false
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "SMS data processed successfully",
  "task_id": "sms_process_20241201_120000_usr_abc1",
  "user_id": "usr_abc123_20241201_120000_xyz789",
  "processed_at": "2024-12-01T12:05:00Z",
  "statistics": {
    "input_sms_count": 2,
    "total_uploaded": 125,
    "total_processed": 125,
    "total_financial": 87
  },
  "pipeline_output": "✅ COMPLETE PIPELINE EXECUTION SUCCESSFUL..."
}
```

### **2. Get Financial Analytics**

```bash
curl -X POST "http://localhost:8000/api/v1/analytics/financial" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_abc123_20241201_120000_xyz789",
    "period": "last_3_months"
  }'
```

**Response:**
```json
{
  "user_id": "usr_abc123_20241201_120000_xyz789",
  "period": "last_3_months",
  "start_date": "2024-09-01T00:00:00Z",
  "end_date": "2024-12-01T23:59:59Z",
  "total_income": 45000.00,
  "total_expense": 32000.00,
  "net_amount": 13000.00,
  "transaction_count": 87,
  "income_transactions": 12,
  "expense_transactions": 75,
  "top_categories": [
    {
      "category": "food",
      "total_amount": 8500.00,
      "count": 25,
      "type": "debit"
    },
    {
      "category": "salary",
      "total_amount": 30000.00,
      "count": 3,
      "type": "credit"
    }
  ],
  "monthly_breakdown": [
    {
      "month": "2024-09",
      "income": 15000.00,
      "expense": 10000.00,
      "net": 5000.00
    },
    {
      "month": "2024-10",
      "income": 15000.00,
      "expense": 11000.00,
      "net": 4000.00
    },
    {
      "month": "2024-11",
      "income": 15000.00,
      "expense": 11000.00,
      "net": 4000.00
    }
  ]
}
```

### **3. Get Income Analytics**

```bash
curl "http://localhost:8000/api/v1/analytics/income/usr_abc123_20241201_120000_xyz789?period=last_month"
```

### **4. Get Expense Analytics**

```bash
curl "http://localhost:8000/api/v1/analytics/expenses/usr_abc123_20241201_120000_xyz789?period=last_month"
```

### **5. Get User Transactions**

```bash
curl "http://localhost:8000/api/v1/users/usr_abc123_20241201_120000_xyz789/transactions?limit=50&transaction_type=credit"
```

### **6. Custom Date Range Analytics**

```bash
curl -X POST "http://localhost:8000/api/v1/analytics/financial" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_abc123_20241201_120000_xyz789",
    "start_date": "2024-11-01",
    "end_date": "2024-11-30"
  }'
```

## 🔐 **Authentication**

Currently, the API operates without authentication for development. For production deployment:

1. **Add JWT Authentication**
2. **Implement API Key validation**
3. **Add rate limiting**
4. **Enable HTTPS**

## ⚠️ **Error Handling**

### **Standard Error Response Format**

```json
{
  "message": "Error description",
  "task_id": "optional_task_id",
  "error": "detailed_error_message",
  "timestamp": "2024-12-01T12:00:00Z"
}
```

### **HTTP Status Codes**

- `200` - Success
- `400` - Bad Request (validation errors)
- `404` - Resource not found (user/transaction not found)
- `500` - Internal Server Error
- `503` - Service Unavailable (database connection issues)

## 🚀 **Deployment**

### **Docker Deployment**

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements_api.txt .
RUN pip install -r requirements_api.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **Environment Variables**

```bash
# Required
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DB=pluto_money

# Optional
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=info
```

### **Production Considerations**

1. **Load Balancing**: Use Nginx or AWS ALB
2. **Database**: MongoDB Atlas or dedicated MongoDB cluster
3. **Monitoring**: Prometheus + Grafana
4. **Logging**: Centralized logging with ELK stack
5. **Security**: WAF, rate limiting, input validation

## 🎯 **Time Period Options**

- `last_week` - Last 7 days
- `last_month` - Last 30 days
- `last_3_months` - Last 90 days
- `last_6_months` - Last 180 days
- `last_year` - Last 365 days
- Custom: Use `start_date` and `end_date` parameters

## 📊 **Supported Analytics**

### **Financial Metrics**
- Total income/expenses
- Net amount (income - expenses)
- Transaction counts
- Average transaction amounts
- Category breakdowns
- Monthly trends

### **SMS Processing Metrics**
- Total SMS uploaded
- Total SMS processed
- Financial SMS count
- Processing success rates
- Pipeline execution statistics

## 🛠️ **Advanced Features**

1. **Background Processing**: Long-running SMS processing tasks
2. **Real-time Updates**: WebSocket support for processing status
3. **Batch Operations**: Process multiple users simultaneously
4. **Data Export**: CSV/Excel export of financial data
5. **Webhooks**: Notify external systems of processing completion

## 🔧 **Development**

### **Run Tests**
```bash
pytest tests/
```

### **Code Formatting**
```bash
black api_server.py
isort api_server.py
```

### **Type Checking**
```bash
mypy api_server.py
```

---

**🎉 Your SMS Financial Processing & Analytics API is ready for production!**
