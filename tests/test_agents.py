import pytest
from langchain_core.messages import HumanMessage
from src.agents.nodes import router_node
from src.agents.state import AgentState

@pytest.mark.asyncio
async def test_router_single_company():
    """Verify that router identifies a single company query."""
    state: AgentState = {
        "messages": [HumanMessage(content="What is Apple's revenue?")],
        "current_ticker": "AAPL",
        "retry_count": 0
    }
    result = await router_node(state)
    assert result["query_type"] == "single_company"
    assert "AAPL" in result["tickers"]

@pytest.mark.asyncio
async def test_router_comparison():
    """Verify that router identifies a comparison query."""
    state: AgentState = {
        "messages": [HumanMessage(content="Compare AAPL vs TSLA")],
        "current_ticker": "AAPL, TSLA",
        "retry_count": 0
    }
    result = await router_node(state)
    assert result["query_type"] == "comparison"
    assert "TSLA" in result["tickers"]
    assert "AAPL" in result["tickers"]
