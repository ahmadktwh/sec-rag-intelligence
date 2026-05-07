import pytest
import os
from dotenv import load_dotenv
from src.vectorstore.search_engine import SearchEngine

load_dotenv()

@pytest.mark.asyncio
async def test_search_engine_initialization():
    """Verify that search engine connects to Pinecone correctly."""
    engine = SearchEngine()
    assert engine.store is not None
    assert engine.store.index_name == os.getenv("PINECONE_INDEX_NAME")

@pytest.mark.asyncio
async def test_search_results_structure():
    """Verify that search results match our expected Pydantic schema."""
    engine = SearchEngine()
    # Test with a known ticker
    results = await engine.execute_search(ticker="AAPL", query="revenue", top_k=2)
    
    assert isinstance(results, list)
    if len(results) > 0:
        res = results[0]
        assert hasattr(res, "text")
        assert hasattr(res, "score")
        assert hasattr(res, "metadata")
        assert res.metadata["ticker"] == "AAPL"
