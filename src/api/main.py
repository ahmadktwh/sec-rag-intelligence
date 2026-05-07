"""
SEC EDGAR Financial Intelligence API
FastAPI server with stateful multi-agent chat and Redis caching.
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from dotenv import load_dotenv

from .schemas import SearchRequest, SearchResponse
from .cache_manager import CacheManager
from ..vectorstore.search_engine import SearchEngine
from ..agents.graph import financial_analyst_app
from langchain_core.messages import HumanMessage

load_dotenv()

# ─── App Initialization ───────────────────────────────────────────────────────
app = FastAPI(
    title="SEC EDGAR Financial Intelligence API",
    description="""
**Enterprise-grade Multi-Agent RAG API** for analyzing SEC EDGAR filings.

## Features
- **Multi-Company Comparison**: Analyze AAPL vs AMZN vs GOOGL in one query
- **Conversation Memory**: AI remembers previous questions in the same session
- **Any AI Model**: Inject your own API key and choose any LLM (Gemini, GPT-4, Claude, etc.)
- **Zero Cost to Owner**: You bring your own API key
- **Powered by**: LangGraph Agents + Pinecone Vector DB + 50 S&P 500 Companies

## Supported Models (via LiteLLM)
- `gemini/gemini-2.5-pro` (Google)
- `gpt-4o` (OpenAI)
- `claude-3-5-sonnet-20241022` (Anthropic)
- `mistral/mistral-large` (Mistral)
- `ollama/llama3` (Local, no key needed)
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ─── Components ───────────────────────────────────────────────────────────────
search_engine = SearchEngine()
cache_manager = CacheManager()

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Pydantic Schemas ─────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    """
    Request body for the /chat endpoint.
    Supports multi-ticker comparison and custom LLM injection.
    """
    ticker: str = Field(
        ...,
        example="AAPL, AMZN",
        description="Single ticker or comma-separated list for comparison (e.g., 'AAPL, AMZN, GOOGL')"
    )
    query: str = Field(
        ...,
        example="Compare Apple and Amazon revenue for 2025",
        description="Your financial question"
    )
    thread_id: str = Field(
        default="default_session",
        example="user_abc_session_1",
        description="Unique session ID for conversation memory"
    )
    llm_model: Optional[str] = Field(
        default=None,
        example="gemini/gemini-2.5-pro",
        description="LiteLLM model string. Default uses server's configured model."
    )
    api_key: Optional[str] = Field(
        default=None,
        example="your-api-key-here",
        description="Your API key for the chosen model provider"
    )


class ChatResponse(BaseModel):
    thread_id: str
    tickers: List[str]
    query_type: str
    answer: str
    sources: List[str]
    confidence: float
    history_count: int
    model_used: str


# ─── Routes ──────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    """Health check — confirms the API is online."""
    return {
        "status": "online",
        "message": "SEC EDGAR Financial Intelligence API v2.0",
        "cache_enabled": cache_manager.enabled,
        "supported_tickers": 50,
        "data_source": "SEC EDGAR Official Filings"
    }


@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search(request: SearchRequest):
    """
    Direct vector search — returns raw matching chunks from SEC filings.
    Use /chat for AI-powered analysis.
    """
    cached = cache_manager.get_cached_response(request.ticker, request.query, request.top_k)
    if cached:
        return cached

    try:
        results = await search_engine.execute_search(
            ticker=request.ticker,
            query=request.query,
            top_k=request.top_k,
            year=request.year
        )
        response_data = {
            "ticker": request.ticker,
            "query": request.query,
            "results": results,
            "total_matches": len(results)
        }
        cache_manager.set_cached_response(request.ticker, request.query, request.top_k, response_data)
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=ChatResponse, tags=["Multi-Agent Chat"])
async def chat(request: ChatRequest):
    """
    **Stateful Multi-Agent Chat** — The main intelligence endpoint.

    - Supports multiple tickers: `"AAPL, AMZN"` for comparison analysis
    - Remembers conversation history via `thread_id`
    - Bring your own API key and model via `llm_model` + `api_key`
    - Powered by 5 specialized LangGraph agents
    """
    try:
        config = {"configurable": {"thread_id": request.thread_id}}

        inputs = {
            "messages": [HumanMessage(content=request.query)],
            "current_ticker": request.ticker,
            "tickers": [],  # Router will parse this
            "llm_model": request.llm_model or os.getenv("LLM_MODEL", "gemini/gemini-2.5-pro"),
            "api_key": request.api_key or "",
            "retry_count": 0,
        }

        result = await financial_analyst_app.ainvoke(inputs, config=config)

        return ChatResponse(
            thread_id=request.thread_id,
            tickers=result.get("tickers", [request.ticker]),
            query_type=result.get("query_type", "single_company"),
            answer=result.get("final_report", "No answer generated"),
            sources=result.get("citations", []),
            confidence=round(result.get("confidence", 0.0), 2),
            history_count=len(result.get("messages", [])),
            model_used=request.llm_model or os.getenv("LLM_MODEL", "gemini/gemini-2.5-pro")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
