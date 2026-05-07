from pydantic import BaseModel, Field
from typing import List, Optional

class SearchRequest(BaseModel):
    """
    Schema for the incoming search request.
    This ensures the user provides a valid ticker and a query string.
    """
    ticker: str = Field(..., example="AAPL", description="The stock ticker to search for.")
    query: str = Field(..., example="What are the main risk factors?", description="The question or search query.")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return.")
    year: Optional[str] = Field(None, example="2025", description="Optional year filter.")

class SearchResult(BaseModel):
    """
    Schema for a single search result match.
    """
    text: str = Field(..., description="The relevant text chunk found in the report.")
    score: float = Field(..., description="Similarity score (how relevant the result is).")
    metadata: dict = Field(..., description="Original metadata (Year, Filing Type, Source).")

class SearchResponse(BaseModel):
    """
    Schema for the final response sent back to the user.
    """
    ticker: str
    query: str
    results: List[SearchResult]
    total_matches: int
