# SMS Transaction Analysis Dashboard

A comprehensive financial transaction analysis system that can load data from MongoDB or local JSON files, providing insights into spending patterns, merchant relationships, and recurring transactions.

## 🚀 Features

- **Dual Data Sources**: MongoDB integration + Local JSON file support
- **User-Specific Analysis**: Filter transactions by user ID
- **Interactive Dashboard**: Streamlit-based web interface
- **Advanced Analytics**: 
  - Daily spend trends
  - Top merchants analysis
  - Recurring transaction detection
  - Market basket analysis (association rules)
- **Real-time Data**: Direct MongoDB connectivity
- **Performance Optimization**: Configurable transaction limits

## 📋 Prerequisites

- Python 3.8+
- MongoDB Atlas account (for cloud database)
- MongoDB connection string

## 🛠️ Installation

1. **Clone and navigate to the project**:
   ```bash
   cd DS/sms
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up MongoDB connection**:
   Create a `.env` file in the project directory:
   ```bash
   # Copy the example file
   cp env_example.txt .env
   
   # Edit .env file with your MongoDB connection string
   MONGODB_URI=mongodb+srv://username:password@cluster0.swuj2.mongodb.net/pluto_money?retryWrites=true&w=majority
   ```

## 🔧 Configuration

### MongoDB Connection String Format
```
mongodb+srv://<username>:<password>@<cluster-url>/<database>?retryWrites=true&w=majority
```

### Environment Variables
- `MONGODB_URI`: Your MongoDB Atlas connection string

## 🧪 Testing

### Test MongoDB Connection
```bash
python test_mongodb_connection.py
```

### Test Specific User
```bash
python test_mongodb_connection.py "688926db7738fbca7e430468"
```

## 🚀 Usage

### Start the Dashboard
```bash
streamlit run transaction_insights_dashboard.py
```

### Generate Synthetic Data (Optional)
```bash
python generate_synthetic_data.py
```

## 📊 Dashboard Features

### Data Source Selection
- **MongoDB**: Connect to your live database
- **Local JSON**: Use synthetic data for testing

### MongoDB Mode Features
- **User Selection**: Choose from available users in database
- **Transaction Limit**: Control data load size for performance
- **Real-time Data**: Live connection to MongoDB

### Analytics Provided
1. **Key Metrics**:
   - Total transactions count
   - Total spend amount
   - Average transaction value

2. **Daily Spend Trend**:
   - Line chart showing spending patterns over time

3. **Top Merchants**:
   - Bar chart of highest spending merchants

4. **Recurring Transactions**:
   - Detection of 30-day interval patterns (subscriptions/bills)

5. **Association Rules**:
   - Market basket analysis showing merchant relationships

## 📁 Project Structure

```
DS/sms/
├── transaction_insights_dashboard.py  # Main dashboard application
├── generate_synthetic_data.py         # Synthetic data generator
├── test_mongodb_connection.py         # Connection testing script
├── requirements.txt                   # Python dependencies
├── env_example.txt                    # Environment variables template
├── synthetic_transactions.json        # Generated test data
├── README.md                          # This file
└── src/
    ├── mongodb_loader.py              # MongoDB connectivity module
    ├── data_loader.py                 # JSON data loading utility
    └── feature_engineering.py         # Feature engineering functions
```

## 🔍 Data Schema

### MongoDB Collection: `financial_transactions`

```json
{
  "_id": "ObjectId",
  "transaction_id": "string",
  "account_number": "string",
  "amount": "number",
  "bank_name": "string",
  "merchant_canonical": "string",
  "merchant_original": "string",
  "transaction_date": "date",
  "transaction_type": "string",
  "user_id": "string",
  "sms_message": "string",
  "source": "sms",
  // ... additional fields
}
```

## 🛡️ Security

- Connection strings stored in environment variables
- No hardcoded credentials
- Secure MongoDB Atlas connection

## 🔧 Troubleshooting

### Connection Issues
1. **Check MongoDB URI**: Verify connection string format
2. **Network Access**: Ensure IP is whitelisted in MongoDB Atlas
3. **Credentials**: Verify username/password

### Data Loading Issues
1. **User ID**: Ensure user exists in database
2. **Collection Name**: Verify `financial_transactions` collection exists
3. **Data Format**: Check transaction document structure

### Performance Issues
1. **Limit Transactions**: Reduce max transactions in dashboard
2. **Indexing**: Add indexes on `user_id` and `transaction_date` fields
3. **Connection Pooling**: MongoDB driver handles connection pooling automatically

## 📈 Performance Optimization

### MongoDB Indexes (Recommended)
```javascript
// Create indexes for better performance
db.financial_transactions.createIndex({"user_id": 1})
db.financial_transactions.createIndex({"transaction_date": 1})
db.financial_transactions.createIndex({"user_id": 1, "transaction_date": -1})
```

### Dashboard Settings
- **Transaction Limit**: Start with 1000, increase as needed
- **Caching**: Streamlit caches data automatically
- **Connection Pooling**: Handled by PyMongo driver

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is part of the MoneyBiology platform.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Run the test script
3. Verify MongoDB connection
4. Check data format compatibility 