# This file centralizes all the agent's tools for easy import and management.
from .flight_tool import flight_search_tool
from .hotel_tool import hotel_search_tool
from .search_tool import web_search_tool
from .calendar_tool import add_event_to_calendar_tool
from .email_tool import send_email_tool

all_tools = [
    flight_search_tool,
    hotel_search_tool,
    web_search_tool,
    add_event_to_calendar_tool,
    send_email_tool,
]