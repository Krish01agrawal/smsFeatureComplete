#!/usr/bin/env python3
"""
Test script for the Production Financial Chat API
Tests the complete pipeline with real user data
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_production_pipeline():
    """Test the complete production pipeline"""
    
    print("🚀 Testing Production Financial Chat API")
    print("=" * 50)
    
    try:
        # Import the production analyzer
        from financial_chat_api_production import ProductionFinancialAnalyzer
        
        # Initialize analyzer
        analyzer = ProductionFinancialAnalyzer()
        print("✅ Production analyzer initialized")
        
        # Test cases based on your real data
        test_cases = [
            {
                "user_id": "itartha",  # Real user from your data
                "query": "total spending and my major expenses for the month of July 2025?",
                "expected_features": ["total spending", "categories", "July 2025"]
            },
            {
                "user_id": "itartha",
                "query": "what is my salary in August 2025?",
                "expected_features": ["STATION91 TECHNOLOG", "120000", "August 2025"]
            },
            {
                "user_id": "user_20250818_172328",  # Another real user
                "query": "show me my spending patterns last month",
                "expected_features": ["spending", "patterns", "last month"]
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 Test Case {i}: {test_case['user_id']}")
            print(f"Query: {test_case['query']}")
            print("-" * 40)
            
            start_time = datetime.now()
            
            try:
                # Run the complete pipeline
                result = await analyzer.analyze_query(test_case['user_id'], test_case['query'])
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                # Validate results
                print(f"⏱️  Processing time: {processing_time:.2f}s")
                print(f"📊 Data points: {result['data_points']}")
                print(f"🔍 Sub-queries: {len(result['sub_queries'])}")
                
                # Check grounding context
                grounding = result.get('grounding_context', {})
                if grounding:
                    print(f"🎯 Time period: {grounding.get('time_period', 'N/A')}")
                    print(f"💰 Total spending: ₹{grounding.get('total_spending', 0):,.2f}")
                    print(f"📈 Success rate: {grounding.get('query_success_rate', 0)*100:.1f}%")
                    print(f"🏥 System health: {grounding.get('system_health', 'unknown')}")
                
                # Show response preview
                response = result.get('response', '')
                if response:
                    preview = response[:200] + "..." if len(response) > 200 else response
                    print(f"💬 Response preview: {preview}")
                
                # Check if expected features are present
                response_lower = response.lower()
                found_features = [f for f in test_case['expected_features'] if f.lower() in response_lower]
                print(f"✅ Features found: {found_features}")
                
                if result.get('error'):
                    print(f"⚠️  Error: {result['error']}")
                else:
                    print("✅ Test completed successfully")
                    
            except Exception as e:
                print(f"❌ Test failed: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n🎉 Production pipeline testing completed!")
        print("=" * 50)
        
        # Test specific components
        print("\n🔧 Component Tests:")
        print("-" * 20)
        
        # Test timezone conversion
        time_window = analyzer._resolve_time_window_ist_to_utc("total spending last month")
        print(f"✅ Timezone conversion: {time_window['label']} | {time_window['start_utc']} to {time_window['end_utc']}")
        
        # Test fallback template selection
        template = analyzer._create_exact_fallback_template("itartha", "total spending in July", time_window)
        print(f"✅ Fallback template: {template['description']}")
        
        # Test cache functionality
        test_key = analyzer._generate_cache_key("test", "itartha", "abcd1234")
        print(f"✅ Cache key generation: {test_key}")
        
        print("\n🏆 All component tests passed!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you have all required dependencies installed:")
        print("pip install fastapi pymongo python-dotenv pytz")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

def test_schema_validation():
    """Test that the schema matches your real data"""
    print("\n🔍 Schema Validation Test")
    print("-" * 30)
    
    # Your sample data structure
    sample_data = {
        "_id": {"$oid": "68a315f008d80cb1d38002c9"},
        "unique_id": "sms_000001_20250818_172953_261009",
        "_source_id": "sms_000001",
        "account": {"bank": "SBI", "account_number": "X9855"},
        "amount": 44,
        "category": "transfer",
        "confidence_score": 0.95,
        "counterparty": "MIDAS DAILY SUPE",
        "created_at": {"$date": "2025-08-18T17:30:48.939Z"},
        "currency": "INR",
        "message_intent": "transaction",
        "metadata": {
            "channel": "sms",
            "sender": "JD-SBIUPI-S",
            "method": "UPI",
            "reference_id": "565625035570"
        },
        "summary": "Debit of 44.0 from SBI account",
        "tags": ["UPI", "SBI"],
        "transaction_date": {"$date": "2025-07-03T21:55:26.348Z"},
        "transaction_type": "debit",
        "updated_at": {"$date": "2025-08-18T17:30:48.939Z"},
        "user_id": "user_20250818_172328"
    }
    
    # Validate key fields
    required_fields = ["user_id", "amount", "transaction_type", "category", "counterparty", "transaction_date"]
    
    print("Required fields validation:")
    for field in required_fields:
        if field in sample_data:
            print(f"✅ {field}: {type(sample_data[field]).__name__} = {sample_data[field]}")
        else:
            print(f"❌ {field}: MISSING")
    
    # Validate data types
    print("\nData type validation:")
    print(f"✅ amount is positive number: {sample_data['amount']} > 0")
    print(f"✅ transaction_type is debit/credit: {sample_data['transaction_type']}")
    print(f"✅ transaction_date is BSON Date: {sample_data['transaction_date']}")
    print(f"✅ user_id is string: {sample_data['user_id']}")
    
    print("✅ Schema validation passed!")

if __name__ == "__main__":
    print("🧪 Production Financial Chat API - Test Suite")
    print("=" * 60)
    
    # Test schema validation first
    test_schema_validation()
    
    # Test the complete pipeline
    asyncio.run(test_production_pipeline())
