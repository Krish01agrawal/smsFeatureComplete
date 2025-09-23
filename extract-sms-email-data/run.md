
1. test_sms.json → sms_mongodb_uploader.py → sms_data (MongoDB)
2. sms_data → mongodb_pipeline.py → sms_financial_filter.py → financial SMS
3. financial SMS → extract_financial_array.py → array format
4. array → main.py (rule-based fallback) → financial_transactions
5. financial_transactions → convert_transaction_dates.py → user_financial_transactions


<!-- 

# Step 1: Filter (from your 5,072 SMS)(raw sms/email)
python3 sms_financial_filter.py sms_data.json -o filtered_financial.json

# Step 2: Extract array (extract fin_data json)
python3 extract_financial_array.py filtered_financial.json -o financial_array.json  

# Step 3: Process with AI (Data to information -> stored in mongodb)
python3 main.py --input financial_array.json --output final_results.json --failures complete_failures.ndjson


python3 main.py --input test_realtime.json --output test_results_realtime.json --failures test_failures_realtime.ndjson --batch-size 1 --parallel-batches 1


 -->




cd extract-sms-email-data/






# 🚀 COMPLETE SMS PROCESSING PIPELINE
# ===================================

# 1. Upload raw SMS data with enterprise user management
python3 sms_mongodb_uploader.py --input test_sms.json --user-name "Test User" --user-email "test@example.com" --create-indexes --user-stats

# 2. Run complete pipeline with user ID (THE MOST IMPORTANT COMMAND)
# Use the user_id from step 1 output
python3 mongodb_pipeline.py --user-id "usr_GENERATED_ID_FROM_STEP_1" --batch-size 2 --model "qwen3:8b"

# 3. (Optional) Convert dates to BSON format
python3 convert_transaction_dates.py --db pluto_money --source financial_transactions --dest user_financial_transactions

# 4. Verify results and check user statistics
python3 user_manager.py --stats
python3 user_manager.py --list







# 📊 MONITORING & ANALYTICS
# =========================

# Check system-wide statistics
python3 user_manager.py --stats

# List all users
python3 user_manager.py --list




# Upload more SMS for existing user
python3 sms_mongodb_uploader.py --input more_sms.json --user-id "usr_EXISTING_USER_ID" --user-stats










# 🚀 NEW: UNIFIED END-TO-END PIPELINE (SINGLE COMMAND)
# ===================================================

# Using existing user_id:
python3 run_complete_pipeline.py --input test_sms.json --user-id "usr_d25b8256_20250922_012726_045eb0fc" --create-indexes

# Using phone number (finds existing user or creates new):
python3 run_complete_pipeline.py --input test_sms.json --phone "+91-9876543210" --name "Test User" --create-indexes

# Creating new user with complete details:
python3 run_complete_pipeline.py --input test_sms.json --name "John Doe" --phone "+91-9876543210" --email "john@example.com" --create-indexes


#Add on data
python3 run_complete_pipeline.py --input test_sms_addon.json --phone "+919878483843" --create-indexes





# 📋 STEP-BY-STEP COMMANDS (MANUAL APPROACH)
# ==========================================

python3 user_manager.py --create --name "Test Working" --email "testworking@example.com" --phone "+91-9876543210"       

python3 sms_mongodb_uploader.py --input test_sms.json --user-id "usr_d25b8256_20250922_012726_045eb0fc" --create-indexes --stats 

python3 mongodb_pipeline.py --user-id "usr_d25b8256_20250922_012726_045eb0fc" --batch-size 2 --model "qwen3:8b"

python3 convert_transaction_dates.py --db pluto_money --source financial_transactions --dest user_financial_transactions







 uvicorn api_server:app --host 0.0.0.0 --port 8001 --reload