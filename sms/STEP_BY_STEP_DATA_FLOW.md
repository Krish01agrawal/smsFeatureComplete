# 🔍 PRODUCTION API v2.0 - STEP-BY-STEP DATA FLOW ANALYSIS
## Complete Pipeline Breakdown for Financial Chat API

---

## 📋 **STEP 1: REQUEST VALIDATION & INITIALIZATION**

### **Input Data:**
```json
{
  "user_id": "user_123",
  "query": "Last month total spending and my major expenses?",
  "context": {} // optional
}
```

### **Operations:**
1. **Request Validation:** Validate JSON structure and required fields
2. **User Existence Check:** Verify `user_123` exists in `user_financial_transactions`
3. **Correlation ID:** Generate unique trace ID for request tracking
4. **Timezone Setup:** Initialize IST ↔ UTC conversion handlers
5. **AI Provider Detection:** Check available AI providers (Groq/Gemini/In-house)
6. **MongoDB Client:** Initialize connection with SSL configuration for Atlas

### **Cache Key Generation:**
- **Sub-queries Cache:** `user_123_subqueries_hash_v2.0`
- **Pipeline Cache:** `user_123_pipelines_hash_v2.0`
- **TTL:** 30 minutes (sub-queries), 2 hours (pipelines)

### **Output:**
- Cache MISS (first time for this specific query)
- Proceed to AI processing with Groq as primary provider

---

## 🧠 **STEP 2: AI MODEL PROCESSING - MULTI-PROVIDER SYSTEM**

### **AI Provider Selection:**
1. **Primary:** Groq (llama3-8b-8192) - Fast inference
2. **Fallback:** Gemini (gemini-1.5-flash) - High quality
3. **Emergency:** In-house models or template system

### **Input to AI Model:**
```
"User Query: 'Last month total spending and my major expenses?'
User ID: user_123

Generate 8-10 specific sub-queries for comprehensive financial analysis.
Requirements:
- Time-aware queries with proper date handling
- Category-based spending analysis
- Pattern recognition and trends
- Major transaction identification
- Comparative analysis capabilities

Return ONLY a JSON array of strings."
```

### **AI Processing:**
- **Model Used:** Groq (llama3-8b-8192)
- **Tokens:** ~250 input, ~400 output
- **Temperature:** 0.1 (deterministic)
- **Max Retries:** 1 per provider
- **Purpose:** Convert natural language to structured sub-queries

### **Output from AI Model:**
```json
[
  "Total spending amount for last month",
  "Top 5 spending categories last month",
  "Major expense transactions over $500",
  "Daily spending patterns last month",
  "Comparison with previous month",
  "Recurring payments and subscriptions",
  "Merchant spending distribution",
  "Weekend vs weekday spending patterns"
]
```

---

## 🔧 **STEP 3: MONGODB QUERY GENERATION - THREE-TIER SYSTEM**

### **Tier 1: LLM-Generated Aggregation Pipelines**
- **Primary Approach:** AI generates MongoDB aggregation pipelines
- **Collection:** `user_financial_transactions`
- **Features:** BSON date handling, debitAmount calculation, IST/UTC conversion

### **Example Generated Pipeline:**
```javascript
{
  "sub_query": "Total spending amount for last month",
  "pipeline": [
    {
      "$match": {
        "user_id": "user_123",
        "transaction_date": {
          "$gte": ISODate("2024-11-01T00:00:00.000Z"),
          "$lt": ISODate("2024-12-01T00:00:00.000Z")
        },
        "transaction_type": "debit"
      }
    },
    {
      "$addFields": {
        "debitAmount": {
          "$cond": {
            "if": { "$lt": ["$amount", 0] },
            "then": { "$abs": "$amount" },
            "else": "$amount"
          }
        }
      }
    },
    {
      "$group": {
        "_id": null,
        "total_spending": { "$sum": "$debitAmount" },
        "transaction_count": { "$sum": 1 }
      }
    }
  ]
}
```

### **Tier 2: Template-Based Fallback**
- **Trigger:** When LLM fails or generates invalid queries
- **Method:** 9 predefined templates for common query patterns
- **Reliability:** Medium quality, always syntactically correct

### **Tier 3: Emergency Fallback**
- **Trigger:** When both LLM and templates fail
- **Method:** Basic aggregation queries
- **Guarantee:** Always returns some result

---

## ⚡ **STEP 4: PARALLEL EXECUTION ENGINE**

### **Concurrent Processing:**
- **Parallel Queries:** 4-6 MongoDB aggregations execute simultaneously
- **Timeout Handling:** Individual query timeouts (30 seconds each)
- **Error Isolation:** One query failure doesn't affect others
- **Resource Management:** Connection pooling and query optimization

### **Execution Results:**
```json
{
  "query_1": { "total_spending": 15750.50, "count": 87 },
  "query_2": { "categories": [{"food": 4200}, {"transport": 2100}] },
  "query_3": { "major_expenses": [{"merchant": "ABC Store", "amount": 1200}] },
  "query_4": { "daily_avg": 525.02 },
  "query_5": { "comparison": {"current": 15750, "previous": 14200} }
}
```

---

## 🧠 **STEP 5: INTELLIGENT RESPONSE GENERATION**

### **Data Synthesis:**
- **Input:** All query results + GroundingContext
- **AI Model:** Same provider as Step 2
- **Process:** Combine results into coherent financial insights

### **Final Response:**
```json
{
  "user_id": "user_123",
  "query": "Last month total spending and my major expenses?",
  "response": "Based on your financial data, you spent ₹15,750 last month across 87 transactions. Your major expense categories were Food & Dining (₹4,200) and Transportation (₹2,100). Notable large expenses include ₹1,200 at ABC Store. This represents a 10.9% increase compared to the previous month (₹14,200).",
  "sub_queries": [...],
  "data_points": 87,
  "processing_time": 3.2,
  "timestamp": "2024-12-07T10:30:00Z",
  "confidence_score": 0.95
}
```

---

## 📊 **SYSTEM PERFORMANCE METRICS**

- **Total Processing Time:** 3.2 seconds
- **Cache Miss Penalty:** +2.1 seconds
- **AI Provider Response:** 0.8 seconds
- **MongoDB Execution:** 1.2 seconds (parallel)
- **Response Generation:** 0.4 seconds

---

*Last Updated: Current as of Production API v2.0*
