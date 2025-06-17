from langchain.tools import tool
from app.core.config import logger

@tool("add_event_to_calendar")
def add_event_to_calendar_tool(summary: str, start_datetime: str, end_datetime: str, location: str = "") -> str:
    """
    (Placeholder) Adds an event to the user's primary Google Calendar.
    This tool is a placeholder and does not have a real implementation.
    Implementing Google Calendar requires a complex OAuth2 flow where the user must grant permission.
    This typically involves frontend and backend coordination to handle the authentication token.
    Args:
        summary (str): The title of the event (e.g., 'Flight to Goa').
        start_datetime (str): The start time in ISO format (e.g., '2024-12-01T09:00:00').
        end_datetime (str): The end time in ISO format (e.g., '2024-12-01T11:30:00').
        location (str): The location of the event (e.g., 'Delhi Airport (DEL)').
    """
    logger.warning("Calendar tool was called, but it is a placeholder.")
    log_message = f"--- CALENDAR EVENT (SKIPPED) ---\nEvent: {summary}\nStart: {start_datetime}\nEnd: {end_datetime}\nLocation: {location}"
    print(log_message)
    return "Skipped adding event to calendar. This feature is not fully implemented."