# 💬 Financial Chat API v2.0 - Complete Production Guide

## 🎯 **OVERVIEW**

The Financial Chat API v2.0 is a production-ready natural language interface for financial data analysis. It features **multi-provider AI integration** (Groq, Gemini, In-house), **three-tier fallback systems**, and **enterprise-grade reliability** for processing data from your MongoDB `pluto_money` database.

---

## 🚀 **QUICK START**

### **1. Start the Production API Server**
```bash
cd DS/sms
python3 run_production_api.py
```

### **2. Alternative Startup Methods**
```bash
# Using the enhanced startup script
python3 start_chat_api.py

# Direct uvicorn (for development)
uvicorn src.financial_chat_api_production:app --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

### **3. API Documentation & Monitoring**
- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Cache Statistics**: http://localhost:8000/cache/stats
- **AI Provider Status**: http://localhost:8000/ai/providers

---

## 📡 **API ENDPOINTS v2.0**

### **🔥 Core Endpoints**

#### **POST /chat**
Main endpoint for natural language financial queries with enhanced AI processing.

**Request Body:**
```json
{
  "user_id": "user_123",
  "query": "What are my spending patterns for the last month?",
  "context": {} // optional
}
```

**Enhanced Response:**
```json
{
  "user_id": "user_123",
  "query": "What are my spending patterns for the last month?",
  "response": "Based on your financial data from user_financial_transactions, you spent ₹15,750 last month across 87 transactions. Your top categories were Food & Dining (₹4,200, 26.7%) and Transportation (₹2,100, 13.3%). Notable patterns include higher weekend spending and a 10.9% increase from the previous month.",
  "sub_queries": [
    "Total spending amount for last month",
    "Top 5 spending categories by amount",
    "Daily spending patterns and trends",
    "Comparison with previous month",
    "Major expense transactions over ₹1000"
  ],
  "data_points": 87,
  "processing_time": 3.2,
  "timestamp": "2024-12-07T10:30:00Z",
  "confidence_score": 0.95,
  "ai_provider": "groq",
  "cache_hit": false
}
```

### **🔧 System Management Endpoints**

#### **GET /health**
Enhanced system health check with detailed status information.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "ai_providers": {
    "groq": "available",
    "gemini": "available",
    "inhouse": "unavailable"
  },
  "cache": "operational",
  "uptime": 3600,
  "version": "2.0.0"
}
```

#### **GET /cache/stats**
Cache performance statistics and metrics.

**Response:**
```json
{
  "cache_stats": {
    "hit_rate": 0.73,
    "total_requests": 1250,
    "cache_hits": 912,
    "cache_misses": 338,
    "avg_response_time_cached": 0.12,
    "avg_response_time_uncached": 3.45
  }
}
```

#### **POST /cache/clear**
Clear system cache (requires admin access).

### **🤖 AI Provider Management Endpoints**

#### **GET /ai/providers**
Get status of all available AI providers.

**Response:**
```json
{
  "providers": {
    "groq": {
      "status": "available",
      "model": "llama3-8b-8192",
      "priority": 1,
      "last_used": "2024-12-07T10:29:45Z"
    },
    "gemini": {
      "status": "available", 
      "model": "gemini-1.5-flash",
      "priority": 2,
      "last_used": "2024-12-07T09:15:30Z"
    }
  },
  "active_provider": "groq"
}
```

#### **POST /ai/switch/{provider}**
Switch to a specific AI provider.

**Parameters:**
- `provider`: groq, gemini, or inhouse

**Response:**
```json
{
  "message": "AI provider switched to groq",
  "previous_provider": "gemini",
  "current_provider": "groq"
}
```

---

## ⚙️ **CONFIGURATION & SETUP**

### **Environment Variables**
```bash
# MongoDB Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/pluto_money
MONGODB_DB=pluto_money

# AI Provider API Keys
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
INHOUSE_API_KEY=your_inhouse_api_key_here  # Optional
INHOUSE_API_URL=http://localhost:5000/v1/chat/completions  # Optional

# System Configuration
DEBUG=False
LOG_LEVEL=INFO
```

### **Database Schema**
- **Collection:** `user_financial_transactions`
- **Required Fields:** `user_id`, `transaction_date`, `amount`, `transaction_type`
- **Date Format:** BSON Date with automatic IST/UTC conversion
- **Amount Handling:** Automatic `debitAmount` calculation for consistent processing

---

## 🚀 **NEW v2.0 FEATURES**

### **🤖 Multi-Provider AI System**
- **Automatic Fallback:** Seamless switching between AI providers
- **Provider Priority:** Configurable preference order
- **Health Monitoring:** Real-time provider status tracking
- **Performance Optimization:** <100ms provider switching time

### **⚡ Enhanced Performance**
- **Parallel Processing:** 4-6 concurrent MongoDB queries
- **Versioned Caching:** Intelligent cache with 60-80% hit rate
- **Connection Pooling:** Optimized MongoDB Atlas connections
- **Timeout Management:** Individual query timeout handling

### **🔒 Enterprise Reliability**
- **Three-Tier Fallback:** LLM → Template → Emergency queries
- **Error Isolation:** Individual query failures don't affect system
- **Graceful Degradation:** System remains functional with provider failures
- **BSON Date Handling:** Proper timezone conversion and date processing

---

## 📊 **PERFORMANCE METRICS**

### **Typical Response Times:**
- **Cached Queries:** ~0.1-0.2 seconds
- **Simple Queries:** ~2-3 seconds  
- **Complex Queries:** ~3-5 seconds
- **Provider Fallback:** <100ms additional overhead

### **System Specifications:**
- **API Version:** v2.0.0
- **Database:** MongoDB Atlas with SSL
- **AI Models:** Groq (llama3-8b-8192), Gemini (gemini-1.5-flash)
- **Cache TTL:** 30min (sub-queries), 2hr (pipelines)
- **Concurrent Queries:** 4-6 parallel MongoDB operations

---

*Last Updated: Production API v2.0 - December 2024*
