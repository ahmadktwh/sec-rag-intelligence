"""
LangGraph Multi-Agent Orchestration
Flow: Router → Retrieval → Analyst → Citation → Guardrail → (Retry/End)
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .state import AgentState
from .nodes import router_node, retrieval_node, analyst_node, citation_node, guardrail_node

MAX_RETRIES = 2
CONFIDENCE_THRESHOLD = 0.65


def should_continue(state: AgentState) -> str:
    """
    Conditional edge: retry retrieval if confidence is low AND retries remain.
    Uses retry_count (not message count) to prevent infinite loops.
    """
    confidence = state.get("confidence", 1.0)
    retry_count = state.get("retry_count", 0)

    if confidence < CONFIDENCE_THRESHOLD and retry_count < MAX_RETRIES:
        logger_msg = f"GUARDRAIL: confidence={confidence:.2f} < {CONFIDENCE_THRESHOLD}, retry {retry_count}/{MAX_RETRIES}"
        print(f"--- {logger_msg} ---")
        return "retrieval"  # Loop back for better data

    return END


def create_financial_graph():
    """
    Creates the 5-Agent Multi-Company Financial Analysis Graph.
    Supports single company, multi-company comparison, and trend queries.
    """
    workflow = StateGraph(AgentState)

    # Add all 5 specialist nodes
    workflow.add_node("router", router_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("citation", citation_node)
    workflow.add_node("guardrail", guardrail_node)

    # Define flow
    workflow.set_entry_point("router")
    workflow.add_edge("router", "retrieval")
    workflow.add_edge("retrieval", "analyst")
    workflow.add_edge("analyst", "citation")
    workflow.add_edge("citation", "guardrail")

    # Conditional: retry or end
    workflow.add_conditional_edges("guardrail", should_continue)

    # In-memory checkpointer (conversation memory per thread_id)
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# Singleton graph instance
financial_analyst_app = create_financial_graph()
