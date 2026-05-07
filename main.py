"""
SEC EDGAR Financial Intelligence RAG System — Entry Point
Author: Mujeeb Ahmad
"""

import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    print("🚀 Starting SEC EDGAR Financial Intelligence Backend...")
    print("📍 API Documentation: http://localhost:8000/docs")
    
    # Run the FastAPI app from src/api/main.py
    uvicorn.run(
        "src.api.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )
