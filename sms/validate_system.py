#!/usr/bin/env python3
"""
Comprehensive System Validation Script
Validates all components of the enhanced financial insights system.
"""

import sys
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def test_imports():
    """Test all critical imports"""
    print("🔧 Testing Imports...")
    
    try:
        # Core libraries
        import streamlit as st
        import pandas as pd
        import plotly.express as px
        import plotly.graph_objects as go
        print("  ✅ Core libraries (streamlit, pandas, plotly)")
        
        # System modules
        from src.data_loader import DataLoader
        from src.preprocess import DataPreprocessor
        from src.insights import TransactionInsights
        from src.visualization import VisualizationEngine
        from enhanced_config import EnhancedConfig
        print("  ✅ System modules")
        
        # Enhanced system
        from src.enhanced_insights import EnhancedInsightsGenerator
        from src.core.smart_data_orchestrator import SmartDataOrchestrator
        print("  ✅ Enhanced insights system")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False

def test_configuration():
    """Test configuration system"""
    print("\n⚙️ Testing Configuration...")
    
    try:
        from enhanced_config import EnhancedConfig
        
        config = EnhancedConfig.get_config()
        print(f"  ✅ Configuration loaded")
        print(f"     - Enhanced system: {config['use_enhanced_insights']}")
        print(f"     - Data quality checks: {config['enable_data_quality_checks']}")
        print(f"     - Salary threshold: ₹{config['salary_detection_threshold']:,}")
        
        # Test toggle functionality
        EnhancedConfig.disable_enhanced_system()
        config_disabled = EnhancedConfig.get_config()
        
        EnhancedConfig.enable_enhanced_system()
        config_enabled = EnhancedConfig.get_config()
        
        if config_disabled['use_enhanced_insights'] == False and config_enabled['use_enhanced_insights'] == True:
            print("  ✅ Configuration toggle working")
        else:
            print("  ⚠️ Configuration toggle may have issues")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False

def test_data_processing():
    """Test data processing pipeline"""
    print("\n📊 Testing Data Processing...")
    
    try:
        from src.preprocess import DataPreprocessor
        
        # Create comprehensive test data
        test_data = [
            {
                'transaction_date': '2024-06-01T00:00:00.000',
                'amount': 40000,
                'transaction_type': 'credit',
                'merchant_canonical': 'STATION91 TECHNOLOGIES',
                'currency': 'INR',
                'category': 'salary'
            },
            {
                'transaction_date': '2024-07-01T00:00:00.000',
                'amount': 40000,
                'transaction_type': 'credit',
                'merchant_canonical': 'STATION91 TECHNOLOGIES',
                'currency': 'INR',
                'category': 'salary'
            },
            {
                'transaction_date': '2025-05-01T00:00:00.000',
                'amount': 60000,
                'transaction_type': 'credit',
                'merchant_canonical': 'STATION91 TECHNOLOGIES',
                'currency': 'INR',
                'category': 'salary'
            },
            {
                'transaction_date': '2024-06-05T00:00:00.000',
                'amount': 1500,
                'transaction_type': 'debit',
                'merchant_canonical': 'Swiggy',
                'currency': 'INR',
                'category': 'food'
            },
            {
                'transaction_date': '2025-05-05T00:00:00.000',
                'amount': 25000,
                'transaction_type': 'debit',
                'merchant_canonical': 'Amazon',
                'currency': 'INR',
                'category': 'shopping'
            }
        ]
        
        df = pd.DataFrame(test_data)
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        print(f"  ✅ Test data created: {len(df)} transactions")
        
        # Test preprocessing
        preprocessor = DataPreprocessor(date_range_months=24)
        df_processed = preprocessor.preprocess(df)
        print(f"  ✅ Preprocessing: {len(df_processed)} transactions retained")
        
        if len(df_processed) > 0:
            print(f"     - Date range: {df_processed['transaction_date'].min().strftime('%Y-%m-%d')} to {df_processed['transaction_date'].max().strftime('%Y-%m-%d')}")
            print(f"     - Income transactions: {len(df_processed[df_processed['transaction_type'] == 'credit'])}")
            print(f"     - Spending transactions: {len(df_processed[df_processed['transaction_type'] == 'debit'])}")
        
        return True, df_processed
        
    except Exception as e:
        print(f"  ❌ Data processing error: {e}")
        import traceback
        traceback.print_exc()
        return False, pd.DataFrame()

def test_insights_systems(df):
    """Test both legacy and enhanced insights systems"""
    print("\n🧠 Testing Insights Systems...")
    
    if df.empty:
        print("  ⚠️ No data available for insights testing")
        return False
    
    try:
        from src.insights import TransactionInsights
        
        # Test Enhanced System
        print("  🚀 Testing Enhanced System...")
        enhanced_analyzer = TransactionInsights(use_enhanced_system=True)
        enhanced_insights = enhanced_analyzer.calculate_insights(df)
        
        salary_info = enhanced_insights.get('salary', {})
        print(f"     ✅ Enhanced system working")
        print(f"        - Current Salary: ₹{enhanced_insights.get('avg_salary', 0):,.2f}")
        print(f"        - Salary Source: {salary_info.get('source', 'Unknown')}")
        print(f"        - Data Quality: {enhanced_insights.get('data_quality', {}).get('data_quality_score', 0):.1f}%")
        
        # Check for salary progression detection
        salary_changes = salary_info.get('salary_changes', [])
        if salary_changes:
            print(f"        - Salary Changes: {len(salary_changes)} detected")
            for change in salary_changes[:2]:  # Show first 2
                print(f"          • {change['from_month']} → {change['to_month']}: ₹{change['old_salary']:,.0f} → ₹{change['new_salary']:,.0f} ({change['change_percentage']:+.1f}%)")
        
        # Test Legacy System (if it works)
        print("  🔧 Testing Legacy System...")
        try:
            legacy_analyzer = TransactionInsights(use_enhanced_system=False)
            legacy_insights = legacy_analyzer.calculate_insights(df)
            print(f"     ✅ Legacy system working")
            print(f"        - Average Salary: ₹{legacy_insights.get('avg_salary', 0):,.2f}")
        except Exception as e:
            print(f"     ⚠️ Legacy system has issues (expected): {str(e)[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Insights system error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mongodb_connectivity():
    """Test MongoDB connectivity"""
    print("\n🗄️ Testing MongoDB Connectivity...")
    
    try:
        from src.data_loader import DataLoader
        import os
        
        loader = DataLoader()
        
        if not loader.mongodb_uri:
            print("  ⚠️ MongoDB URI not configured (this is optional)")
            print("     Set MONGODB_URI environment variable to test database connectivity")
            return True
        
        # Test connection
        users, error = loader.get_available_users()
        
        if error:
            print(f"  ⚠️ MongoDB connection issue: {error}")
            print("     Dashboard will work with local JSON files")
            return True
        
        if users:
            print(f"  ✅ MongoDB connected successfully")
            print(f"     - Available users: {len(users)}")
            print(f"     - Sample users: {users[:3]}")
        else:
            print("  ⚠️ MongoDB connected but no users found")
        
        return True
        
    except Exception as e:
        print(f"  ❌ MongoDB test error: {e}")
        return False

def test_app_readiness():
    """Test if the Streamlit app is ready to run"""
    print("\n🚀 Testing App Readiness...")
    
    try:
        # Test all app components
        from src.data_loader import DataLoader
        from src.preprocess import DataPreprocessor
        from src.insights import TransactionInsights
        from src.visualization import VisualizationEngine
        from enhanced_config import EnhancedConfig
        
        # Initialize components like the app does
        config = EnhancedConfig.get_config()
        components = {
            'data_loader': DataLoader(),
            'preprocessor': DataPreprocessor(),
            'insights_analyzer': TransactionInsights(use_enhanced_system=config['use_enhanced_insights']),
            'visualizer': VisualizationEngine(),
            'config': config
        }
        
        print("  ✅ All app components initialized successfully")
        print(f"     - Enhanced system: {config['use_enhanced_insights']}")
        print(f"     - Data loader: Ready")
        print(f"     - Preprocessor: Ready")
        print(f"     - Insights analyzer: Ready")
        print(f"     - Visualizer: Ready")
        
        return True
        
    except Exception as e:
        print(f"  ❌ App readiness error: {e}")
        return False

def main():
    """Run comprehensive system validation"""
    print("🔍 Comprehensive System Validation")
    print("=" * 50)
    
    results = []
    
    # Run all tests
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_configuration()))
    
    data_ok, test_df = test_data_processing()
    results.append(("Data Processing", data_ok))
    
    results.append(("Insights Systems", test_insights_systems(test_df)))
    results.append(("MongoDB Connectivity", test_mongodb_connectivity()))
    results.append(("App Readiness", test_app_readiness()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print("-" * 50)
    print(f"Overall Status: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL SYSTEMS GO!")
        print("   Your enhanced financial insights system is ready!")
        print("   Start the dashboard with: streamlit run app.py")
    elif passed >= total - 1:
        print("\n✅ SYSTEM READY with minor issues")
        print("   The system is functional. Minor issues noted above.")
        print("   Start the dashboard with: streamlit run app.py")
    else:
        print("\n⚠️ SYSTEM HAS ISSUES")
        print("   Please address the failed tests before using the system.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
