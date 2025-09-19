# 🚀 Team Setup Instructions

Quick setup guide for testing the SMS Transaction Dashboard.

## 📋 Prerequisites

- Python 3.8 or higher
- Git (for cloning the repository)

## ⚡ Quick Start (1-Minute Setup)

### 1. **Clone & Navigate**
```bash
git clone <repository-url>
cd moneybiology/DS/sms
```

### 2. **Setup Environment**
```bash
# Copy environment template
cp env_example.txt .env

# Make run script executable  
chmod +x run.sh
```

### 3. **Run the Dashboard**
```bash
./run.sh
```

That's it! The dashboard will be available at: **http://localhost:12001**

## 🔧 What the Script Does Automatically

- ✅ Creates virtual environment if needed
- ✅ Installs all dependencies
- ✅ Sets up environment variables
- ✅ Tests MongoDB connection
- ✅ Starts dashboard on port 12001
- ✅ Provides network access for team testing

## 🌐 Access URLs

- **Local**: http://localhost:12001
- **Network**: http://YOUR_IP:12001 (shown in terminal)

## 📊 Testing Data Sources

### Option 1: Real MongoDB Data ✅
- Uses production database: `pluto_money.financial_transactions`
- Select "MongoDB" in the dashboard sidebar
- Choose user from dropdown

### Option 2: Synthetic Test Data 🧪
- Generate test data: `cd test && python generate_synthetic_data.py`
- Select "Local File" in dashboard
- Upload generated JSON file

## 🛠 Troubleshooting

### Port Already in Use
```bash
./run.sh 12002  # Use different port
```

### MongoDB Connection Issues
- Check your internet connection
- Verify `.env` file has correct credentials
- Dashboard works with local files if MongoDB fails

### Python/Dependencies Issues
```bash
# Manual setup if needed
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp env_example.txt .env
streamlit run app.py --server.port 12001
```

### Virtual Environment Issues
```bash
# Remove and recreate
rm -rf venv
./run.sh  # Will recreate automatically
```

## 🎯 Testing Checklist

- [ ] Dashboard loads successfully
- [ ] MongoDB connection works
- [ ] Can select different users
- [ ] All sections display data:
  - [ ] Salary & Income Overview
  - [ ] Financial Health metrics
  - [ ] Monthly trends chart
  - [ ] Payment method analysis
  - [ ] Recurring transactions
  - [ ] Spending patterns

## 📞 Need Help?

<!-- streamlit run app.py --server.port 3000 -->

1. **Check the terminal output** - it shows detailed status
2. **Try different port**: `./run.sh 12003`
3. **Use test data** if MongoDB fails
4. **Contact the dev team** with error screenshots

## 🚨 Important Notes

- **Port 12001** is the default for team testing
- **MongoDB credentials** are pre-configured
- **All dependencies** install automatically
- **Works on Mac/Linux/WSL**
- **Network accessible** for team collaboration

---

**Happy Testing! 🎉**