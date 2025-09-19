# 🚀 CURRENT SYSTEM PIPELINE FLOW CHART
## Production API v2.0 - Complete Pipeline Architecture

```
                    🎯 USER QUERY INPUT
                    ┌─────────────────────────────────┐
                    │ POST /chat                      │
                    │ user_id: "user_123"            │
                    │ query: "Last month total       │
                    │       spending and my major    │
                    │       expenses?"               │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │   REQUEST VALIDATION & SETUP   │
                    │  • Validate user_123 exists    │
                    │  • Generate correlation ID     │
                    │  • IST ↔ UTC timezone setup   │
                    │  • Initialize MongoDB client  │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │    VERSIONED CACHE CHECK       │
                    │  • Sub-queries cache (30 min)  │
                    │  • Pipeline cache (2 hours)    │
                    │  • User-specific cache keys    │
                    │  • Version-aware invalidation  │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │      CACHE RESULT?             │
                    └─────────┬───────────────┬───────┘
                              │               │
                              │ HIT           │ MISS
                              ▼               ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │   RETURN CACHED │    │  AI PROVIDER    │
                    │   RESPONSE WITH │    │   SELECTION     │
                    │   METADATA      │    │  (Groq/Gemini)  │
                    └─────────────────┘    └─────────┬───────┘
                                                     │
                                                     ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │          AI MODEL PROCESSING                           │
                    │     (Multi-Provider with Fallback)                     │
                    │                                                         │
                    │ • Auto-detect available providers                      │
                    │ • Priority: Groq → Gemini → In-house                  │
                    │ • Generate 8-10 sub-queries from user intent          │
                    │ • Fallback to template system if AI fails             │
                    │                                                         │
                    │ • Groq (llama3-8b-8192)                               │
                    │ • Gemini (gemini-1.5-flash)                           │
                    │ • In-house models (configurable)                      │
                    │                                                         │
                    │ Example Sub-queries Generated:                          │
                    │ • "Total spending last month"                          │
                    │ • "Top spending categories"                            │
                    │ • "Major expense transactions"                         │
                    │ • "Daily spending patterns"                            │
                    └─────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │         MONGODB QUERY GENERATION                        │
                    │      (Production Collection: user_financial_transactions)│
                    │                                                         │
                    │ • LLM-generated aggregation pipelines                  │
                    │ • Three-tier fallback system:                          │
                    │   - Tier 1: LLM-generated (highest quality)           │
                    │   - Tier 2: Template-based (medium quality)           │
                    │   - Tier 3: Emergency fallback (always works)         │
                    │ • BSON date handling with IST/UTC conversion          │
                    │ • debitAmount calculation in all pipelines            │
                    └─────────────────────────┬───────────────────────────────┘
                                              │
                                              ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │        PARALLEL EXECUTION ENGINE                        │
                    │         (4-6 Concurrent Queries)                       │
                    │                                                         │
                    │ • Execute all MongoDB queries simultaneously           │
                    │ • Individual query timeout handling                    │
                    │ • Error isolation (failures don't affect others)      │
                    │ • Result aggregation and validation                    │
                    │ • GroundingContext generation for accuracy            │
                    └─────────────────────────┬───────────────────────────────┘
                                              │
                                              ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │         INTELLIGENT RESPONSE GENERATION                │
                    │           (AI-Powered Synthesis)                       │
                    │                                                         │
                    │ • Combine all query results into coherent response    │
                    │ • Generate insights and patterns                       │
                    │ • Include confidence scores and metadata              │
                    │ • Format for optimal user experience                  │
                    └─────────────────────────┬───────────────────────────────┘
                                              │
                                              ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │              FINAL RESPONSE                            │
                    │                                                         │
                    │ • Complete JSON response with insights                 │
                    │ • Processing time and data point metrics              │
                    │ • Cache storage for future requests                   │
                    │ • Error handling and graceful degradation             │
                    └─────────────────────────────────────────────────────────┘

```

---

## 🔧 **CURRENT SYSTEM SPECIFICATIONS**

### **API Endpoints (v2.0):**
- `POST /chat` - Main natural language query endpoint
- `GET /health` - System health and status
- `GET /cache/stats` - Cache performance metrics
- `POST /cache/clear` - Cache management
- `GET /ai/providers` - Available AI providers
- `POST /ai/switch/{provider}` - Switch AI provider

### **Database Schema:**
- **Collection:** `user_financial_transactions`
- **Database:** `pluto_money`
- **Features:** BSON date handling, timezone conversion, debitAmount calculation

### **AI Providers:**
- **Groq:** llama3-8b-8192 (primary, fast inference)
- **Gemini:** gemini-1.5-flash (secondary, high quality)
- **In-house:** Configurable custom models

### **Performance Features:**
- **Caching:** Versioned cache with 30min-2hour TTL
- **Parallel Processing:** 4-6 concurrent MongoDB queries
- **Fallback System:** Three-tier reliability (LLM → Template → Emergency)
- **Timezone Handling:** Automatic IST ↔ UTC conversion
- **Error Resilience:** Individual query failure isolation

### **Key Improvements from v1.0:**
- Multi-provider AI system with automatic fallback
- Versioned caching for better performance
- Enhanced MongoDB aggregation pipeline generation
- BSON date handling for accurate time-based queries
- Parallel execution engine for faster responses
- GroundingContext validation for accuracy

---

## 📊 **SYSTEM METRICS**

### **Performance:**
- **Response Time:** ~2-5 seconds for complex queries
- **Cache Hit Rate:** 60-80% for repeated queries
- **Parallel Execution:** 4-6 concurrent database operations
- **AI Provider Fallback:** <100ms provider switching

### **Reliability:**
- **Uptime:** 99.9% target with health monitoring
- **Error Handling:** Graceful degradation at each tier
- **Data Accuracy:** GroundingContext validation
- **Timezone Accuracy:** IST/UTC conversion with BSON dates

---

*Last Updated: Current as of Production API v2.0*
