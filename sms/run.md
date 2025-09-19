

common 12001 port run team:
./run.sh

testing streamlit:
(venv) krishagrawal@Mac sms % streamlit run app.py


streamlit run app.py --server.port 3000










api for Query-Response sms-data:

uvicorn run_production_api:app --host 0.0.0.0 --port 8001

python3 run_production_api.py








# Check status
python batch_process_users.py --status-only

# Process all users  
python batch_process_users.py
