import os
from datetime import datetime, date
from langchain.tools import tool
from langchain_community.utilities import SerpAPIWrapper
from app.core.config import settings, logger

# Initialize the SerpAPI wrapper once
os.environ["SERPAPI_API_KEY"] = settings.SERP_API_KEY
search_wrapper = SerpAPIWrapper(
    params={
        "engine": "google_hotels",
        "currency": "USD", # You can make this dynamic
    }
)
logger.info("Hotel Search Tool (SerpAPI) initialized.")

def validate_dates(checkin_date: str, checkout_date: str) -> tuple[bool, str]:
    """Validate that both dates are in the future and checkout is after checkin."""
    try:
        checkin = datetime.strptime(checkin_date, '%Y-%m-%d').date()
        checkout = datetime.strptime(checkout_date, '%Y-%m-%d').date()
        today = date.today()
        
        if checkin < today:
            return False, f"Check-in date {checkin_date} must be today or a future date."
        if checkout <= checkin:
            return False, f"Check-out date {checkout_date} must be after check-in date {checkin_date}."
        return True, ""
    except ValueError:
        return False, "Invalid date format. Please use YYYY-MM-DD format."

@tool("hotel_search")
def hotel_search_tool(location: str, checkin_date: str, checkout_date: str) -> str:
    """
    Searches for hotels in a specific location for given check-in and check-out dates.
    Args:
        location (str): The city or area to search for hotels in (e.g., 'Calangute, Goa').
        checkin_date (str): The check-in date in 'YYYY-MM-DD' format.
        checkout_date (str): The check-out date in 'YYYY-MM-DD' format.
    """
    # Validate dates first
    is_valid, error_message = validate_dates(checkin_date, checkout_date)
    if not is_valid:
        return f"Error: {error_message}"

    logger.info(f"Searching hotels in {location} from {checkin_date} to {checkout_date}")
    try:
        search_params = {
            "q": f"hotels in {location}",
            "check_in_date": checkin_date,
            "check_out_date": checkout_date,
        }
        logger.info(f"Calling SerpAPI with query: hotels in {location}")
        results = search_wrapper.run(str(search_params))
        
        # SerpAPI returns a string that needs to be evaluated if it contains a dict
        if "error" in results.lower():
            return f"Could not complete hotel search: {results}"

        return f"Hotel search results for {location}: {results}"
    except Exception as e:
        logger.error(f"An error occurred during hotel search: {e}", exc_info=True)
        return f"An unexpected error occurred during hotel search: {str(e)}"