"""
AGI Dashboard startup — run this from the backend/ folder
"""
import uvicorn, os, sys

if __name__ == "__main__":
    # Add parent to path so "src/" pipeline code is accessible
    sys.path.insert(0, os.path.dirname(__file__))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENV", "production") == "development",
        log_level="info",
    )