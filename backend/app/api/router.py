import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langgraph.graph import StateGraph, END
from app.schemas.trip import TripRequest, StreamMessage
from app.agent.graph import AgentState
from app.agent.nodes import (
    parse_user_prompt_node, flight_search_node, hotel_search_node,
    activities_search_node, compile_plan_node, send_email_node
)
from app.core.config import logger

router = APIRouter()

# --- Define the Conditional Logic for the Graph ---
def should_continue(state: AgentState) -> str:
    """
    This function is the "brain" of the graph's control flow.
    It checks if an error has occurred in the previous step.
    If an error exists, it routes the graph to the final 'compile_plan' node to format the error message.
    Otherwise, it continues to the next logical step.
    """
    if state.get("error"):
        logger.warning(f"Error detected in agent state: '{state['error']}'. Routing to end.")
        return "end_with_error"
    return "continue_to_next_step"

# --- Build the Agentic Graph ---
workflow = StateGraph(AgentState)

# Add nodes to the graph
workflow.add_node("parse_user_prompt", parse_user_prompt_node)
workflow.add_node("find_flights", flight_search_node)
workflow.add_node("find_hotels", hotel_search_node)
workflow.add_node("find_activities", activities_search_node)
workflow.add_node("compile_plan", compile_plan_node)
workflow.add_node("send_email", send_email_node)

# Define the graph's structure with edges and conditional logic
workflow.set_entry_point("parse_user_prompt")

workflow.add_conditional_edges(
    "parse_user_prompt",
    should_continue,
    {"continue_to_next_step": "find_flights", "end_with_error": "compile_plan"}
)
workflow.add_conditional_edges(
    "find_flights",
    should_continue,
    {"continue_to_next_step": "find_hotels", "end_with_error": "compile_plan"}
)
workflow.add_conditional_edges(
    "find_hotels",
    should_continue,
    {"continue_to_next_step": "find_activities", "end_with_error": "compile_plan"}
)
workflow.add_edge("find_activities", "compile_plan")
workflow.add_edge("compile_plan", "send_email")
workflow.add_edge("send_email", END)

# Compile the graph into a runnable application
app_graph = workflow.compile()

# --- Define the API Endpoint ---
async def run_agent_stream(prompt: str):
    """
    Runs the agent graph and yields structured JSON events for the frontend
    in a server-sent event (SSE) stream.
    """
    # Use a unique thread ID for each request to ensure state isolation
    config = {"configurable": {"thread_id": f"trip-{__import__('uuid').uuid4()}"}}
    initial_state = {"user_prompt": prompt, "intermediate_steps": []}

    try:
        # `astream_events` provides real-time visibility into the graph's execution
        async for event in app_graph.astream_events(initial_state, config, version="v1"):
            kind = event["event"]
            
            # We are interested in when a node finishes its execution
            if kind == "on_chain_end":
                node_name = event["name"]
                
                # Stream intermediate log messages to the frontend
                if node_name in ["parse_user_prompt", "find_flights", "find_hotels", "find_activities"]:
                    node_output = event["data"]["output"]
                    if node_output and node_output.get("intermediate_steps"):
                        latest_step_log = node_output["intermediate_steps"][-1]
                        msg = StreamMessage(type="log", content=latest_step_log)
                        yield f"data: {msg.model_dump_json()}\n\n"
                
                # When the final plan is compiled, stream it as the result
                elif node_name == "compile_plan":
                    final_plan = event["data"]["output"].get("final_plan")
                    if final_plan:
                        msg_type = "error" if "error" in final_plan.lower() else "result"
                        msg = StreamMessage(type=msg_type, content=final_plan)
                        yield f"data: {msg.model_dump_json()}\n\n"
                        
    except Exception as e:
        logger.error(f"An unhandled exception occurred in the agent stream: {e}", exc_info=True)
        error_msg = StreamMessage(type="error", content=f"A critical error occurred: {str(e)}")
        yield f"data: {error_msg.model_dump_json()}\n\n"

@router.post("/plan-trip", tags=["Agent"])
async def plan_trip_endpoint(request: TripRequest):
    """
    Takes a user prompt and returns a stream of events as the AI agent plans the trip.
    The stream provides structured JSON messages for logs, results, and errors.
    """
    return StreamingResponse(run_agent_stream(request.prompt), media_type="text/event-stream")