from typing import Annotated, Sequence, TypedDict, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Shared Whiteboard for all 5 agents.
    Supports single-company AND multi-company comparison queries.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # === Input Context ===
    current_ticker: str          # Primary ticker (e.g. "AAPL")
    tickers: List[str]           # All tickers parsed from input (e.g. ["AAPL", "AMZN"])
    query_type: str              # "single_company" | "comparison" | "trend"
    llm_model: str               # Which model to use (injected by user)
    api_key: str                 # User's API key (injected at request time)

    # === Intermediate Data ===
    retrieved_docs: list         # Raw chunks from Pinecone (all tickers combined)
    answer: str                  # Analyst's draft answer
    citations: list              # Human-readable citations (NOT filenames/embeddings)
    confidence: float            # 0.0–1.0 quality score
    retry_count: int             # Guardrail retry tracker (prevents infinite loops)

    # === Final Output ===
    final_report: str
