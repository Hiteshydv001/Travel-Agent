from typing import TypedDict, List, Optional
from app.schemas.trip import ParsedTripRequest

class AgentState(TypedDict):
    """
    Defines the state of our agent. This state is passed between nodes in the graph,
    allowing each step to access data from previous steps.
    """
    user_prompt: str
    parsed_prompt: Optional[ParsedTripRequest] # Use the validated Pydantic model
    flight_info: Optional[str]
    hotel_info: Optional[str]
    activity_info: Optional[str]
    final_plan: Optional[str]
    error: Optional[str] # A dedicated field to track if an error has occurred
    intermediate_steps: List[str] # A log of actions taken for streaming to the frontend