import os
from pinecone import Pinecone
from dotenv import load_dotenv

def test_connection():
    load_dotenv()
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    
    print(f"Testing Pinecone with Key: {api_key[:10]}... (Length: {len(api_key)})")
    print(f"Index Name: {index_name}")
    
    try:
        pc = Pinecone(api_key=api_key)
        # Try to list indexes to verify key
        indexes = pc.list_indexes()
        print("✅ Connection Successful! Found indexes:")
        for idx in indexes:
            print(f" - {idx.name}")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    test_connection()
