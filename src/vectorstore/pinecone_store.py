import os
import logging
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document

# Setup Logging
logger = logging.getLogger(__name__)

class PineconeStore:
    """
    Handles vector storage and retrieval using Pinecone and Google Gemini embeddings.
    """
    
    def __init__(self, index_name: str, api_key: str, environment: str = "us-east-1"):
        """
        Initialize Pinecone connection and Gemini embedding model.
        """
        load_dotenv()
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.index = self.pc.Index(index_name)
        
        # Initialize Gemini Embeddings ONCE (prevents memory leak)
        google_api_key = os.getenv("GOOGLE_API_KEY")
        self.doc_embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=google_api_key,
            task_type="retrieval_document"
        )
        # Separate query embedding model (different task_type, same singleton)
        self.query_embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=google_api_key,
            task_type="retrieval_query"
        )

    def upsert_documents(self, documents: List[Document], batch_size: int = 100):
        """
        Embeds and upserts documents to Pinecone in batches.
        """
        logger.info(f"Upserting {len(documents)} chunks to Pinecone index: {self.index_name}")
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            # Extract texts and metadata
            texts = [doc.page_content for doc in batch]
            metadatas = [doc.metadata for doc in batch]
            
            # Generate IDs (Ticker_ChunkIndex)
            ids = [f"{doc.metadata.get('ticker', 'UNK')}_{doc.metadata.get('chunk_index', idx)}" 
                   for idx, doc in enumerate(batch)]
            
            # Generate Embeddings (using singleton doc_embeddings)
            try:
                vectors = self.doc_embeddings.embed_documents(texts)
                
                # Prepare records for Pinecone
                records = []
                for id, vector, metadata, text in zip(ids, vectors, metadatas, texts):
                    # SEC chunks can be large, store text in metadata for retrieval
                    metadata['text'] = text 
                    records.append({
                        "id": id,
                        "values": vector,
                        "metadata": metadata
                    })
                
                # Upsert to Pinecone
                self.index.upsert(vectors=records)
                logger.info(f"Successfully upserted batch {i//batch_size + 1}")
                
            except Exception as e:
                logger.error(f"Failed to upsert batch starting at {i}: {e}")

    def delete_by_ticker(self, ticker: str):
        """
        Deletes all documents associated with a specific ticker.
        Essential for re-ingestion to prevent data corruption.
        """
        try:
            logger.info(f"Wiping out all existing data for ticker: {ticker}")
            self.index.delete(filter={"ticker": {"$eq": ticker}})
            logger.info(f"Successfully cleared index for {ticker}")
        except Exception as e:
            logger.error(f"Failed to delete records for {ticker}: {e}")

    def similarity_search(self, query: str, ticker: Optional[str] = None, k: int = 5) -> List[Dict]:
        """
        Performs a similarity search, optionally filtered by ticker.
        """
        # Generate query embedding (uses singleton — no memory leak)
        query_vector = self.query_embeddings.embed_query(query)
        
        # Setup filter
        filter_dict = {}
        if ticker:
            filter_dict["ticker"] = {"$eq": ticker}
            
        # Query Pinecone
        results = self.index.query(
            vector=query_vector,
            top_k=k,
            include_metadata=True,
            filter=filter_dict if filter_dict else None
        )
        
        return results['matches']

if __name__ == "__main__":
    # Test the store
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    
    # Initialize store
    store = PineconeStore(
        index_name=os.getenv("PINECONE_INDEX_NAME", "sec-rag-intelligence"),
        api_key=os.getenv("PINECONE_API_KEY")
    )
    
    # Test Search (Assuming data exists)
    print("\n[TEST] Testing search for 'revenue'...")
    results = store.similarity_search("What is the total revenue?", ticker="AAPL", k=3)
    
    for match in results:
        print(f"\nScore: {match['score']:.4f}")
        print(f"Ticker: {match['metadata']['ticker']}")
        print(f"Text: {match['metadata']['text'][:200]}...")
