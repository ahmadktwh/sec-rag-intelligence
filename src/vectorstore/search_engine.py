import os
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
from .pinecone_store import PineconeStore
from ..api.schemas import SearchResult

# Setup Logging
logger = logging.getLogger(__name__)

class SearchEngine:
    """
    The brain behind searching. Connects the API requests to Pinecone vector lookups.
    """
    
    def __init__(self):
        load_dotenv()
        self.store = PineconeStore(
            index_name=os.getenv("PINECONE_INDEX_NAME"),
            api_key=os.getenv("PINECONE_API_KEY")
        )

    async def execute_search(self, ticker: str, query: str, top_k: int = 5, year: Optional[str] = None) -> List[SearchResult]:
        """
        Orchestrates the search process:
        1. Embeds the query
        2. Filters by ticker (and optionally year)
        3. Retrieves top-k matches from Pinecone
        """
        try:
            logger.info(f"Executing search for {ticker}: '{query}' (top_k={top_k})")
            
            # Use the similarity search method from our PineconeStore
            matches = self.store.similarity_search(
                query=query,
                ticker=ticker,
                k=top_k
            )
            
            results = []
            for match in matches:
                # Map Pinecone results to our SearchResult schema
                result = SearchResult(
                    text=match['metadata'].get('text', 'No content found'),
                    score=match['score'],
                    metadata={
                        "ticker": match['metadata'].get('ticker'),
                        "year": match['metadata'].get('year'),
                        "filing_type": match['metadata'].get('filing_type'),
                        "source": match['metadata'].get('source')
                    }
                )
                results.append(result)
                
            return results
            
        except Exception as e:
            logger.error(f"Search engine error: {e}")
            raise e
