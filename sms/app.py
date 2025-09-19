"""
Modular Streamlit app for SMS transaction analysis.
Uses the new modular architecture for better maintainability and scalability.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import os
from datetime import datetime

# Import our modular components
from src.data_loader import DataLoader
from src.mongodb_loader import MongoDBLoader
from src.preprocess import DataPreprocessor
from src.insights import TransactionInsights
from src.visualization import VisualizationEngine
from enhanced_config import EnhancedConfig

# Force single connection mode at app startup (ONE TIME ONLY)
try:
    from src.mongodb_connection_manager import force_single_connection
    force_single_connection()  # This will only run once due to global flag
except Exception as e:
    print(f"⚠️ Could not enable single connection mode: {e}")

# Configure page
st.set_page_config(
    page_title="Financial Transaction Insights Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize components with Streamlit caching
@st.cache_resource
def initialize_components():
    """Initialize all analysis components with caching to prevent repeated connections."""
    config = EnhancedConfig.get_config()
    
    # Initialize MongoDB loader if connection is available
    mongodb_loader = None
    try:
        mongodb_loader = MongoDBLoader()
        
        # Log MongoDB connection details for debugging
        connection_details = {
            'connection_string': mongodb_loader.connection_string[:50] + '...' if mongodb_loader.connection_string else 'None',
            'database': mongodb_loader.db_name,
            'collection': mongodb_loader.collection_name,
            'full_collection_path': f"{mongodb_loader.db_name}.{mongodb_loader.collection_name}"
        }
        
        st.success("✅ MongoDB connection established and cached")
        st.info(f"📊 **Data Source**: `{connection_details['full_collection_path']}`")
        st.code(f"Connection: {connection_details['connection_string']}\nDatabase: {connection_details['database']}\nCollection: {connection_details['collection']}")
        
    except Exception as e:
        st.warning(f"⚠️ MongoDB connection not available: {e}")
    
    # Show single connection status (no more forcing - already done at startup)
    try:
        from src.mongodb_connection_manager import mongodb_manager
        
        connection_stats = mongodb_manager.get_connection_stats()
        st.success(f"✅ MongoDB Connections: {connection_stats['total_connections']} active (single connection mode)")
        
        # Show connection details for debugging
        if connection_stats['connection_info']:
            for conn_id, info in connection_stats['connection_info'].items():
                st.info(f"🔗 Single Connection: `{conn_id}` serves all components")
        
    except Exception as e:
        st.warning(f"⚠️ Could not get connection stats: {e}")
    
    return {
        'data_loader': DataLoader(),
        'mongodb_loader': mongodb_loader,
        'preprocessor': DataPreprocessor(),
        'insights_analyzer': TransactionInsights(use_enhanced_system=config['use_enhanced_insights'], user_id=st.session_state.get('user_id')),
        'visualizer': VisualizationEngine(),
        'config': config
    }

def main():
    """Main application function."""
    st.title("💰 Financial Transaction Insights Dashboard")
    st.markdown("### Advanced SMS Transaction Analysis with Modular Architecture")
    
    # Initialize components
    components = initialize_components()
    
    # Sidebar configuration
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # Enhanced insights toggle
        # FORCE ENHANCED INSIGHTS SYSTEM - No user choice needed, always use the best system
        use_enhanced = True  # Always use the superior Enhanced Insights System
        st.info("🚀 **Enhanced Insights System** - Using our most advanced AI-powered analysis")
        
        # Date range selection for analysis
        st.subheader("📅 Analysis Period")
        analysis_months = st.selectbox(
            "Historical Data Range",
            options=["All Time", 3, 6, 12, 18, 24, 36],
            index=0,  # Default to All Time for complete data
            help="Select analysis period: '3 months' = last 3 months from today, '6 months' = last 6 months from today, etc. 'All Time' = complete transaction history. You get ALL transactions for the selected period - no limits!"
        )
        
        # Convert "All Time" to 0 for the preprocessor
        if analysis_months == "All Time":
            analysis_months = 0
        
        # Store in session state for use in data processing
        if analysis_months != st.session_state.get('analysis_months', 0):  # Default to 0 (All Time)
            st.session_state['analysis_months'] = analysis_months
            # Clear processed data to force reprocessing with new date range
            if 'df' in st.session_state:
                del st.session_state['df']
            if 'raw_df' in st.session_state:
                # If we have raw data, reprocess it immediately with new date range AND STORE IT
                with st.spinner(f"🔄 Reprocessing data for {analysis_months}-month analysis..."):
                    # CRITICAL: Clear all caches to ensure fresh code
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    
                    from src.preprocess import DataPreprocessor
                    user_id = st.session_state.get('user_id')
                    
                    # CRITICAL: Force reload of preprocessing module to get latest fixes
                    import importlib
                    import src.preprocess
                    importlib.reload(src.preprocess)
                    
                    # CRITICAL FIX: Enable storage to update processed collection with latest code
                    preprocessor = DataPreprocessor(date_range_months=analysis_months, store_processed_data=True)
                    processed_df = preprocessor.preprocess(st.session_state['raw_df'], user_id=user_id)
                    st.session_state['df'] = processed_df
                    
                    st.success(f"💾 Successfully processed and stored {len(processed_df)} transactions")
                    st.info("🔄 Fresh data now available - dashboard will refresh automatically")
                    
                    # Force immediate refresh to show new data
                    st.rerun()
                if analysis_months == 0:
                    st.success(f"✅ Complete data reprocessed! Now showing ALL {len(processed_df)} transactions (entire history).")
                else:
                    st.success(f"✅ Complete data reprocessed! Now showing ALL {len(processed_df)} transactions from last {analysis_months} months.")
            else:
                if analysis_months == 0:
                    st.info(f"📅 Analysis period changed to All Time. Please reload data to apply changes.")
                else:
                    st.info(f"📅 Analysis period changed to {analysis_months} months. Please reload data to apply changes.")
        
        # Show current data info if available
        if 'df' in st.session_state and not st.session_state['df'].empty:
            current_months = st.session_state.get('analysis_months', 0)  # Default to All Time
            user_id = st.session_state.get('user_id', 'Unknown')
            # Display analysis period info
            if current_months == 0:
                st.info(f"📊 Showing ALL {len(st.session_state['df'])} transactions (complete history)")
            else:
                st.info(f"📊 Showing ALL {len(st.session_state['df'])} transactions from last {current_months} months (complete data for period)")
            
            # Simple refresh data button (clean slate processing)
            if st.button("🔄 Refresh Data", help="Reload and reprocess all data from MongoDB", type="primary"):
                # CRITICAL: Clear all Streamlit caches to ensure we use the latest code
                st.cache_data.clear()
                st.cache_resource.clear()
                if 'user_id' in st.session_state and 'mongodb_loader' in st.session_state:
                    with st.spinner(f"🧹 Clean slate processing for user {user_id}..."):
                        try:
                            # Get MongoDB loader from session or create new one
                            mongodb_loader = st.session_state.get('mongodb_loader')
                            if not mongodb_loader:
                                mongodb_loader = components.get('mongodb_loader')
                            
                            if mongodb_loader:
                                # Load fresh raw data
                                st.info("📥 Loading fresh raw data from MongoDB...")
                                df = mongodb_loader.get_user_transactions(user_id, force_raw_data=True)  # FIXED: Remove limit to get all transactions
                                
                                if not df.empty:
                                    st.info("🧹 Performing clean slate processing...")
                                    
                                    # CRITICAL: Force reload of preprocessing module to get latest fixes
                                    import importlib
                                    import src.preprocess
                                    importlib.reload(src.preprocess)
                                    
                                    # Clean slate processing with latest code
                                    from src.preprocess import DataPreprocessor
                                    preprocessor = DataPreprocessor(date_range_months=current_months, store_processed_data=True)
                                    processed_df = preprocessor.preprocess(df, user_id=user_id)
                                    
                                    # Update session state
                                    st.session_state['df'] = processed_df
                                    st.session_state['raw_df'] = df
                                    
                                    st.success(f"🎉 Clean slate processing completed! {len(df)} raw → {len(processed_df)} processed transactions")
                                    st.rerun()
                                else:
                                    st.error(f"❌ No data found for user {user_id}")
                            else:
                                st.error("❌ MongoDB loader not available")
                        except Exception as e:
                            st.error(f"❌ Refresh failed: {e}")
                else:
                    st.error("❌ No user selected. Please load data first.")
            
        if use_enhanced != components['config']['use_enhanced_insights']:
            if use_enhanced:
                EnhancedConfig.enable_enhanced_system()
                st.success("✅ Enhanced insights system enabled!")
            else:
                EnhancedConfig.disable_enhanced_system()
                st.info("ℹ️ Using legacy system for backward compatibility")
            # Force reinitialization of components with new config
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()
        
        # Data source selection
        data_source = st.selectbox(
            "Choose Data Source",
            ["Local JSON File", "MongoDB"],
            help="Select data source for analysis"
        )
        
        if data_source == "MongoDB":
            if components['mongodb_loader']:
                configure_mongodb_source(components['mongodb_loader'])
            else:
                st.error("❌ MongoDB connection not available. Please check your MongoDB configuration.")
        else:
            configure_local_source(components['data_loader'])
    
    # Main content area
    if 'df' in st.session_state and not st.session_state['df'].empty:
        # Show current data source at the top of analysis
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if 'data_source' in st.session_state:
                st.info(f"📊 **Current Data Source**: `{st.session_state['data_source']}` | **User**: `{st.session_state.get('user_id', 'Unknown')}` | **Transactions**: {len(st.session_state['df'])}")
            else:
                st.info(f"📊 **Current Data**: {len(st.session_state['df'])} transactions for user `{st.session_state.get('user_id', 'Unknown')}`")
        
        # Keep it simple - no confusing buttons in main area
        
        display_analysis(components, st.session_state['df'])
    else:
        st.info("👆 Please configure and load data from the sidebar to begin analysis.")

def configure_mongodb_source(mongodb_loader):
    """Configure MongoDB data source."""
    st.subheader("📊 MongoDB Settings")
    
    # Check MongoDB connection
    if not mongodb_loader.connection_string:
        st.error("❌ MongoDB URI not configured!")
        st.info("Please set MONGODB_URI environment variable")
        st.code("MONGODB_URI=mongodb+srv://divyamverma:geMnO2HtgXwOrLsW@cluster0.gzbouvi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
        return
    
    # Manual database/collection configuration
    with st.expander("🔧 Advanced Database Configuration"):
        st.subheader("🔍 Current Configuration")
        st.json({
            "connection_string": mongodb_loader.connection_string[:80] + "..." if mongodb_loader.connection_string else "None",
            "database": mongodb_loader.db_name,
            "collection": mongodb_loader.collection_name,
            "full_path": f"{mongodb_loader.db_name}.{mongodb_loader.collection_name}"
        })
        
        col1, col2 = st.columns(2)
        with col1:
            manual_db = st.text_input(
                "Database Name",
                value=mongodb_loader.db_name,
                help="Manual database name override"
            )
        with col2:
            manual_collection = st.text_input(
                "Collection Name", 
                value=mongodb_loader.collection_name,
                help="Manual collection name override"
            )
        
        if st.button("🔧 Apply Manual Configuration", type="secondary"):
            try:
                # Update the MongoDB loader configuration
                mongodb_loader.db_name = manual_db
                mongodb_loader.collection_name = manual_collection
                mongodb_loader.db = mongodb_loader.client[manual_db]
                mongodb_loader.collection = mongodb_loader.db[manual_collection]
                
                st.success(f"✅ Configuration updated to: `{manual_db}.{manual_collection}`")
                st.info("🔄 Please reload the page to refresh user list with new configuration")
                
            except Exception as e:
                st.error(f"❌ Failed to update configuration: {e}")
    
    # Debug button
    if st.button("🔍 Debug MongoDB Connection", type="secondary"):
        with st.spinner("Debugging MongoDB connection..."):
            try:
                # Test connection
                users = mongodb_loader.get_available_users()
                st.success(f"✅ Connection successful! Found {len(users)} users.")
            except Exception as e:
                st.error(f"❌ Connection failed: {e}")
    
    # Get available users
    try:
        users = mongodb_loader.get_available_users()
        st.info(f"🔍 **Found {len(users)} users** in `{mongodb_loader.db_name}.{mongodb_loader.collection_name}`: {users}")
    except Exception as e:
        st.error(f"❌ Error connecting to MongoDB: {e}")
        st.error(f"🔍 **Debug Info**: Failed to get users from `{mongodb_loader.db_name}.{mongodb_loader.collection_name}`")
        return
    
    if not users:
        st.warning(f"⚠️ No users found in `{mongodb_loader.db_name}.{mongodb_loader.collection_name}`")
        st.error("🔍 **Debug**: The collection might be empty or user_id field might not exist")
        return
    
    # User selection
    selected_user = st.selectbox(
        "Select User",
        users,
        help="Choose a user to analyze"
    )
    
    # REMOVED: Max Transactions limit for data accuracy
    # Users get complete data for their selected date range
    
    # Load button
    if st.button("🚀 Load User Data", type="primary"):
        with st.spinner("Loading transactions from MongoDB..."):
            try:
                # Log the exact collection being queried
                st.info(f"🔍 **Loading from**: `{mongodb_loader.db_name}.{mongodb_loader.collection_name}` for user `{selected_user}`")
                
                df = mongodb_loader.get_user_transactions(selected_user)  # Load ALL transactions for selected date range
                
                if df.empty:
                    st.warning(f"⚠️ No transactions found for user: {selected_user}")
                    st.error(f"🔍 **Debug Info**: Searched in `{mongodb_loader.db_name}.{mongodb_loader.collection_name}` for user_id='{selected_user}'")
                    return
                else:
                    st.success(f"✅ **Data loaded from**: `{mongodb_loader.db_name}.{mongodb_loader.collection_name}` - Found {len(df)} transactions")
                    
            except Exception as e:
                st.error(f"❌ Error loading data: {e}")
                st.error(f"🔍 **Debug Info**: Failed to load from `{mongodb_loader.db_name}.{mongodb_loader.collection_name}` for user_id='{selected_user}'")
                return
            
            # Process data with selected date range using CLEAN SLATE PROCESSING
            from src.preprocess import DataPreprocessor
            analysis_months = st.session_state.get('analysis_months', 0)  # Default to All Time
            
            st.info(f"🧹 **CLEAN SLATE PROCESSING**: Completely refreshing all data for user `{selected_user}`")
            
            # Force clean slate processing with storage enabled
            preprocessor = DataPreprocessor(date_range_months=analysis_months, store_processed_data=True)
            processed_df = preprocessor.preprocess(df, user_id=selected_user)
            
            # Store processed data in session state
            st.session_state['df'] = processed_df
            st.session_state['user_id'] = selected_user
            st.session_state['raw_df'] = df  # Keep raw data for reference
            st.session_state['data_source'] = f"{mongodb_loader.db_name}.{mongodb_loader.collection_name}"
            
            st.success(f"✅ **Data Pipeline Complete**:")
            st.success(f"   📊 **Source**: `{mongodb_loader.db_name}.{mongodb_loader.collection_name}`")
            st.success(f"   👤 **User**: `{selected_user}`")
            st.success(f"   📈 **Raw Transactions**: {len(df)}")
            st.success(f"   🔄 **Processed for Analysis**: {len(processed_df)} (last {analysis_months} months)")
            
            # Show sample of raw data for verification
            if len(df) > 0:
                st.subheader("🔍 Sample Raw Data (First 3 transactions)")
                sample_columns = ['user_id', 'amount', 'transaction_date', 'counterparty', 'category'] 
                available_columns = [col for col in sample_columns if col in df.columns]
                if available_columns:
                    st.dataframe(df[available_columns].head(3))
                else:
                    st.dataframe(df.head(3))  # Show all columns if sample columns not available

def configure_local_source(data_loader):
    """Configure local JSON file source."""
    st.subheader("📁 Local File Settings")
    
    # Get available JSON files
    current_dir = Path(".")
    json_files = list(current_dir.glob("*.json"))
    
    # Also check test directory
    test_dir = Path("test")
    if test_dir.exists():
        json_files.extend(list(test_dir.glob("*.json")))
    
    if not json_files:
        st.error("❌ No JSON files found")
        st.info("Please run generate_synthetic_data.py first or place a JSON file in the current directory")
        return
    
    # File selection
    file_names = [f.name for f in json_files]
    selected_file = st.selectbox("Select JSON file:", file_names)
    
    if selected_file:
        file_path = next(f for f in json_files if f.name == selected_file)
        st.info(f"📄 Selected file: {file_path}")
        
        # Load data
        if st.button("📂 Load Local Data", type="primary"):
            with st.spinner("Loading local transaction data..."):
                try:
                    df = data_loader.load_json(file_path)
                    
                    # Validate data
                    is_valid, issues = data_loader.validate_data(df)
                    if not is_valid:
                        st.error(f"❌ Data validation failed: {issues}")
                        return
                    
                    # Store in session state
                    st.session_state['df'] = df
                    st.success(f"✅ Loaded {len(df)} transactions from local file")
                    
                except Exception as e:
                    st.error(f"❌ Error loading file: {e}")

def display_analysis(components, df):
    """Display comprehensive analysis results."""
    # Use the data that's already been processed with the correct analysis period
    # No need to reprocess - df is already the processed data from session state
    df_processed = df
    
    if df_processed.empty:
        st.error("❌ No data available after preprocessing")
        return
    
    # Calculate insights - ensure we use current config
    with st.spinner("🧠 Calculating insights..."):
        # Re-initialize analyzer with current config to ensure enhanced system is used
        current_config = EnhancedConfig.get_config()
        insights_analyzer = TransactionInsights(use_enhanced_system=current_config['use_enhanced_insights'], user_id=st.session_state.get('user_id'))
        
        insights = insights_analyzer.calculate_insights(df_processed)
    
    # Display results
    display_salary_overview(insights)
    display_overview(insights)
    display_financial_insights(insights)
    display_card_usage(insights)
    display_monthly_trends(insights, components['visualizer'])
    display_transaction_classification(insights, components['visualizer'])
    display_spending_patterns(insights, components['visualizer'])
    display_payment_apps(insights, components['visualizer'])
    display_consistent_habits(insights)
    display_relationship_changes(insights)
    display_health_spending(insights)
    display_spending_personality(insights)
    display_anomalies(insights, components['visualizer'])
    display_recurring_transactions(insights)
    display_behavioral_insights(insights, components['visualizer'])
    
    # Display advanced behavioral intelligence
    display_behavioral_intelligence(insights)

def display_salary_overview(insights):
    """Display salary information prominently at the top with change tracking."""
    st.header("💼 Salary & Income Overview")
    
    # Get salary information with change tracking
    salary_info = insights.get('salary', {})
    avg_salary = insights.get('avg_salary', 0)
    avg_income = insights.get('avg_income', 0)
    
    # Display salary changes if available
    salary_changes = salary_info.get('salary_changes', [])
    # Use the enhanced salary info if available
    current_salary = salary_info.get('current_salary', avg_salary)
    if hasattr(current_salary, 'item'):  # Handle numpy types
        current_salary = current_salary.item()
    
    # Get salary source from enhanced insights
    salary_source = salary_info.get('source', 'Unknown')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Current Monthly Salary",
            f"₹{current_salary:,.2f}",
            help="Your current monthly salary (most recent period)"
        )
        
        # Show salary change if available
        if salary_changes:
            latest_change = salary_changes[-1]
            change_delta = f"{latest_change['change_percentage']:+.1f}%"
            st.caption(f"Last change: {change_delta}")
    
    with col2:
        st.metric(
            "Total Monthly Income",
            f"₹{avg_income:,.2f}",
            help="Total monthly income including salary and other sources"
        )
    
    with col3:
        salary_source = salary_info.get('source', 'Unknown')
        st.metric(
            "Salary Source",
            salary_source,
            help="Detected source of salary payments"
        )
    
    with col4:
        other_income = insights.get('avg_other_income', 0)
        st.metric(
            "Other Income",
            f"₹{other_income:,.2f}",
            help="Additional income beyond salary"
        )
    
    # Display salary change history if available
    if salary_changes:
        st.subheader("📈 Salary Change History")
        for change in salary_changes:
            change_type = "📈 Promotion" if change['change_type'] == 'promotion' else "📉 Reduction"
            st.info(f"{change_type}: ₹{change['old_salary']:,.2f} → ₹{change['new_salary']:,.2f} "
                   f"({change['change_percentage']:+.1f}%) in {change['to_month']}")

def display_overview(insights):
    """Display overview metrics."""
    st.header("📊 Overview")
    
    # Basic stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Transactions",
            insights['stats'].get('Total Transactions', 0),
            help="Total number of transactions analyzed"
        )
    
    with col2:
        st.metric(
            "Total Spend",
            f"₹{insights['stats'].get('Total Spend', 0):,.2f}",
            help="Total amount spent across all transactions"
        )
    
    with col3:
        st.metric(
            "Avg Transaction",
            f"₹{insights['stats'].get('Average Transaction Value', 0):,.2f}",
            help="Average transaction amount"
        )
    
    with col4:
        st.metric(
            "Date Range",
            f"{insights['stats'].get('Date Range', {}).get('Days', 0)} days",
            help="Time period covered by the data"
        )

def display_financial_insights(insights):
    """Display financial insights."""
    st.header("💰 Financial Health")
    
    # Financial metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Monthly Income",
            f"₹{insights.get('avg_income', 0):,.2f}",
            help="Average monthly income"
        )
    
    with col2:
        st.metric(
            "Monthly Expenses",
            f"₹{insights.get('avg_expense', 0):,.2f}",
            help="Average monthly expenses"
        )
    
    with col3:
        st.metric(
            "Monthly Savings",
            f"₹{insights.get('savings', 0):,.2f}",
            help="Average monthly savings"
        )
    
    with col4:
        savings_rate = insights.get('savings_rate', 0)
        st.metric(
            "Savings Rate",
            f"{savings_rate:.1f}%",
            delta=f"{'📈' if savings_rate > 0 else '📉'}",
            help="Percentage of income saved"
        )
    
    # Financial health score
    health_score = insights.get('financial_health_score', 0)
    st.progress(health_score / 100, text=f"Financial Health Score: {health_score:.0f}/100")

def display_card_usage(insights):
    """Display detailed card usage breakdown."""
    st.header("💳 Card Usage Breakdown")
    
    card_usage = insights.get('card_usage', {})
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Credit Card Spend",
            f"₹{card_usage.get('credit_card_spend', 0):,.2f}",
            help="Total amount spent using credit cards"
        )
    
    with col2:
        st.metric(
            "Credit Card Payment",
            f"₹{card_usage.get('credit_card_payment', 0):,.2f}",
            help="Total credit card bill payments"
        )
    
    with col3:
        # Calculate credit card due (spend - payment)
        cc_spend = card_usage.get('credit_card_spend', 0)
        cc_payment = card_usage.get('credit_card_payment', 0)
        cc_due = cc_spend - cc_payment
        st.metric(
            "Credit Card Due",
            f"₹{cc_due:,.2f}",
            delta=f"{'📈' if cc_due > 0 else '📉'}",
            help="Outstanding credit card balance"
        )
    
    with col4:
        st.metric(
            "Debit Card Spend",
            f"₹{card_usage.get('debit_card', 0):,.2f}",
            help="Total amount spent using debit cards"
        )
    
    with col5:
        st.metric(
            "UPI Spend",
            f"₹{card_usage.get('upi', 0):,.2f}",
            help="Total amount spent using UPI"
        )

def display_monthly_trends(insights, visualizer):
    """Display monthly trends with line chart."""
    st.header("📈 Monthly Financial Trends")
    
    monthly_income = insights.get('monthly_income', pd.Series())
    monthly_expense = insights.get('monthly_expense', pd.Series())
    monthly_savings = insights.get('monthly_savings', pd.Series())  # Use actual savings data
    
    if not monthly_income.empty or not monthly_expense.empty:
        # Create line chart with markers
        fig = go.Figure()
        
        # Add income line
        if not monthly_income.empty:
            fig.add_trace(go.Scatter(
                x=[str(month) for month in monthly_income.index],
                y=monthly_income.values,
                mode='lines+markers',
                name='Income',
                line=dict(color='green', width=3),
                marker=dict(size=8, symbol='square')
            ))
        
        # Add expense line
        if not monthly_expense.empty:
            fig.add_trace(go.Scatter(
                x=[str(month) for month in monthly_expense.index],
                y=monthly_expense.values,
                mode='lines+markers',
                name='Expenses',
                line=dict(color='red', width=3),
                marker=dict(size=8, symbol='square')
            ))
        
        # Add savings line
        if not monthly_savings.empty:
            fig.add_trace(go.Scatter(
                x=[str(month) for month in monthly_savings.index],
                y=monthly_savings.values,
                mode='lines+markers',
                name='Savings',
                line=dict(color='blue', width=3),
                marker=dict(size=8, symbol='square')
            ))
        
        fig.update_layout(
            title="Monthly Income, Expenses & Savings Trends",
            xaxis_title="Month",
            yaxis_title="Amount (₹)",
            height=500,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No monthly trend data available.")

def display_transaction_classification(insights, visualizer):
    """Display transaction classification with hierarchical breakdown."""
    st.header("📊 Transaction Classification")
    
    txn_breakdown = insights.get('txn_type_breakdown', pd.Series())
    
    if isinstance(txn_breakdown, pd.Series) and not txn_breakdown.empty:
        # Create hierarchical breakdown
        col1, col2 = st.columns(2)
        
        with col1:
            # Main classification chart
            fig = px.bar(
                x=txn_breakdown.index,
                y=txn_breakdown.values,
                title="Transaction Type Distribution",
                color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            )
            fig.update_layout(
                xaxis_title="Transaction Type",
                yaxis_title="Count",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Detailed breakdown
            st.subheader("📋 Detailed Breakdown")
            
            # Income breakdown
            income_total = txn_breakdown.get('income', 0) + txn_breakdown.get('salary', 0)
            if income_total > 0:
                st.info(f"**Income Transactions**: {income_total}")
                if txn_breakdown.get('salary', 0) > 0:
                    st.write(f"  • Salary: {txn_breakdown.get('salary', 0)}")
                if txn_breakdown.get('income', 0) > 0:
                    st.write(f"  • Other Income: {txn_breakdown.get('income', 0)}")
            
            # Expense breakdown
            expense_total = txn_breakdown.get('expense', 0) + txn_breakdown.get('upi', 0) + txn_breakdown.get('debit_card', 0) + txn_breakdown.get('credit_card_spend', 0)
            if expense_total > 0:
                st.warning(f"**Expense Transactions**: {expense_total}")
                if txn_breakdown.get('upi', 0) > 0:
                    st.write(f"  • UPI: {txn_breakdown.get('upi', 0)}")
                if txn_breakdown.get('debit_card', 0) > 0:
                    st.write(f"  • Debit Card: {txn_breakdown.get('debit_card', 0)}")
                if txn_breakdown.get('credit_card_spend', 0) > 0:
                    st.write(f"  • Credit Card: {txn_breakdown.get('credit_card_spend', 0)}")
                if txn_breakdown.get('expense', 0) > 0:
                    st.write(f"  • Other Expenses: {txn_breakdown.get('expense', 0)}")
            
            # Other transactions
            if txn_breakdown.get('other', 0) > 0:
                st.info(f"**Other Transactions**: {txn_breakdown.get('other', 0)}")
            
            # Payment method breakdown
            payment_method_breakdown = insights.get('payment_method_breakdown', pd.Series())
            
            # Handle both dict and Series formats
            if isinstance(payment_method_breakdown, dict):
                if payment_method_breakdown:  # Check if dict is not empty
                    st.subheader("💳 Payment Method Breakdown")
                    for method, count in payment_method_breakdown.items():
                        st.write(f"  • {method}: {count} transactions")
            elif isinstance(payment_method_breakdown, pd.Series) and not payment_method_breakdown.empty:
                st.subheader("💳 Payment Method Breakdown")
                for method, count in payment_method_breakdown.items():
                    st.write(f"  • {method}: {count} transactions")

def display_spending_patterns(insights, visualizer):
    """Display spending patterns with interactive drill-down."""
    st.header("🏷️ Spending by Category")
    
    category_spending = insights.get('category_spending_pattern', pd.Series())
    
    if isinstance(category_spending, pd.Series) and not category_spending.empty:
        # Create pie chart
        fig = px.pie(
            values=category_spending.values,
            names=category_spending.index,
            title="Spending Distribution by Category",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # Category drill-down
        st.subheader("🔍 Category Drill-Down")
        
        # Get merchant category data
        merchant_category_data = insights.get('merchant_category_spend', pd.DataFrame())
        
        if not merchant_category_data.empty:
            # Create selectbox for category selection
            selected_category = st.selectbox(
                "Select Category to Drill Down:",
                category_spending.index.tolist(),
                help="Click to see merchant distribution within this category"
            )
            
            # Filter data for selected category
            category_merchants = merchant_category_data[merchant_category_data['category'] == selected_category]
            
            if not category_merchants.empty:
                # Create merchant breakdown chart
                merchant_fig = px.bar(
                    category_merchants,
                    x='merchant_canonical',
                    y='amount',
                    title=f"Merchant Distribution in {selected_category}",
                    color_discrete_sequence=['#ff7f0e']
                )
                merchant_fig.update_layout(
                    xaxis_title="Merchant",
                    yaxis_title="Amount (₹)",
                    height=400,
                    xaxis_tickangle=-45
                )
                st.plotly_chart(merchant_fig, use_container_width=True)
                
                # Show top merchants
                st.subheader(f"📋 Top Merchants in {selected_category}")
                top_merchants = category_merchants.nlargest(5, 'amount')
                for _, row in top_merchants.iterrows():
                    percentage = (row['amount'] / category_merchants['amount'].sum()) * 100
                    st.write(f"• **{row['merchant_canonical']}**: ₹{row['amount']:,.2f} ({percentage:.1f}%)")
        
        # Spending pattern summary
        st.subheader("📊 Spending Pattern Summary")
        top_categories = category_spending.head(3)
        summary_text = " | ".join([f"{cat}: ₹{amt:,.2f}" for cat, amt in top_categories.items()])
        st.success(f"**Your top spending patterns**: {summary_text}")

def display_payment_apps(insights, visualizer):
    """Display payment app usage with enhanced categorization."""
    st.header("📱 Payment Method Analysis")
    
    # Try enhanced payment method breakdown first
    payment_methods = insights.get('payment_method_breakdown', {})
    app_spend = insights.get('app_spend', pd.Series())
    
    # Use enhanced payment methods if available
    if isinstance(payment_methods, dict) and payment_methods and payment_methods != {'Other': len(payment_methods)}:
        # Convert to Series for visualization
        app_spend = pd.Series(payment_methods)
    elif isinstance(payment_methods, pd.Series) and not payment_methods.empty:
        # Already a Series, use directly
        app_spend = payment_methods
    
    if (isinstance(app_spend, pd.Series) and not app_spend.empty) or (isinstance(payment_methods, dict) and payment_methods) or (isinstance(payment_methods, pd.Series) and not payment_methods.empty):
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart for payment methods
            fig = px.pie(
                values=app_spend.values,
                names=app_spend.index,
                title="Payment Method Distribution",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Bar chart for payment methods
            fig = px.bar(
                x=app_spend.index,
                y=app_spend.values,
                title="Payment Method Spending",
                color_discrete_sequence=['#2ca02c']
            )
            fig.update_layout(
                xaxis_title="Payment Method",
                yaxis_title="Amount (₹)",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Most used payment method
        most_used = app_spend.index[0] if isinstance(app_spend, pd.Series) and not app_spend.empty else "None"
        st.info(f"**Most used payment method**: {most_used}")
        
        # Payment method insights
        st.subheader("💡 Payment Method Insights")
        
        # UPI insights
        if 'UPI Payments' in app_spend.index:
            upi_percentage = (app_spend['UPI Payments'] / app_spend.sum()) * 100
            st.success(f"📱 **UPI Usage**: {upi_percentage:.1f}% of your spending uses UPI - you're embracing digital payments!")
        
        # Card insights
        if 'Card Payment' in app_spend.index:
            card_percentage = (app_spend['Card Payment'] / app_spend.sum()) * 100
            st.info(f"💳 **Card Usage**: {card_percentage:.1f}% of spending via cards - good for rewards and credit building!")
        
        # ATM insights
        if 'ATM/Cash' in app_spend.index:
            atm_percentage = (app_spend['ATM/Cash'] / app_spend.sum()) * 100
            if atm_percentage > 20:
                st.warning(f"🏧 **High Cash Usage**: {atm_percentage:.1f}% via ATM - consider digital alternatives for better tracking!")
            else:
                st.success(f"🏧 **Moderate Cash Usage**: {atm_percentage:.1f}% via ATM - good balance!")
    else:
        st.info("No payment method data available.")

def display_consistent_habits(insights):
    """Display consistent spending habits."""
    st.header("🔄 Consistent Spending Habits")
    
    consistent_merchants = insights.get('consistent_merchants', pd.Series())
    
    if isinstance(consistent_merchants, pd.Series) and not consistent_merchants.empty:
        st.success(f"✅ Found {len(consistent_merchants)} consistent spending patterns")
        
        # Group by habit type
        habit_categories = {
            'Transportation': ['uber', 'ola', 'rapido', 'bus', 'metro'],
            'Food & Coffee': ['swiggy', 'zomato', 'starbucks', 'coffee', 'cafe'],
            'Shopping': ['amazon', 'flipkart', 'myntra'],
            'Entertainment': ['netflix', 'prime', 'hotstar'],
            'Utilities': ['airtel', 'jio', 'vodafone', 'electricity']
        }
        
        for category, keywords in habit_categories.items():
            category_merchants = []
            for merchant in consistent_merchants.index:
                if any(keyword in merchant.lower() for keyword in keywords):
                    category_merchants.append(merchant)
            
            if category_merchants:
                st.subheader(f"📅 {category} Habits")
                for merchant in category_merchants[:3]:  # Show top 3
                    st.write(f"• **{merchant}**: Regular payments detected")
    else:
        st.info("ℹ️ No consistent spending patterns detected yet.")

def display_relationship_changes(insights):
    """Display relationship change indicators."""
    st.header("💝 Relationship Change Indicators")
    
    new_merchants = insights.get('relationship_change_merchants', set())
    disappeared_merchants = insights.get('disappeared_merchants', set())
    
    if new_merchants or disappeared_merchants:
        col1, col2 = st.columns(2)
        
        with col1:
            if new_merchants:
                st.subheader("🆕 New Merchants (Recent Months)")
                st.success(f"Found {len(new_merchants)} new merchant relationships")
                
                # Categorize new merchants
                categories = {
                    'Travel & Transport': [],
                    'Food & Dining': [],
                    'Shopping': [],
                    'Entertainment': [],
                    'Health & Wellness': [],
                    'Other': []
                }
                
                for merchant in new_merchants:
                    merchant_lower = merchant.lower()
                    if any(keyword in merchant_lower for keyword in ['uber', 'ola', 'travel', 'bus']):
                        categories['Travel & Transport'].append(merchant)
                    elif any(keyword in merchant_lower for keyword in ['swiggy', 'zomato', 'restaurant', 'food']):
                        categories['Food & Dining'].append(merchant)
                    elif any(keyword in merchant_lower for keyword in ['amazon', 'flipkart', 'shopping']):
                        categories['Shopping'].append(merchant)
                    elif any(keyword in merchant_lower for keyword in ['netflix', 'prime', 'entertainment']):
                        categories['Entertainment'].append(merchant)
                    elif any(keyword in merchant_lower for keyword in ['hospital', 'pharmacy', 'medical', 'fitness']):
                        categories['Health & Wellness'].append(merchant)
                    else:
                        categories['Other'].append(merchant)
                
                for category, merchants in categories.items():
                    if merchants:
                        st.write(f"**{category}**:")
                        for merchant in merchants[:3]:  # Show top 3
                            st.write(f"  • {merchant}")
        
        with col2:
            if disappeared_merchants:
                st.subheader("👋 Discontinued Merchants")
                st.warning(f"Found {len(disappeared_merchants)} discontinued relationships")
                
                for merchant in list(disappeared_merchants)[:5]:  # Show top 5
                    st.write(f"• {merchant}")
    else:
        st.info("ℹ️ No significant relationship changes detected recently.")

def display_health_spending(insights):
    """Display health-related spending."""
    st.header("🏥 Health-Related Spending")
    
    health_spending = insights.get('health_spending', pd.Series())
    
    if not health_spending.empty:
        st.success(f"✅ Found {len(health_spending)} health-related transactions")
        
        # Categorize health spending
        health_categories = {
            'Medical Bills': [],
            'Pharmacy': [],
            'Fitness & Wellness': [],
            'Insurance': [],
            'Other Health': []
        }
        
        total_health_spending = health_spending.sum()
        
        for merchant, amount in health_spending.items():
            merchant_lower = merchant.lower()
            if any(keyword in merchant_lower for keyword in ['hospital', 'clinic', 'doctor', 'medical']):
                health_categories['Medical Bills'].append((merchant, amount))
            elif any(keyword in merchant_lower for keyword in ['pharmacy', 'chemist', 'drug']):
                health_categories['Pharmacy'].append((merchant, amount))
            elif any(keyword in merchant_lower for keyword in ['fitness', 'gym', 'yoga', 'wellness']):
                health_categories['Fitness & Wellness'].append((merchant, amount))
            elif any(keyword in merchant_lower for keyword in ['insurance', 'policy', 'lic']):
                health_categories['Insurance'].append((merchant, amount))
            else:
                health_categories['Other Health'].append((merchant, amount))
        
        # Display by category
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Health Spending", f"₹{total_health_spending:,.2f}")
            
            for category, items in health_categories.items():
                if items:
                    category_total = sum(amount for _, amount in items)
                    st.write(f"**{category}**: ₹{category_total:,.2f}")
        
        with col2:
            # Show top health merchants
            st.subheader("🏥 Top Health Merchants")
            top_health = health_spending.head(5)
            for merchant, amount in top_health.items():
                percentage = (amount / total_health_spending) * 100
                st.write(f"• **{merchant}**: ₹{amount:,.2f} ({percentage:.1f}%)")
    else:
        st.info("ℹ️ No health-related transactions detected.")

def display_spending_personality(insights):
    """Display detailed spending personality."""
    st.header("👤 Spending Personality Analysis")
    
    # Get personality data
    person_intro = insights.get('person_intro', '')
    top_categories = insights.get('category_spending_pattern', pd.Series()).head(3)
    consistent_merchants = insights.get('consistent_merchants', pd.Series())
    time_pattern = insights.get('time_pattern', pd.Series())
    
    # Create personality insights
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Spending Profile")
        st.info(person_intro)
        
        if not top_categories.empty:
            st.write("**Top Spending Categories**:")
            for i, (category, amount) in enumerate(top_categories.items(), 1):
                st.write(f"{i}. **{category}**: ₹{amount:,.2f}")
    
    with col2:
        st.subheader("⏰ Spending Behavior")
        
        if not time_pattern.empty:
            st.write("**Peak Spending Times**:")
            peak_time = time_pattern.idxmax()
            peak_amount = time_pattern.max()
            st.write(f"• **{peak_time}**: ₹{peak_amount:,.2f}")
        
        if not consistent_merchants.empty:
            st.write("**Loyal Merchants**:")
            for merchant in consistent_merchants.head(3).index:
                st.write(f"• {merchant}")
    
    # Financial personality type
    savings_rate = insights.get('savings_rate', 0)
    if savings_rate >= 30:
        personality_type = "💰 **Savings Champion** - Excellent financial discipline!"
    elif savings_rate >= 20:
        personality_type = "📈 **Smart Saver** - Good financial habits!"
    elif savings_rate >= 10:
        personality_type = "⚖️ **Balanced Spender** - Moderate savings rate."
    else:
        personality_type = "⚠️ **High Spender** - Consider increasing savings."
    
    st.success(personality_type)

def display_anomalies(insights, visualizer):
    """Display enhanced anomaly detection results."""
    st.header("🚨 Spending Pattern Analysis")
    
    # Pattern breaks
    if not insights.get('pattern_break_months', pd.Series()).empty:
        st.subheader("📊 Spending Pattern Breaks")
        st.warning(f"⚠️ **Pattern break months**: {', '.join([str(idx) for idx in insights['pattern_break_months'].index.tolist()])}")
        
        # Pattern break chart
        if insights.get('pattern_break_chart_data'):
            pattern_chart = visualizer.create_pattern_break_chart(insights['pattern_break_chart_data'])
            st.plotly_chart(pattern_chart, use_container_width=True)
    else:
        st.success("✅ No significant spending pattern breaks detected")
    
    # Enhanced spending spikes
    if not insights.get('emotional_spikes', pd.DataFrame()).empty:
        st.subheader("📈 Spending Spikes Analysis")
        
        # Get spike analysis data
        spike_chart_data = insights.get('emotional_spike_chart_data', {})
        spike_analysis = spike_chart_data.get('spike_analysis', {})
        
        # Display spike insights
        if spike_analysis.get('behavioral_insights'):
            st.subheader("🧠 Behavioral Insights")
            for insight in spike_analysis['behavioral_insights']:
                st.write(f"• {insight}")
        
        # Display spike statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Spike Days", spike_analysis.get('total_spikes', 0))
        with col2:
            st.metric("High Spike Days", spike_analysis.get('high_spikes', 0))
        with col3:
            st.metric("Extreme Spike Days", spike_analysis.get('extreme_spikes', 0))
        
        # Display top spike categories
        if spike_analysis.get('spike_categories'):
            st.subheader("🎯 Top Spike Categories")
            for category, amount in list(spike_analysis['spike_categories'].items())[:3]:
                st.write(f"• **{category}**: ₹{amount:,.2f}")
        
        # Display spike chart
        spike_chart = visualizer.create_spike_chart(insights['emotional_spikes'])
        st.plotly_chart(spike_chart, use_container_width=True)
    else:
        st.success("✅ No unusual spending spikes detected")

def display_recurring_transactions(insights):
    """Display enhanced recurring transaction analysis."""
    st.header("🔄 Recurring Transactions")
    
    recurring_df = insights.get('recurring', pd.DataFrame())
    
    if not recurring_df.empty:
        # Active recurring transactions
        # Handle missing is_active column
        if 'is_active' in recurring_df.columns:
            active_recurring = recurring_df[recurring_df['is_active'] == True]
        else:
            # If no is_active column, assume all are active
            active_recurring = recurring_df
        
        if not active_recurring.empty:
            st.success(f"✅ Found {len(active_recurring)} active recurring payment patterns")
            
            # Display recurring transactions
            display_recurring_transactions_group(active_recurring)
            
            # Summary statistics
            st.subheader("📊 Recurring Payment Summary")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_recurring = active_recurring['average_amount'].sum()
                st.metric("Total Monthly Recurring", f"₹{total_recurring:,.2f}")
            
            with col2:
                avg_frequency = active_recurring['median_gap_days'].mean()
                st.metric("Average Frequency", f"{avg_frequency:.0f} days")
            
            with col3:
                high_confidence = len(active_recurring[active_recurring.get('confidence_score', 0) > 0.8])
                st.metric("High Confidence Patterns", high_confidence)
        
        else:
            st.warning("⚠️ No active recurring payments found")
            
            # Show inactive patterns if any
            if 'is_active' in recurring_df.columns:
                inactive_recurring = recurring_df[recurring_df['is_active'] == False]
                if not inactive_recurring.empty:
                    st.subheader("📋 Inactive Patterns")
                    st.info(f"Found {len(inactive_recurring)} inactive recurring patterns that may have stopped")
                    
                    for _, row in inactive_recurring.head(3).iterrows():
                        merchant = row.get('merchant', 'Unknown')
                        amount = row.get('average_amount', 0)
                        frequency = row.get('median_gap_days', 0)
                        last_date = row.get('last_payment_date', 'Unknown')
                        
                        if hasattr(last_date, 'strftime'):
                            last_date_str = last_date.strftime('%Y-%m-%d')
                        else:
                            last_date_str = str(last_date)
                        
                        st.write(f"• **{merchant}**: ₹{amount:.2f} every {frequency:.0f} days (last: {last_date_str})")
    else:
        st.info("ℹ️ No recurring transaction patterns detected")
        
        # Provide helpful tips
        st.subheader("💡 Tips for Better Recurring Payment Detection")
        st.write("""
        • **Rent Payments**: Make payments around the same time each month
        • **ATM Withdrawals**: Regular cash withdrawals for specific purposes
        • **Investment/SIP**: Regular investment payments
        • **Subscriptions**: Streaming, software, or service subscriptions
        • **Utilities**: Regular bill payments for electricity, water, etc.
        """)

def display_behavioral_insights(insights, visualizer):
    """Display behavioral insights including time patterns."""
    st.header("🧠 Behavioral Insights")
    
    # Time patterns
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⏰ Time-of-Day Patterns")
        if not insights.get('time_pattern', pd.Series()).empty:
            time_chart = visualizer.create_bar_chart(
                insights['time_pattern'],
                title="Spending by Time of Day"
            )
            st.plotly_chart(time_chart, use_container_width=True)
        else:
            st.info("No time pattern data available.")
    
    with col2:
        st.subheader("📅 Day-of-Week Patterns")
        if not insights.get('day_spend', pd.Series()).empty:
            day_chart = visualizer.create_bar_chart(
                insights['day_spend'],
                title="Spending by Day of Week"
            )
            st.plotly_chart(day_chart, use_container_width=True)
        else:
            st.info("No day pattern data available.")
    
    # Daily spending trend
    st.subheader("📈 Daily Spending Trend")
    if not insights.get('daily_trend', pd.Series()).empty:
        daily_chart = visualizer.create_line_chart(
            insights['daily_trend'],
            title="Daily Spend Trend"
        )
        st.plotly_chart(daily_chart, use_container_width=True)
        
        # Show daily trend summary
        daily_stats = insights['daily_trend']
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Average Daily Spend", f"₹{daily_stats.mean():,.2f}")
        
        with col2:
            st.metric("Highest Daily Spend", f"₹{daily_stats.max():,.2f}")
        
        with col3:
            st.metric("Lowest Daily Spend", f"₹{daily_stats.min():,.2f}")
    else:
        st.info("No daily trend data available.")

def display_behavioral_intelligence(insights):
    """Display advanced behavioral intelligence insights."""
    from src.behavioral_dashboard import BehavioralDashboard
    
    behavioral_insights = insights.get('behavioral_intelligence', {})
    if not behavioral_insights:
        return
    
    behavioral_dashboard = BehavioralDashboard()
    
    # Display behavioral insights in sections
    behavioral_dashboard.display_predictive_insights(behavioral_insights)
    behavioral_dashboard.display_personality_profile(behavioral_insights)
    behavioral_dashboard.display_lifestyle_patterns(behavioral_insights)
    behavioral_dashboard.display_stress_patterns(behavioral_insights)
    behavioral_dashboard.display_life_changes(behavioral_insights)
    behavioral_dashboard.display_financial_health_signals(behavioral_insights)
    behavioral_dashboard.display_behavioral_summary(behavioral_insights)

def display_recurring_transactions_group(active_recurring):
    """Helper function to display recurring transactions"""
    # Group by payment type for better organization
    # Handle missing payment_type column
    if 'payment_type' in active_recurring.columns:
        payment_types = active_recurring['payment_type'].unique()
        
        for payment_type in payment_types:
            type_recurring = active_recurring[active_recurring['payment_type'] == payment_type]
            st.subheader(f"📅 {payment_type} Payments")
            display_recurring_rows(type_recurring)
    else:
        # If no payment_type column, display all as one group
        st.subheader(f"📅 Recurring Payments")
        display_recurring_rows(active_recurring)

def display_recurring_rows(recurring_data):
    """Display recurring transaction rows"""
    for _, row in recurring_data.iterrows():
        # Calculate days until next payment (with error handling)
        try:
            if 'next_due_date' in row and pd.notna(row['next_due_date']):
                days_until = (pd.to_datetime(row['next_due_date']) - pd.Timestamp.now()).days
            else:
                days_until = None
        except:
            days_until = None
        
        # Create a metric card for each recurring payment
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            merchant = row.get('merchant', 'Unknown')
            st.metric("Merchant", merchant)
        
        with col2:
            amount = row.get('average_amount', 0)
            st.metric("Amount", f"₹{amount:.2f}")
        
        with col3:
            frequency = row.get('median_gap_days', 0)
            if frequency > 0:
                st.metric("Frequency", f"{frequency:.0f} days")
            else:
                st.metric("Frequency", "Variable")
        
        with col4:
            if days_until is not None:
                if days_until <= 7:
                    st.metric("Due", f"⚠️ {days_until} days", delta="Urgent")
                elif days_until <= 14:
                    st.metric("Due", f"📅 {days_until} days", delta="Soon")
                else:
                    st.metric("Due", f"📅 {days_until} days")
            else:
                st.metric("Due", "Unknown")
        
        # Show confidence and pattern details if available
        if 'confidence_score' in row and pd.notna(row['confidence_score']):
            confidence = row['confidence_score']
            pattern_details = row.get('pattern_details', 'Regular pattern detected')
            
            if confidence > 0.8:
                st.success(f"🎯 High confidence pattern: {pattern_details}")
            elif confidence > 0.6:
                st.info(f"📊 Moderate confidence pattern: {pattern_details}")
            else:
                st.warning(f"⚠️ Low confidence pattern: {pattern_details}")
        
        st.divider()

if __name__ == "__main__":
    main() 