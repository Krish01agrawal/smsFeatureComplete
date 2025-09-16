user_sms.json    -->      user_financial.json

user_financial.json     -->         structured_user_finData.json

batch_processing sms to llm





# Step 1: Filter (from your 5,072 SMS)(raw sms/email)
python3 sms_financial_filter.py sms_data.json -o filtered_financial.json

# Step 2: Extract array (extract fin_data json)
python3 extract_financial_array.py filtered_financial.json -o financial_array.json  

# Step 3: Process with AI (Data to information -> stored in mongodb)
python3 main.py --input financial_array.json --output final_results.json --failures complete_failures.ndjson



python3 main.py --input test_realtime.json --output test_results_realtime.json --failures test_failures_realtime.ndjson --batch-size 1 --parallel-batches 1


















# 1. First, upload fresh SMS data
python3 sms_mongodb_uploader.py --input test_sms.json

python3 sms_mongodb_uploader.py --input "assets/sms_data/sms_data_divyam.json" --user-id "test_user_divyam" --batch-size 100 --create-indexes --stats




# 2. Run complete pipeline
python3 mongodb_pipeline.py --limit 100 --batch-size 10

python3 mongodb_pipeline.py --user-id "test_user_divyam" --limit 50 --batch-size 2












# 1. Upload raw SMS data
python3 sms_mongodb_uploader.py --input test_sms.json --user-id "test_user_divyam" --create-indexes --stats

# 2. Run complete pipeline (THE MOST IMPORTANT COMMAND)
python3 mongodb_pipeline.py --user-id "test_user_divyam" --batch-size 5 --model "qwen3:8b"

# 3. (Optional) Convert dates to BSON format
python3 convert_transaction_dates.py --db pluto_money --source financial_transactions --dest user_financial_transactions

# 4. Verify results
python3 -c "from mongodb_operations import MongoDBOperations; mongo = MongoDBOperations(); print('Final transactions:', mongo.transactions_collection.count_documents({'user_id': 'test_user_divyam'})); mongo.close_connection()"