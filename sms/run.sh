#!/bin/bash

# SMS Transaction Dashboard - Team Testing Script
# Port: 12001
# Usage: ./run.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 SMS Transaction Dashboard - Team Testing${NC}"
echo -e "${BLUE}============================================${NC}"

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo -e "${RED}❌ Error: app.py not found. Please run this script from the SMS project root directory.${NC}"
    exit 1
fi

# Set default port
PORT=${1:-12001}
echo -e "${YELLOW}📡 Server will run on port: ${PORT}${NC}"

# Check if port is available
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}❌ Error: Port $PORT is already in use.${NC}"
    echo -e "${YELLOW}💡 Try a different port: ./run.sh 12002${NC}"
    exit 1
fi

# Environment setup
echo -e "${YELLOW}🔧 Setting up environment...${NC}"

# Check if .env file exists, if not create from template
if [ ! -f ".env" ]; then
    if [ -f "env_example.txt" ]; then
        echo -e "${YELLOW}📝 Creating .env file from template...${NC}"
        cp env_example.txt .env
        echo -e "${GREEN}✅ .env file created. Please update it with your MongoDB credentials.${NC}"
    else
        echo -e "${YELLOW}📝 Creating default .env file...${NC}"
        cat > .env << EOF
# MongoDB Configuration
MONGODB_URI=mongodb+srv://divyamverma:geMnO2HtgXwOrLsW@cluster0.gzbouvi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
MONGODB_DATABASE=moneybiology
MONGODB_COLLECTION=sms_transactions

# Application Configuration
DEBUG=True
LOG_LEVEL=INFO

# Dashboard Configuration
DEFAULT_MAX_TRANSACTIONS=1000
CACHE_TIMEOUT=300

# Security (for production)
SECRET_KEY=your-secret-key-here
EOF
        echo -e "${GREEN}✅ Default .env file created. Please update MongoDB settings.${NC}"
    fi
fi

# Load environment variables
if [ -f ".env" ]; then
    echo -e "${YELLOW}🔑 Loading environment variables...${NC}"
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
fi

# Set additional environment variables for Streamlit
export STREAMLIT_SERVER_PORT=$PORT
export STREAMLIT_SERVER_ADDRESS=0.0.0.0
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
export STREAMLIT_SERVER_ENABLE_CORS=true
export STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# Check Python version
echo -e "${YELLOW}🐍 Checking Python version...${NC}"
python_version=$(python3 --version 2>&1)
echo -e "${GREEN}✅ $python_version${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo -e "${YELLOW}🔧 No virtual environment found. Creating one...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created.${NC}"
fi

# Activate virtual environment
if [ -d "venv" ]; then
    echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Check and install dependencies
echo -e "${YELLOW}📦 Checking dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    # Check if key packages are installed
    if ! python3 -c "import streamlit, pandas, numpy, plotly, pymongo" 2>/dev/null; then
        echo -e "${YELLOW}📦 Installing dependencies...${NC}"
        pip install -r requirements.txt
        echo -e "${GREEN}✅ Dependencies installed.${NC}"
    else
        echo -e "${GREEN}✅ Dependencies already installed.${NC}"
    fi
else
    echo -e "${RED}❌ requirements.txt not found!${NC}"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Check MongoDB connection (optional)
echo -e "${YELLOW}🔌 Testing MongoDB connection...${NC}"
cd "$(dirname "$0")" # Ensure we're in the script directory
python3 -c "
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
try:
    from data_loader import DataLoader
    loader = DataLoader()
    users, error = loader.get_available_users()
    if error:
        print('⚠️  MongoDB connection failed: ' + str(error))
        print('💡 You can still test with local JSON files')
    else:
        print('✅ MongoDB connection successful')
        print(f'📊 Found {len(users)} users in database')
except ImportError as e:
    print('⚠️  Import error: ' + str(e))
    print('💡 MongoDB connection test skipped - modules will load when app starts')
except Exception as e:
    print('⚠️  MongoDB test failed: ' + str(e))
    print('💡 You can still test with local JSON files')
" 2>/dev/null || echo -e "${YELLOW}⚠️  MongoDB connection test skipped${NC}"

# Clear any existing cache
echo -e "${YELLOW}🧹 Clearing Streamlit cache...${NC}"
rm -rf ~/.streamlit/cache 2>/dev/null || true

# Display team testing information
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}🎉 Ready for Team Testing!${NC}"
echo -e "${GREEN}============================================${NC}"
echo -e "${BLUE}📱 Application URL: ${GREEN}http://localhost:$PORT${NC}"

# Get network IP for macOS
NETWORK_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
if [ -n "$NETWORK_IP" ]; then
    echo -e "${BLUE}📱 Network URL: ${GREEN}http://$NETWORK_IP:$PORT${NC}"
else
    echo -e "${BLUE}📱 Network URL: ${GREEN}http://YOUR_IP:$PORT${NC}"
fi
echo -e "${BLUE}📊 Dashboard: ${GREEN}Financial Transaction Insights${NC}"
echo -e "${BLUE}🔧 Environment: ${GREEN}Development/Testing${NC}"
echo -e "${GREEN}============================================${NC}"

# Show quick testing tips
echo -e "${YELLOW}💡 Quick Testing Tips:${NC}"
echo -e "${YELLOW}  • Use MongoDB data source for real data${NC}"
echo -e "${YELLOW}  • Use Local File for synthetic testing data${NC}"
echo -e "${YELLOW}  • Check test/ directory for sample data${NC}"
echo -e "${YELLOW}  • Generate test data: cd test && python generate_synthetic_data.py${NC}"
echo -e "${YELLOW}  • Press Ctrl+C to stop the server${NC}"
echo -e "${YELLOW}============================================${NC}"

# Start the application
echo -e "${GREEN}🚀 Starting SMS Transaction Dashboard...${NC}"
echo -e "${BLUE}📡 Server starting on port $PORT...${NC}"

# Run Streamlit with proper configuration
streamlit run app.py \
    --server.port $PORT \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false \
    --server.enableCORS true \
    --server.enableXsrfProtection false \
    --theme.base "dark" \
    --theme.primaryColor "#FF6B6B" \
    --theme.backgroundColor "#0E1117" \
    --theme.secondaryBackgroundColor "#262730" \
    --theme.textColor "#FAFAFA"