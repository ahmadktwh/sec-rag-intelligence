import os
from pinecone import Pinecone
from dotenv import load_dotenv

def list_tickers():
    load_dotenv()
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    
    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)
    
    # Since we can't easily list unique metadata values in Pinecone without a full scan
    # we'll use the stats and some common tickers to check density
    stats = index.describe_index_stats()
    print(f"Index Stats: {stats}")
    
    # Check for some common tickers to see what's already there
    test_tickers = ["MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "V", "JNJ", "WMT"]
    found = []
    for ticker in test_tickers:
        res = index.query(vector=[0]*3072, top_k=1, filter={"ticker": {"$eq": ticker}})
        if res.get("matches"):
            found.append(ticker)
    
    print(f"Sample tickers already in DB: {found}")

if __name__ == "__main__":
    list_tickers()
