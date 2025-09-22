#!/usr/bin/env python3
"""
SMS Financial Processing & Analytics API
=======================================

FastAPI server providing:
1. SMS Processing Pipeline API
2. Financial Analytics & Insights API
3. Transaction Data Management API

Built on top of the SMS processing pipeline system.
"""

import os
import sys
import json
import asyncio
import tempfile
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Path as PathParam
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from pymongo import MongoClient
from bson import ObjectId
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="SMS Financial Processing & Analytics API",
    description="Complete SMS processing pipeline with financial analytics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DB = os.getenv('MONGODB_DB', 'pluto_money')

if not MONGODB_URI:
    raise ValueError("MONGODB_URI environment variable is required")

# Global MongoDB client
mongo_client = MongoClient(MONGODB_URI, tlsAllowInvalidCertificates=True)
db = mongo_client[MONGODB_DB]

# Collections
users_collection = db['users']
sms_data_collection = db['sms_data']
financial_transactions_collection = db['financial_transactions']
user_financial_transactions_collection = db['user_financial_transactions']

# Pydantic Models
class SMSMessage(BaseModel):
    """Individual SMS message model"""
    sender: str = Field(..., description="SMS sender ID")
    body: str = Field(..., description="SMS message content")
    date: str = Field(..., description="SMS timestamp (ISO format)")
    type: str = Field(default="SmsMessageKind.received", description="SMS type")

class SMSProcessingRequest(BaseModel):
    """Request model for SMS processing endpoint"""
    user_id: str = Field(..., description="User ID for processing")
    sms_data: List[SMSMessage] = Field(..., description="List of SMS messages to process")
    batch_size: int = Field(default=5, ge=1, le=20, description="Processing batch size")
    model: str = Field(default="qwen3:8b", description="LLM model to use")
    create_indexes: bool = Field(default=False, description="Create database indexes")
    skip_date_conversion: bool = Field(default=False, description="Skip final date conversion")

    @validator('sms_data')
    def validate_sms_data(cls, v):
        if not v or len(v) == 0:
            raise ValueError("sms_data cannot be empty")
        return v

class FinancialAnalyticsRequest(BaseModel):
    """Request model for financial analytics"""
    user_id: str = Field(..., description="User ID for analytics")
    start_date: Optional[str] = Field(None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format)")
    period: Optional[str] = Field(None, description="Predefined period: last_week, last_month, last_3_months, last_5_months, last_6_months, last_year")

    @validator('period')
    def validate_period(cls, v):
        if v and v not in ['last_week', 'last_month', 'last_3_months', 'last_5_months', 'last_6_months', 'last_year']:
            raise ValueError("Invalid period. Use: last_week, last_month, last_3_months, last_5_months, last_6_months, last_year")
        return v

class ProcessingStatus(BaseModel):
    """Processing status response model"""
    status: str
    message: str
    user_id: str
    task_id: str
    started_at: datetime
    estimated_completion: Optional[datetime] = None

class FinancialSummary(BaseModel):
    """Financial summary response model"""
    user_id: str
    period: str
    start_date: datetime
    end_date: datetime
    total_income: float
    total_expense: float
    net_amount: float
    transaction_count: int
    income_transactions: int
    expense_transactions: int
    top_categories: List[Dict[str, Any]]
    monthly_breakdown: List[Dict[str, Any]]

# Utility Functions
def get_date_range(period: str) -> tuple[datetime, datetime]:
    """Get date range based on period"""
    end_date = datetime.now()
    
    if period == 'last_week':
        start_date = end_date - timedelta(weeks=1)
    elif period == 'last_month':
        start_date = end_date - timedelta(days=30)
    elif period == 'last_3_months':
        start_date = end_date - timedelta(days=90)
    elif period == 'last_5_months':
        start_date = end_date - timedelta(days=150)
    elif period == 'last_6_months':
        start_date = end_date - timedelta(days=180)
    elif period == 'last_year':
        start_date = end_date - timedelta(days=365)
    else:
        raise ValueError(f"Invalid period: {period}")
    
    return start_date, end_date

def parse_iso_date(date_str: str) -> datetime:
    """Parse ISO date string to datetime"""
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}")

async def run_pipeline_async(user_id: str, user_phone: str, sms_file_path: str, batch_size: int, model: str, 
                           create_indexes: bool, skip_date_conversion: bool) -> Dict[str, Any]:
    """Run the complete SMS processing pipeline asynchronously"""
    
    cmd = [
        "python3", "run_complete_pipeline.py",
        "--input", sms_file_path,
        "--phone", user_phone,
        "--batch-size", str(batch_size),
        "--model", model
    ]
    
    if create_indexes:
        cmd.append("--create-indexes")
    
    if skip_date_conversion:
        cmd.append("--skip-date-conversion")
    
    try:
        # Run the pipeline
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            "success": process.returncode == 0,
            "returncode": process.returncode,
            "stdout": stdout.decode('utf-8'),
            "stderr": stderr.decode('utf-8')
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "returncode": -1
        }

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "SMS Financial Processing & Analytics API",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "process_sms": "/api/v1/sms/process",
            "financial_analytics": "/api/v1/analytics/financial",
            "user_transactions": "/api/v1/users/{user_id}/transactions",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test MongoDB connection
        db.command('ping')
        return {
            "status": "healthy",
            "timestamp": datetime.now(),
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(),
                "database": "disconnected",
                "error": str(e)
            }
        )

@app.post("/api/v1/sms/process")
async def process_sms_data(request: SMSProcessingRequest, background_tasks: BackgroundTasks):
    """
    Process SMS data through the complete pipeline
    
    This endpoint:
    1. Validates the input SMS data
    2. Creates a temporary file with the SMS data
    3. Runs the complete processing pipeline
    4. Returns processing status and results
    """
    
    # Generate task ID
    task_id = f"sms_process_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.user_id[:8]}"
    
    try:
        # Validate user exists (handle both ObjectId and string user_id)
        from bson import ObjectId
        
        user = None
        user_id_obj = None
        try:
            # Try ObjectId lookup first
            user_id_obj = ObjectId(request.user_id)
            user = users_collection.find_one({"_id": user_id_obj})
        except:
            # Fallback to string user_id lookup (backward compatibility)
            user = users_collection.find_one({"user_id": request.user_id})
            if user and user.get("_id"):
                user_id_obj = user["_id"]
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User not found: {request.user_id}"
            )
        
        # Create temporary file with SMS data
        sms_data_list = [sms.dict() for sms in request.sms_data]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(sms_data_list, temp_file, indent=2)
            temp_file_path = temp_file.name
        
        # Run pipeline asynchronously using phone number for better user identification
        user_phone = user.get("phone") if user else None
        if not user_phone:
            raise HTTPException(
                status_code=400,
                detail="User phone number not found - required for SMS processing"
            )
        
        result = await run_pipeline_async(
            user_id=str(user_id_obj) if user_id_obj else request.user_id,
            user_phone=user_phone,
            sms_file_path=temp_file_path,
            batch_size=request.batch_size,
            model=request.model,
            create_indexes=request.create_indexes,
            skip_date_conversion=request.skip_date_conversion
        )
        
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass  # Ignore cleanup errors
        
        if result["success"]:
            # Get processing statistics (handle both ObjectId and string user_id)
            user_stats = None
            try:
                user_id_obj = ObjectId(request.user_id)
                user_stats = users_collection.find_one({"_id": user_id_obj})
            except:
                user_stats = users_collection.find_one({"user_id": request.user_id})
            
            return {
                "status": "success",
                "message": "SMS data processed successfully",
                "task_id": task_id,
                "user_id": request.user_id,
                "processed_at": datetime.now(),
                "statistics": {
                    "input_sms_count": len(request.sms_data),
                    "total_uploaded": user_stats.get("sms_stats", {}).get("total_uploaded", 0),
                    "total_processed": user_stats.get("sms_stats", {}).get("total_processed", 0),
                    "total_financial": user_stats.get("sms_stats", {}).get("total_financial", 0)
                },
                "pipeline_output": result["stdout"][-1000:] if result["stdout"] else ""  # Last 1000 chars
            }
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Pipeline processing failed",
                    "task_id": task_id,
                    "error": result.get("stderr", "Unknown error"),
                    "returncode": result.get("returncode", -1)
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal server error during SMS processing",
                "task_id": task_id,
                "error": str(e)
            }
        )

@app.post("/api/v1/analytics/financial")
async def get_financial_analytics(request: FinancialAnalyticsRequest):
    """
    Get comprehensive financial analytics for a user
    
    Provides:
    - Total income and expenses
    - Net amount (income - expenses)
    - Transaction counts and breakdowns
    - Category analysis
    - Monthly trends
    """
    
    try:
        # Validate user exists (handle both ObjectId and string user_id)
        from bson import ObjectId
        
        user = None
        user_id_obj = None
        try:
            # Try ObjectId lookup first
            user_id_obj = ObjectId(request.user_id)
            user = users_collection.find_one({"_id": user_id_obj})
        except:
            # Fallback to string user_id lookup (backward compatibility)
            user = users_collection.find_one({"user_id": request.user_id})
            if user and user.get("_id"):
                user_id_obj = user["_id"]
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User not found: {request.user_id}"
            )
        
        # Determine date range
        if request.period:
            start_date, end_date = get_date_range(request.period)
            period_str = request.period
        elif request.start_date and request.end_date:
            start_date = parse_iso_date(request.start_date)
            end_date = parse_iso_date(request.end_date)
            period_str = f"custom_{request.start_date}_to_{request.end_date}"
        else:
            # Default to last month
            start_date, end_date = get_date_range('last_month')
            period_str = "last_month_default"
        
        # Query transactions using the resolved user_id_obj
        query = {
            "transaction_date": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        
        # Use the resolved user_id_obj or fallback to string
        if user_id_obj:
            query["user_id"] = user_id_obj
        else:
            query["user_id"] = request.user_id
        
        transactions = list(user_financial_transactions_collection.find(query))
        
        if not transactions:
            return FinancialSummary(
                user_id=request.user_id,
                period=period_str,
                start_date=start_date,
                end_date=end_date,
                total_income=0.0,
                total_expense=0.0,
                net_amount=0.0,
                transaction_count=0,
                income_transactions=0,
                expense_transactions=0,
                top_categories=[],
                monthly_breakdown=[]
            )
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(transactions)
        
        # Calculate basic metrics
        income_df = df[df['transaction_type'] == 'credit']
        expense_df = df[df['transaction_type'] == 'debit']
        
        total_income = float(income_df['amount'].sum()) if not income_df.empty else 0.0
        total_expense = float(expense_df['amount'].sum()) if not expense_df.empty else 0.0
        net_amount = total_income - total_expense
        
        # Category analysis
        category_analysis = df.groupby('category').agg({
            'amount': ['sum', 'count'],
            'transaction_type': 'first'
        }).reset_index()
        
        category_analysis.columns = ['category', 'total_amount', 'count', 'type']
        top_categories = category_analysis.nlargest(5, 'total_amount').to_dict('records')
        
        # Monthly breakdown
        df['month'] = pd.to_datetime(df['transaction_date']).dt.to_period('M')
        monthly_stats = df.groupby(['month', 'transaction_type'])['amount'].sum().unstack(fill_value=0)
        
        monthly_breakdown = []
        for month in monthly_stats.index:
            monthly_breakdown.append({
                "month": str(month),
                "income": float(monthly_stats.loc[month].get('credit', 0)),
                "expense": float(monthly_stats.loc[month].get('debit', 0)),
                "net": float(monthly_stats.loc[month].get('credit', 0) - monthly_stats.loc[month].get('debit', 0))
            })
        
        return FinancialSummary(
            user_id=request.user_id,
            period=period_str,
            start_date=start_date,
            end_date=end_date,
            total_income=total_income,
            total_expense=total_expense,
            net_amount=net_amount,
            transaction_count=len(transactions),
            income_transactions=len(income_df),
            expense_transactions=len(expense_df),
            top_categories=top_categories,
            monthly_breakdown=monthly_breakdown
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error generating financial analytics",
                "error": str(e)
            }
        )

@app.get("/api/v1/analytics/income/{user_id}")
async def get_income_analytics(
    user_id: str = PathParam(..., description="User ID"),
    period: str = Query(default="last_month", description="Time period"),
    start_date: Optional[str] = Query(None, description="Custom start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Custom end date (ISO format)")
):
    """
    Get detailed income analytics for a user
    
    Returns:
    - Total credited amount
    - Income sources breakdown
    - Trends over time
    """
    
    request = FinancialAnalyticsRequest(
        user_id=user_id,
        period=period if not start_date else None,
        start_date=start_date,
        end_date=end_date
    )
    
    analytics = await get_financial_analytics(request)
    
    # Extract income-specific data
    return {
        "user_id": user_id,
        "period": analytics.period,
        "date_range": {
            "start": analytics.start_date,
            "end": analytics.end_date
        },
        "total_income": analytics.total_income,
        "income_transactions": analytics.income_transactions,
        "average_income_per_transaction": analytics.total_income / max(analytics.income_transactions, 1),
        "top_income_categories": [cat for cat in analytics.top_categories if cat.get('type') == 'credit'],
        "monthly_income_trend": [
            {"month": month["month"], "income": month["income"]} 
            for month in analytics.monthly_breakdown
        ]
    }

@app.get("/api/v1/analytics/expenses/{user_id}")
async def get_expense_analytics(
    user_id: str = PathParam(..., description="User ID"),
    period: str = Query(default="last_month", description="Time period"),
    start_date: Optional[str] = Query(None, description="Custom start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Custom end date (ISO format)")
):
    """
    Get detailed expense analytics for a user
    
    Returns:
    - Total debited amount
    - Expense categories breakdown
    - Spending patterns
    """
    
    request = FinancialAnalyticsRequest(
        user_id=user_id,
        period=period if not start_date else None,
        start_date=start_date,
        end_date=end_date
    )
    
    analytics = await get_financial_analytics(request)
    
    # Extract expense-specific data
    return {
        "user_id": user_id,
        "period": analytics.period,
        "date_range": {
            "start": analytics.start_date,
            "end": analytics.end_date
        },
        "total_expenses": analytics.total_expense,
        "expense_transactions": analytics.expense_transactions,
        "average_expense_per_transaction": analytics.total_expense / max(analytics.expense_transactions, 1),
        "top_expense_categories": [cat for cat in analytics.top_categories if cat.get('type') == 'debit'],
        "monthly_expense_trend": [
            {"month": month["month"], "expenses": month["expense"]} 
            for month in analytics.monthly_breakdown
        ]
    }

@app.get("/api/v1/users/{user_id}/transactions")
async def get_user_transactions(
    user_id: str = PathParam(..., description="User ID"),
    limit: int = Query(default=100, ge=1, le=1000, description="Number of transactions to return"),
    offset: int = Query(default=0, ge=0, description="Number of transactions to skip"),
    transaction_type: Optional[str] = Query(None, description="Filter by type: credit or debit"),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)")
):
    """
    Get paginated user transactions with optional filters
    """
    
    try:
        # Build query with proper user_id handling
        from bson import ObjectId
        
        user_id_obj = None
        try:
            # Try ObjectId lookup first
            user_id_obj = ObjectId(user_id)
        except:
            # Keep as string if conversion fails
            pass
        
        query = {"user_id": user_id_obj if user_id_obj else user_id}
        
        if transaction_type:
            if transaction_type not in ['credit', 'debit']:
                raise HTTPException(
                    status_code=400,
                    detail="transaction_type must be 'credit' or 'debit'"
                )
            query["transaction_type"] = transaction_type
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = parse_iso_date(start_date)
            if end_date:
                date_filter["$lte"] = parse_iso_date(end_date)
            query["transaction_date"] = date_filter
        
        # Get total count
        total_count = user_financial_transactions_collection.count_documents(query)
        
        # Get transactions with pagination
        transactions = list(
            user_financial_transactions_collection
            .find(query)
            .sort("transaction_date", -1)
            .skip(offset)
            .limit(limit)
        )
        
        # Convert ObjectId to string for JSON serialization
        for txn in transactions:
            if '_id' in txn:
                txn['_id'] = str(txn['_id'])
            if 'transaction_date' in txn and hasattr(txn['transaction_date'], 'isoformat'):
                txn['transaction_date'] = txn['transaction_date'].isoformat()
        
        return {
            "user_id": user_id,
            "transactions": transactions,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_next": offset + limit < total_count,
                "has_previous": offset > 0
            },
            "filters": {
                "transaction_type": transaction_type,
                "start_date": start_date,
                "end_date": end_date
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error retrieving user transactions",
                "error": str(e)
            }
        )

@app.get("/api/v1/users/{user_id}/summary")
async def get_user_summary(user_id: str = PathParam(..., description="User ID")):
    """
    Get comprehensive user summary including profile and financial overview
    """
    
    try:
        # Get user profile (handle both ObjectId and string user_id)
        from bson import ObjectId
        
        user = None
        user_id_obj = None
        try:
            # Try ObjectId lookup first
            user_id_obj = ObjectId(user_id)
            user = users_collection.find_one({"_id": user_id_obj})
        except:
            # Fallback to string user_id lookup (backward compatibility)
            user = users_collection.find_one({"user_id": user_id})
            if user and user.get("_id"):
                user_id_obj = user["_id"]
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User not found: {user_id}"
            )
        
        # Get recent financial analytics (last month)
        analytics_request = FinancialAnalyticsRequest(
            user_id=user_id,
            period="last_month"
        )
        
        recent_analytics = await get_financial_analytics(analytics_request)
        
        # Get transaction counts by type
        total_transactions = user_financial_transactions_collection.count_documents(
            {"user_id": user_id_obj if user_id_obj else user_id}
        )
        
        return {
            "user_profile": {
                "user_id": user["user_id"],
                "name": user.get("name"),
                "email": user.get("email"),
                "phone": user.get("phone"),
                "created_at": user.get("created_at"),
                "is_active": user.get("is_active", True)
            },
            "sms_statistics": user.get("sms_stats", {}),
            "financial_overview": {
                "total_transactions": total_transactions,
                "last_month_income": recent_analytics.total_income,
                "last_month_expenses": recent_analytics.total_expense,
                "last_month_net": recent_analytics.net_amount
            },
            "summary_generated_at": datetime.now()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error generating user summary",
                "error": str(e)
            }
        )

# Error Handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"message": "Resource not found", "timestamp": datetime.now().isoformat()}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error", "timestamp": datetime.now().isoformat()}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
