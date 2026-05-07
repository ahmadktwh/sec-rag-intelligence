"""
Multi-Agent Nodes — SEC EDGAR Financial Intelligence System

5 Specialized Agents:
  1. Router      — Classifies query type and parses tickers
  2. Retrieval   — Fetches relevant chunks from Pinecone for ALL tickers
  3. Analyst     — Synthesizes professional financial analysis
  4. Citation    — Builds clean, human-readable source references
  5. Guardrail   — Quality check with real confidence scoring + retry logic
"""
import re
import os
import logging
from typing import Dict, Any, List
from langchain_core.messages import AIMessage
from ..vectorstore.pinecone_store import PineconeStore
from ..api.schemas import SearchResult
from .state import AgentState
from .llm_provider import LLMProvider

logger = logging.getLogger(__name__)

# ─── Singleton PineconeStore (no memory leak) ────────────────────────────────
_store: PineconeStore = None

def _get_store() -> PineconeStore:
    global _store
    if _store is None:
        _store = PineconeStore(
            index_name=os.getenv("PINECONE_INDEX_NAME"),
            api_key=os.getenv("PINECONE_API_KEY")
        )
    return _store


def _get_llm(state: AgentState) -> LLMProvider:
    """Returns LLMProvider using model/key from state (user-injected) or env defaults."""
    return LLMProvider(
        model=state.get("llm_model") or None,
        api_key=state.get("api_key") or None
    )


# ─── 1. ROUTER NODE ──────────────────────────────────────────────────────────
async def router_node(state: AgentState) -> Dict[str, Any]:
    """
    Parses the user's message to:
      - Detect query type (single/comparison/trend)
      - Extract all mentioned tickers from the query AND input
    Uses lightweight keyword rules — no expensive LLM call for simple routing.
    """
    last_message = state["messages"][-1].content
    raw_ticker = state.get("current_ticker", "")

    # --- Parse tickers ---
    # 1. Split comma/space-separated tickers from input field (e.g. "AAPL, AMZN")
    parsed = [t.strip().upper() for t in re.split(r"[,\s]+", raw_ticker) if t.strip()]

    # 2. Also scan the query text for any uppercase 2–5 letter words that look like tickers
    query_tickers = re.findall(r"\b[A-Z]{2,5}\b", last_message)
    known_tickers = {
        "AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","JPM","V","UNH",
        "MA","JNJ","PG","AVGO","HD","XOM","MRK","COST","ABBV","CVX",
        "ADBE","CRM","BAC","KO","PEP","MCD","CSCO","NFLX","TMO","ABT",
        "AMD","ORCL","WMT","INTU","DIS","DHR","PFE","NKE","VZ","TXN",
        "PM","AMAT","COP","RTX","QCOM","UPS","IBM","LOW","CAT","GE"
    }
    for qt in query_tickers:
        if qt in known_tickers and qt not in parsed:
            parsed.append(qt)

    tickers = parsed if parsed else ["AAPL"]

    # --- Detect query type ---
    msg_lower = last_message.lower()
    if len(tickers) > 1 or any(w in msg_lower for w in ["vs", "versus", "compare", "comparison", "against", "both", "which"]):
        query_type = "comparison"
    elif any(w in msg_lower for w in ["trend", "over years", "since", "history", "growth", "yoy", "year over year"]):
        query_type = "trend"
    else:
        query_type = "single_company"

    logger.info(f"ROUTER → type={query_type}, tickers={tickers}")
    return {
        "query_type": query_type,
        "tickers": tickers,
        "current_ticker": tickers[0],
        "retry_count": state.get("retry_count", 0)
    }


# ─── 2. RETRIEVAL NODE ───────────────────────────────────────────────────────
async def retrieval_node(state: AgentState) -> Dict[str, Any]:
    """
    Fetches relevant chunks from Pinecone for ALL tickers in the query.
    For comparison queries, retrieves data for each company separately
    then merges results so the Analyst has full context.
    """
    query = state["messages"][-1].content
    tickers = state.get("tickers") or [state.get("current_ticker", "AAPL")]
    store = _get_store()

    all_docs = []
    # Enhance query for better financial retrieval if needed
    search_query = query
    if any(word in query.lower() for word in ["buy", "compare", "performance", "revenue", "profit", "financial"]):
        search_query = f"{query} consolidated statements of income revenue net income earnings per share balance sheet"
        logger.info(f"RETRIEVAL → Enhanced query: {search_query}")

    for ticker in tickers:
        logger.info(f"RETRIEVAL → Fetching for {ticker}")
        try:
            # Increased k to 15 to ensure we get tables and numbers
            matches = store.similarity_search(query=search_query, ticker=ticker, k=15)
            for match in matches:
                result = SearchResult(
                    text=match["metadata"].get("text", ""),
                    score=match["score"],
                    metadata={
                        "ticker": match["metadata"].get("ticker", ticker),
                        "year": match["metadata"].get("year", "N/A"),
                        "filing_type": match["metadata"].get("filing_type", "10-K"),
                        "source": match["metadata"].get("source", ""),
                        "chunk_index": match["metadata"].get("chunk_index", 0),
                        "total_chunks": match["metadata"].get("total_chunks", 0),
                    }
                )
                all_docs.append(result)
        except Exception as e:
            logger.error(f"Retrieval error for {ticker}: {e}")

    logger.info(f"RETRIEVAL → Total chunks fetched: {len(all_docs)} across {tickers}")
    return {"retrieved_docs": all_docs}


# ─── 3. ANALYST NODE ─────────────────────────────────────────────────────────
async def analyst_node(state: AgentState) -> Dict[str, Any]:
    """
    Senior Financial Analyst agent.
    Uses retrieved chunks + full conversation history to write a
    structured, professional financial report.
    """
    docs: List[SearchResult] = state.get("retrieved_docs", [])
    tickers = state.get("tickers", [state.get("current_ticker", "AAPL")])
    query_type = state.get("query_type", "single_company")

    # Build structured context grouped by ticker
    context_sections = []
    ticker_data: Dict[str, List[str]] = {}
    for doc in docs:
        t = doc.metadata.get("ticker", "Unknown")
        if t not in ticker_data:
            ticker_data[t] = []
        ticker_data[t].append(doc.text)

    for t, chunks in ticker_data.items():
        # Removed truncation to ensure all 15 chunks are analyzed
        section = f"=== {t} SEC Filing Data ===\n" + "\n\n".join(chunks)
        context_sections.append(section)

    context = "\n\n".join(context_sections) if context_sections else "No relevant data found in filings."

    # Build conversation history string (last 6 turns)
    history = state["messages"][-6:]
    history_str = "\n".join([
        f"{'User' if hasattr(m, 'type') and m.type == 'human' else 'Analyst'}: {m.content[:300]}"
        for m in history[:-1]  # Exclude current message
    ])

    # ── ADVANCED SYSTEM PROMPT ──────────────────────────────────────────────
    common_instructions = """
You are a Senior Financial Analyst at a top-tier firm. You must output your ENTIRE response in highly structured, professional Markdown. 
DO NOT use any custom XML tags or artifacts. Your entire response will be displayed in the main interface.

STRICT FORMATTING RULES:
1. Use `##` for main section headers (e.g., `## Executive Summary`, `## Financial Performance`).
2. Use `###` for sub-sections.
3. ALWAYS include a detailed Markdown table for financial data.
4. Use **bold** text to highlight key numbers or metrics.
5. Use bullet points (`*` or `-`) for lists to ensure readability.

REQUIRED STRUCTURE:
## Executive Summary
[A concise, 2-3 sentence overview]

## Financial Metrics
[A detailed Markdown table comparing the companies or showing the trend. Columns MUST be aligned properly.]

## Segment Analysis & Insights
[Bullet points detailing specific operational insights]

## Investment Verdict
[Final, decisive conclusion]
"""

    if query_type == "comparison" and len(tickers) > 1:
        system_prompt = f"""{common_instructions}
Your task: Provide a COMPREHENSIVE COMPARATIVE ANALYSIS of {", ".join(tickers)} based on SEC 10-K filings."""
    elif query_type == "trend":
        system_prompt = f"""{common_instructions}
Your task: Analyze the historical financial trends for {", ".join(tickers)}."""
    else:
        system_prompt = f"""{common_instructions}
Your task: Provide a detailed analysis of {tickers[0]} based on SEC filings."""

    # Full prompt to LLM
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"""PREVIOUS CONVERSATION:
{history_str}

SEC FILING CONTEXT:
{context}

CURRENT QUESTION: {state['messages'][-1].content}

Provide your professional analysis:"""}
    ]

    llm = _get_llm(state)
    answer = await llm.ainvoke(messages, temperature=0.1)

    logger.info(f"ANALYST → Generated {len(answer)} char response for {tickers}")
    return {"answer": answer}


# ─── 4. CITATION NODE ────────────────────────────────────────────────────────
async def citation_node(state: AgentState) -> Dict[str, Any]:
    """
    Builds human-readable citations from document metadata.
    Shows: Company, Filing Type, Fiscal Year, Section — NOT filenames or vectors.
    """
    docs: List[SearchResult] = state.get("retrieved_docs", [])
    citations = []
    seen = set()

    for i, doc in enumerate(docs):
        meta = doc.metadata
        ticker = meta.get("ticker", "Unknown")
        year = meta.get("year", "N/A")
        filing_type = meta.get("filing_type", "10-K")
        chunk_idx = meta.get("chunk_index", 0)
        total = meta.get("total_chunks", 0)

        # Estimate section from chunk position
        if total > 0:
            position_pct = chunk_idx / total
            if position_pct < 0.15:
                section = "Business Overview (Part I, Item 1)"
            elif position_pct < 0.30:
                section = "Risk Factors (Part I, Item 1A)"
            elif position_pct < 0.50:
                section = "Management's Discussion & Analysis (Part II, Item 7)"
            elif position_pct < 0.70:
                section = "Financial Statements (Part II, Item 8)"
            else:
                section = "Notes to Financial Statements (Part II, Item 8)"
        else:
            section = "Financial Report"

        # Deduplicate citations
        key = f"{ticker}_{year}_{section}"
        if key not in seen:
            seen.add(key)
            citation = f"[{len(citations)+1}] {ticker} | {filing_type} Filing | Fiscal Year {year} | {section} | Relevance Score: {doc.score:.2f}"
            citations.append(citation)

    logger.info(f"CITATION → Generated {len(citations)} unique citations")
    return {"citations": citations}


# ─── 5. GUARDRAIL NODE ───────────────────────────────────────────────────────
async def guardrail_node(state: AgentState) -> Dict[str, Any]:
    """
    Quality control agent.
    Uses LLM to self-assess confidence instead of brittle string matching.
    Retries retrieval if confidence < threshold (max 2 retries).
    """
    answer = state.get("answer", "")
    docs = state.get("retrieved_docs", [])
    retry_count = state.get("retry_count", 0)

    # Use LLM for real confidence scoring
    if answer and docs:
        llm = _get_llm(state)
        confidence_prompt = [
            {"role": "system", "content": "You are a quality control reviewer for financial analysis. Rate the quality of an answer on a scale of 0.0 to 1.0. Respond with ONLY a number between 0.0 and 1.0."},
            {"role": "user", "content": f"""Rate this financial analysis answer:

ANSWER: {answer[:800]}

Criteria:
- Contains specific financial figures (high score)
- Directly answers the question (high score)
- Says it lacks data without trying (low score)
- Very short or vague (low score)
- Contains fabricated/made-up numbers (very low score)

Score (0.0–1.0):"""}
        ]
        try:
            score_str = await llm.ainvoke(confidence_prompt, temperature=0)
            # Extract first float found in response
            import re
            matches = re.findall(r"0?\.\d+|1\.0|[01]", score_str)
            confidence = float(matches[0]) if matches else 0.8
            confidence = min(max(confidence, 0.0), 1.0)
        except Exception:
            # Fallback to heuristic if LLM fails
            confidence = 0.9 if len(answer) > 300 and docs else 0.4
    elif not docs:
        confidence = 0.2
    else:
        confidence = 0.5

    logger.info(f"GUARDRAIL → confidence={confidence:.2f}, retry_count={retry_count}")

    # Build final report with proper citations
    citations_text = "\n".join(state.get("citations", []))
    if citations_text:
        final_report = f"{answer}\n\n---\n**Sources (SEC Official Filings)**\n{citations_text}"
    else:
        final_report = answer

    return {
        "confidence": confidence,
        "retry_count": retry_count + 1,
        "final_report": final_report,
        "messages": [AIMessage(content=final_report)]
    }
