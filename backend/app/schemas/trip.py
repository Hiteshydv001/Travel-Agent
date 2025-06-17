from pydantic import BaseModel, EmailStr
from typing import Optional, Literal

class ParsedTripRequest(BaseModel):
    """
    A validated, structured representation of the user's trip request.
    This schema is used to ensure the data extracted from the initial prompt is correct.
    """
    origin: str
    destination: str
    departure_date: str
    return_date: str
    user_email: Optional[EmailStr] = None

class TripRequest(BaseModel):
    """
    The input model for the /plan-trip API endpoint.
    """
    prompt: str

class StreamMessage(BaseModel):
    """
    Defines the structure of a single message in the response stream for the frontend.
    Using a literal type provides clear, predictable message types.
    """
    type: Literal["log", "result", "error"]
    content: str