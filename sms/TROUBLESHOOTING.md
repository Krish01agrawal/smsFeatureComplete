# 🔧 Troubleshooting Guide

## Common Python Errors and Solutions

### 1. Import Errors

#### Error: `ModuleNotFoundError: No module named 'src'`
**Solution:**
```bash
# Make sure you're in the correct directory
cd DS/sms

# Verify the directory structure
ls -la src/

# Run with proper path
python3 -c "import sys; sys.path.append('.'); from src.insights import TransactionInsights"
```

#### Error: `ModuleNotFoundError: No module named 'streamlit'`
**Solution:**
```bash
# Install missing dependencies
pip3 install -r requirements.txt

# Or install individually
pip3 install streamlit pandas plotly pymongo python-dotenv mlxtend rapidfuzz
```

### 2. Streamlit Errors

#### Error: `streamlit: command not found`
**Solution:**
```bash
# Install streamlit
pip3 install streamlit

# Or use python module
python3 -m streamlit run app.py
```

#### Error: Streamlit app won't start
**Solution:**
```bash
# Check if port is in use
lsof -i :8501

# Use different port
streamlit run app.py --server.port 8502

# Or use the provided run script
./run.sh
```

### 3. MongoDB Errors

#### Error: `ServerSelectionTimeoutError`
**Solution:**
```bash
# Check .env file exists
ls -la .env

# Copy from template if missing
cp env_example.txt .env

# Edit with your MongoDB URI
nano .env
```

#### Error: `No module named 'pymongo'`
**Solution:**
```bash
pip3 install pymongo
```

### 4. Data Processing Errors

#### Error: `Empty DataFrame after preprocessing`
**Solution:**
The system now uses 24-month date range by default. If you still get empty data:

```python
# Use longer date range
from src.preprocess import DataPreprocessor
preprocessor = DataPreprocessor(date_range_months=36)  # 3 years
```

#### Error: `KeyError: 'payment_method'`
**Solution:**
This is fixed in the enhanced system. Make sure you're using:
```python
analyzer = TransactionInsights(use_enhanced_system=True)
```

### 5. Enhanced System Errors

#### Error: Issues with enhanced insights
**Solution:**
```bash
# Test the enhanced system
python3 demo_enhanced_insights.py

# Validate the system
python3 validate_system.py

# Switch to legacy if needed
from enhanced_config import EnhancedConfig
EnhancedConfig.disable_enhanced_system()
```

### 6. Performance Issues

#### Error: App is slow or crashes
**Solution:**
```bash
# Limit transaction count
# In MongoDB source, set max transactions to 1000

# Or in code:
df_limited = df.head(1000)  # Limit to 1000 transactions
```

### 7. Dependency Issues

#### Error: `rapidfuzz not available`
**Solution:**
```bash
# Install rapidfuzz for better fuzzy matching
pip3 install rapidfuzz

# This is optional - system works without it
```

## Quick Fixes

### Reset Everything
```bash
# Remove cache and restart
rm -rf __pycache__ src/__pycache__
python3 validate_system.py
```

### Clean Installation
```bash
# Remove virtual environment if exists
rm -rf venv

# Create new virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Test system
python3 validate_system.py
```

### Emergency Fallback
```bash
# Use legacy system only
python3 -c "
from enhanced_config import EnhancedConfig
EnhancedConfig.disable_enhanced_system()
print('Switched to legacy system')
"
```

## Diagnostic Commands

### Check System Status
```bash
python3 validate_system.py
```

### Test Core Components
```bash
python3 -c "
import sys
sys.path.append('.')
from src.insights import TransactionInsights
analyzer = TransactionInsights()
print('✅ System working')
"
```

### Test Data Processing
```bash
python3 demo_enhanced_insights.py
```

### Check Dependencies
```bash
python3 -c "
import pandas as pd
import streamlit as st
import plotly.express as px
import pymongo
print('✅ All dependencies available')
"
```

## Environment Variables

Make sure your `.env` file contains:
```bash
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database
```

## Port Issues

If default port (8501) is busy:
```bash
# Use different port
streamlit run app.py --server.port 8502

# Or kill existing streamlit processes
pkill -f streamlit
```

## Contact Support

If you're still having issues, please provide:

1. **Exact error message** (copy-paste the full error)
2. **What you were trying to do** (start app, load data, etc.)
3. **Your environment**:
   ```bash
   python3 --version
   pip3 list | grep -E "(streamlit|pandas|plotly|pymongo)"
   ```
4. **Steps to reproduce** the error

## Quick Start (If All Else Fails)

```bash
# 1. Go to the correct directory
cd DS/sms

# 2. Install dependencies
pip3 install streamlit pandas plotly pymongo python-dotenv mlxtend rapidfuzz

# 3. Test the system
python3 validate_system.py

# 4. Start the app
python3 -m streamlit run app.py

# 5. If that fails, try:
python3 -c "
import sys
sys.path.append('.')
from enhanced_config import EnhancedConfig
EnhancedConfig.disable_enhanced_system()
print('Using legacy system')
"
python3 -m streamlit run app.py
```
