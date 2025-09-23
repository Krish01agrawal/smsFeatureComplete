#!/usr/bin/env python3
"""
Modified API Server - No Users Collection Dependency
===================================================

This version removes the dependency on the users collection and works with
your custom user format where _id is the user_id.

Key Changes:
1. Removes user validation from users collection
2. Uses provided user_id directly
3. Removes user statistics tracking
4. Works with your custom user format
"""

import os
import json
import tempfile
import asyncio
import subprocess
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from pymongo import MongoClient
from bson import ObjectId
import logging
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom JSON encoder to handle ObjectId
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

def convert_objectid_to_str(data):
    """Convert ObjectId fields to strings for JSON serialization"""
    if isinstance(data, dict):
        return {key: convert_objectid_to_str(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_objectid_to_str(item) for item in data]
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data

# MongoDB connection - Use environment variable or default to local
# You can set MONGODB_URI in .env file or environment variable
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/blackcard")
MONGODB_DB = os.getenv("MONGODB_DB", "blackcard")

print(f"🔗 Using MongoDB URI: {MONGODB_URI}")

try:
    client = MongoClient(
        MONGODB_URI,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000
    )
    db = client[MONGODB_DB]
    # Test connection
    db.command('ping')
    print("✅ MongoDB connected successfully")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    print("🔄 Please check your MongoDB connection and .env file")
    client = None
    db = None

# Collections (NO USERS COLLECTION NEEDED)
if db is not None:
    sms_data_collection = db["sms_data"]
    sms_fin_rawdata_collection = db["sms_fin_rawdata"]
    financial_transactions_collection = db["financial_transactions"]
    user_financial_transactions_collection = db["user_financial_transactions"]
else:
    # Mock collections for development when MongoDB is not available
    sms_data_collection = None
    sms_fin_rawdata_collection = None
    financial_transactions_collection = None
    user_financial_transactions_collection = None

app = FastAPI(
    title="SMS Financial Processing & Analytics API",
    description="Process SMS data and provide financial analytics without users collection dependency",
    version="1.0.0"
)

# Pydantic Models
class SMSData(BaseModel):
    sender: str
    body: str
    date: str
    type: str

class SMSProcessingRequest(BaseModel):
    user_id: str
    sms_data: List[SMSData]
    batch_size: int = Field(default=5, ge=1, le=50)
    model: str = Field(default="qwen3:8b")
    create_indexes: bool = Field(default=True)
    skip_date_conversion: bool = Field(default=False)

class FinancialAnalyticsRequest(BaseModel):
    user_id: str
    period: str = Field(..., pattern="^(last_week|last_2_weeks|last_month|last_3_months|last_5_months|last_6_months|last_9_months |last_12_months|last_year|last_2_years|last_3_years|last_5_years|last_10_years)$")
    
    @validator('period')
    def validate_period(cls, v):
        valid_periods = ["last_week", "last_2_weeks", "last_month", "last_3_months", "last_5_months", "last_6_months", "last_9_months", "last_12_months", "last_year", "last_2_years", "last_3_years", "last_5_years", "last_10_years"]
        if v not in valid_periods:
            raise ValueError(f"Invalid period. Use: {', '.join(valid_periods)}")
        return v

# Utility Functions
def get_date_range(period: str) -> tuple:
    """Get start and end dates for the given period using proper month-based calculation"""
    now = datetime.now()
    
    if period == "last_week":
        start_date = now - timedelta(days=7)
    elif period == "last_2_weeks":
        start_date = now - timedelta(days=14)
    elif period == "last_month":
        # Last complete month
        if now.month == 1:
            start_date = datetime(now.year - 1, 12, 1)
        else:
            start_date = datetime(now.year, now.month - 1, 1)
        end_date = datetime(now.year, now.month, 1) - timedelta(days=1)
    elif period == "last_3_months":
        # Last 3 complete months
        if now.month <= 3:
            start_date = datetime(now.year - 1, 12 - (3 - now.month), 1)
        else:
            start_date = datetime(now.year, now.month - 3, 1)
        end_date = now  # Include current month
    elif period == "last_5_months":
        # Last 5 complete months
        if now.month <= 5:
            start_date = datetime(now.year - 1, 12 - (5 - now.month), 1)
        else:
            start_date = datetime(now.year, now.month - 5, 1)
        end_date = now  # Include current month
    elif period == "last_6_months":
        # Last 6 complete months (April to September for current September)
        if now.month <= 6:
            start_date = datetime(now.year - 1, 12 - (6 - now.month), 1)
        else:
            start_date = datetime(now.year, now.month - 5, 1)
        end_date = now  # Include current month
    elif period == "last_9_months":
        # Last 9 complete months
        if now.month <= 9:
            start_date = datetime(now.year - 1, 12 - (9 - now.month), 1)
        else:
            start_date = datetime(now.year, now.month - 9, 1)
        end_date = now  # Include current month
    elif period == "last_12_months":
        # Last 12 complete months
        if now.month <= 12:
            start_date = datetime(now.year - 1, 12 - (12 - now.month), 1)
        else:
            start_date = datetime(now.year, now.month - 12, 1)
        end_date = now  # Include current month
    elif period == "last_year":
        # Last year (current year)
        start_date = datetime(now.year, 1, 1)
        end_date = now  # Include current year up to today
    elif period == "last_2_years":
        # Last 2 years (current year + previous year)
        start_date = datetime(now.year - 1, 1, 1)
        end_date = now  # Include current year up to today
    elif period == "last_3_years":
        # Last 3 years (current year + previous 2 years)
        start_date = datetime(now.year - 2, 1, 1)
        end_date = now  # Include current year up to today
    elif period == "last_5_years":
        # Last 5 years (current year + previous 4 years)
        start_date = datetime(now.year - 4, 1, 1)
        end_date = now  # Include current year up to today
    elif period == "last_10_years":
        # Last 10 years (current year + previous 9 years)
        start_date = datetime(now.year - 9, 1, 1)
        end_date = now  # Include current year up to today
    else:
        # Default to last month
        if now.month == 1:
            start_date = datetime(now.year - 1, 12, 1)
        else:
            start_date = datetime(now.year, now.month - 1, 1)
        end_date = now.replace(day=1) - timedelta(days=1)
    
    return start_date, end_date

def get_monthly_breakdown(transactions: List[Dict], start_date: datetime, end_date: datetime) -> Dict[str, Dict]:
    """Get month-by-month breakdown of transactions"""
    monthly_data = {}
    
    # Initialize all months in range (inclusive of start and end months)
    current = start_date.replace(day=1)
    end_month = end_date.replace(day=1)
    
    while current <= end_month:
        month_key = current.strftime("%Y-%m")
        monthly_data[month_key] = {
            "month": current.strftime("%B %Y"),
            "income": 0.0,
            "expense": 0.0,
            "savings": 0.0,
            "expense_ratio": 0.0,
            "transaction_count": 0
        }
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    # Process transactions
    for transaction in transactions:
        trans_date = transaction.get("transaction_date")
        if isinstance(trans_date, str):
            trans_date = datetime.fromisoformat(trans_date.replace('Z', '+00:00'))
        
        month_key = trans_date.strftime("%Y-%m")
        if month_key in monthly_data:
            amount = transaction.get("amount", 0)
            trans_type = transaction.get("transaction_type", "")
            
            monthly_data[month_key]["transaction_count"] += 1
            
            if trans_type == "credit":
                monthly_data[month_key]["income"] += amount
            elif trans_type == "debit":
                monthly_data[month_key]["expense"] += amount
            
            # Calculate savings and ratio
            monthly_data[month_key]["savings"] = monthly_data[month_key]["income"] - monthly_data[month_key]["expense"]
            if monthly_data[month_key]["income"] > 0:
                monthly_data[month_key]["expense_ratio"] = monthly_data[month_key]["expense"] / monthly_data[month_key]["income"]
    
    return monthly_data

def get_yearly_breakdown(transactions: List[Dict], start_date: datetime, end_date: datetime) -> Dict[str, Dict]:
    """Get year-by-year breakdown of transactions"""
    yearly_data = {}
    
    # Initialize all years in range
    current_year = start_date.year
    end_year = end_date.year
    
    for year in range(current_year, end_year + 1):
        year_key = str(year)
        yearly_data[year_key] = {
            "year": year_key,
            "income": 0.0,
            "expense": 0.0,
            "savings": 0.0,
            "expense_ratio": 0.0,
            "transaction_count": 0
        }
    
    # Process transactions
    for transaction in transactions:
        trans_date = transaction.get("transaction_date")
        if isinstance(trans_date, str):
            trans_date = datetime.fromisoformat(trans_date.replace('Z', '+00:00'))
        
        year_key = str(trans_date.year)
        if year_key in yearly_data:
            amount = transaction.get("amount", 0)
            trans_type = transaction.get("transaction_type", "")
            
            yearly_data[year_key]["transaction_count"] += 1
            
            if trans_type == "credit":
                yearly_data[year_key]["income"] += amount
            elif trans_type == "debit":
                yearly_data[year_key]["expense"] += amount
            
            # Calculate savings and ratio
            yearly_data[year_key]["savings"] = yearly_data[year_key]["income"] - yearly_data[year_key]["expense"]
            if yearly_data[year_key]["income"] > 0:
                yearly_data[year_key]["expense_ratio"] = yearly_data[year_key]["expense"] / yearly_data[year_key]["income"]
    
    return yearly_data

async def run_pipeline_async(user_id: str, sms_file_path: str, batch_size: int, model: str, 
                           create_indexes: bool, skip_date_conversion: bool) -> Dict[str, Any]:
    """Run the complete SMS processing pipeline asynchronously"""
    try:
        cmd = [
            "python3", "run_complete_pipeline.py",
            "--input", sms_file_path,
            "--user-id", user_id,  # Use user_id directly
            "--batch-size", str(batch_size),
            "--model", model
        ]
        
        if create_indexes:
            cmd.append("--create-indexes")
        
        if skip_date_conversion:
            cmd.append("--skip-date-conversion")
        
        logger.info(f"Running pipeline command: {' '.join(cmd)}")
        
        # Get the directory where the API server is located (where pipeline scripts are)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=script_dir
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            "success": process.returncode == 0,
            "returncode": process.returncode,
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else ""
        }
        
    except Exception as e:
        logger.error(f"Pipeline execution error: {e}")
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
        "message": "SMS Financial Processing & Analytics API (No Users Collection)",
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
        if db is not None:
            # Test MongoDB connection
            db.command('ping')
            return {
                "status": "healthy",
                "timestamp": datetime.now(),
                "database": "connected",
                "version": "1.0.0"
            }
        else:
            return {
                "status": "degraded",
                "timestamp": datetime.now(),
                "database": "disconnected",
                "version": "1.0.0",
                "message": "Running in development mode without MongoDB"
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
    
    NO USERS COLLECTION VALIDATION - Uses provided user_id directly
    """
    
    # Generate task ID
    task_id = f"sms_process_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.user_id[:8]}"
    
    try:
        # NO USER VALIDATION - Use provided user_id directly
        logger.info(f"Processing SMS for user_id: {request.user_id}")
        
        # Check if MongoDB is available
        if db is None:
            raise HTTPException(
                status_code=503,
                detail="MongoDB connection not available. Please check your database connection."
            )
        
        # Create temporary file with SMS data
        sms_data_list = [sms.dict() for sms in request.sms_data]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(sms_data_list, temp_file, indent=2)
            temp_file_path = temp_file.name
        
        # Run pipeline asynchronously using user_id directly
        result = await run_pipeline_async(
            user_id=request.user_id,
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
            # Get processing statistics from actual collections
            if sms_data_collection is not None and financial_transactions_collection is not None:
                total_uploaded = sms_data_collection.count_documents({"user_id": ObjectId(request.user_id)})
                total_processed = sms_data_collection.count_documents({
                    "user_id": ObjectId(request.user_id),
                    "is_processed": True
                })
                total_financial = financial_transactions_collection.count_documents({
                    "user_id": ObjectId(request.user_id)
                })
            else:
                # Fallback when MongoDB is not available
                total_uploaded = len(request.sms_data)
                total_processed = len(request.sms_data)
                total_financial = 0
            
            return {
                "status": "success",
                "message": "SMS data processed successfully",
                "task_id": task_id,
                "user_id": request.user_id,
                "processed_at": datetime.now(),
                "statistics": {
                    "input_sms_count": len(request.sms_data),
                    "total_uploaded": total_uploaded,
                    "total_processed": total_processed,
                    "total_financial": total_financial
                },
                "pipeline_output": result["stdout"][-1000:] if result["stdout"] else ""
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
        logger.error(f"Unexpected error in process_sms_data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/api/v1/analytics/financial")
async def get_financial_analytics(request: FinancialAnalyticsRequest):
    """Get comprehensive financial analytics for a user"""
    try:
        start_date, end_date = get_date_range(request.period)
        
        # Convert user_id to ObjectId
        user_id_obj = ObjectId(request.user_id)
        
        # Query financial transactions
        query = {
            "user_id": user_id_obj,
            "transaction_date": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        
        transactions = list(user_financial_transactions_collection.find(query))
        
        # Calculate analytics
        total_income = sum(t.get("amount", 0) for t in transactions if t.get("transaction_type") == "credit")
        total_expense = sum(t.get("amount", 0) for t in transactions if t.get("transaction_type") == "debit")
        total_savings = total_income - total_expense
        expense_ratio = total_expense / total_income if total_income > 0 else 0
        
        income_transactions = [t for t in transactions if t.get("transaction_type") == "credit"]
        expense_transactions = [t for t in transactions if t.get("transaction_type") == "debit"]
        
        # Convert ObjectId fields to strings for JSON serialization
        transactions_serialized = convert_objectid_to_str(transactions)
        
        # Determine breakdown type based on period
        breakdown = {}
        if any(request.period.endswith(suffix) for suffix in ["_months"]) or request.period == "last_year":
            # Month-by-month breakdown for periods up to 1 year
            breakdown = get_monthly_breakdown(transactions, start_date, end_date)
        elif any(request.period.endswith(suffix) for suffix in ["_years"]):
            # Year-by-year breakdown for multi-year periods
            breakdown = get_yearly_breakdown(transactions, start_date, end_date)
        
        return {
            "user_id": request.user_id,
            "period": request.period,
            "start_date": start_date,
            "end_date": end_date,
            "total_income": total_income,
            "total_expense": total_expense,
            "total_savings": total_savings,
            "expense_ratio": expense_ratio,
            "transaction_count": len(transactions),
            "income_transactions": len(income_transactions),
            "expense_transactions": len(expense_transactions),
            "breakdown": breakdown,
            "transactions": transactions_serialized
        }
        
    except Exception as e:
        logger.error(f"Error in financial analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/income/{user_id}")
async def get_income_analytics(user_id: str, period: str = "last_month"):
    """Get income analytics for a user"""
    try:
        start_date, end_date = get_date_range(period)
        user_id_obj = ObjectId(user_id)
        
        query = {
            "user_id": user_id_obj,
            "transaction_type": "credit",
            "transaction_date": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        
        transactions = list(user_financial_transactions_collection.find(query))
        total_income = sum(t.get("amount", 0) for t in transactions)
        
        # Convert ObjectId fields to strings for JSON serialization
        transactions_serialized = convert_objectid_to_str(transactions)
        
        # Add breakdown for periods
        breakdown = {}
        if any(period.endswith(suffix) for suffix in ["_months"]) or period == "last_year":
            breakdown = get_monthly_breakdown(transactions, start_date, end_date)
        elif any(period.endswith(suffix) for suffix in ["_years"]):
            breakdown = get_yearly_breakdown(transactions, start_date, end_date)
        
        return {
            "user_id": user_id,
            "period": period,
            "total_income": total_income,
            "transaction_count": len(transactions),
            "breakdown": breakdown,
            "transactions": transactions_serialized
        }
        
    except Exception as e:
        logger.error(f"Error in income analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/expenses/{user_id}")
async def get_expense_analytics(user_id: str, period: str = "last_month"):
    """Get expense analytics for a user"""
    try:
        start_date, end_date = get_date_range(period)
        user_id_obj = ObjectId(user_id)
        
        query = {
            "user_id": user_id_obj,
            "transaction_type": "debit",
            "transaction_date": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        
        transactions = list(user_financial_transactions_collection.find(query))
        total_expense = sum(t.get("amount", 0) for t in transactions)
        
        # Convert ObjectId fields to strings for JSON serialization
        transactions_serialized = convert_objectid_to_str(transactions)
        
        # Add breakdown for periods
        breakdown = {}
        if any(period.endswith(suffix) for suffix in ["_months"]) or period == "last_year":
            breakdown = get_monthly_breakdown(transactions, start_date, end_date)
        elif any(period.endswith(suffix) for suffix in ["_years"]):
            breakdown = get_yearly_breakdown(transactions, start_date, end_date)
        
        return {
            "user_id": user_id,
            "period": period,
            "total_expense": total_expense,
            "transaction_count": len(transactions),
            "breakdown": breakdown,
            "transactions": transactions_serialized
        }
        
    except Exception as e:
        logger.error(f"Error in expense analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/users/{user_id}/transactions")
async def get_user_transactions(user_id: str, limit: int = 50, offset: int = 0):
    """Get user transactions with pagination"""
    try:
        user_id_obj = ObjectId(user_id)
        
        query = {"user_id": user_id_obj}
        
        # Get total count
        total_count = user_financial_transactions_collection.count_documents(query)
        
        # Get paginated results
        transactions = list(
            user_financial_transactions_collection
            .find(query)
            .sort("transaction_date", -1)
            .skip(offset)
            .limit(limit)
        )
        
        # Convert ObjectId fields to strings for JSON serialization
        transactions_serialized = convert_objectid_to_str(transactions)
        
        return {
            "user_id": user_id,
            "transactions": transactions_serialized,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/users/{user_id}/summary")
async def get_user_summary(user_id: str):
    """Get user summary statistics"""
    try:
        user_id_obj = ObjectId(user_id)
        
        # Count transactions
        total_transactions = user_financial_transactions_collection.count_documents(
            {"user_id": user_id_obj}
        )
        
        # Count SMS data
        total_sms = sms_data_collection.count_documents({"user_id": user_id_obj})
        processed_sms = sms_data_collection.count_documents({
            "user_id": user_id_obj,
            "is_processed": True
        })
        
        # Get recent transactions
        recent_transactions = list(
            user_financial_transactions_collection
            .find({"user_id": user_id_obj})
            .sort("transaction_date", -1)
            .limit(5)
        )
        
        # Calculate comprehensive financial metrics
        all_transactions = list(user_financial_transactions_collection.find({"user_id": user_id_obj}))
        total_income = sum(t.get("amount", 0) for t in all_transactions if t.get("transaction_type") == "credit")
        total_expense = sum(t.get("amount", 0) for t in all_transactions if t.get("transaction_type") == "debit")
        total_savings = total_income - total_expense
        expense_ratio = total_expense / total_income if total_income > 0 else 0
        
        # Convert ObjectId fields to strings for JSON serialization
        recent_transactions_serialized = convert_objectid_to_str(recent_transactions)
        
        return {
            "user_id": user_id,
            "statistics": {
                "total_sms": total_sms,
                "processed_sms": processed_sms,
                "total_transactions": total_transactions,
                "total_income": total_income,
                "total_expense": total_expense,
                "total_savings": total_savings,
                "expense_ratio": expense_ratio
            },
            "recent_transactions": recent_transactions_serialized
        }
        
    except Exception as e:
        logger.error(f"Error getting user summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
