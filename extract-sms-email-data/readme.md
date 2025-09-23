📱 RAW SMS DATA (any format)
    ↓
🔐 USER MANAGEMENT (globally unique IDs)  -  sms_mongodb_uploader.py
    ↓  
💾 sms_data (MongoDB) [is_processed tracking]
    ↓
🔍 FINANCIAL FILTERING (rule-based intelligence) -  mongodb_pipeline.py
    ↓
💾 sms_fin_rawdata (MongoDB) [isprocessed tracking] 
    ↓
⚡ PARALLEL PROCESSING (LLM + Rule-based fallback) - main.py
    ↓
💾 financial_transactions (MongoDB) [structured data]
    ↓
📅 DATE CONVERSION (optional BSON format) - convert_transaction_dates.py
    ↓
💾 user_financial_transactions (MongoDB) [final storage]