📱 RAW SMS DATA (any format)
    ↓
🔐 USER MANAGEMENT (globally unique IDs)
    ↓  
💾 sms_data (MongoDB) [is_processed tracking]
    ↓
🔍 FINANCIAL FILTERING (rule-based intelligence)
    ↓
💾 sms_fin_rawdata (MongoDB) [isprocessed tracking] 
    ↓
⚡ PARALLEL PROCESSING (LLM + Rule-based fallback)
    ↓
💾 financial_transactions (MongoDB) [structured data]
    ↓
📅 DATE CONVERSION (optional BSON format)
    ↓
💾 user_financial_transactions (MongoDB) [final storage]