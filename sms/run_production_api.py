#!/usr/bin/env python3
"""
Production script to run the Financial Chat API
Uses the production-ready implementation with all features
"""

import uvicorn
from src.financial_chat_api_production import app

if __name__ == "__main__":
    print("🚀 Starting Financial Chat API - PRODUCTION VERSION")
    print("=" * 60)
    print("✅ Features:")
    print("  • IST ↔ UTC timezone conversion")
    print("  • BSON Date handling")
    print("  • debitAmount calculation in all pipelines")
    print("  • 9 exact fallback templates")
    print("  • Versioned caching system")
    print("  • Parallel execution")
    print("  • GroundingContext validation")
    print("  • Real schema: user_financial_transactions")
    print()
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    print("💬 Chat Endpoint: POST http://localhost:8000/chat")
    print("=" * 60)
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
