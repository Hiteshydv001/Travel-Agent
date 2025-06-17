from datetime import datetime, date
from langchain.tools import tool
from amadeus import Client, ResponseError
from app.core.config import settings, logger

# Initialize the Amadeus client once
amadeus_client = None
if all([settings.AMADEUS_CLIENT_ID, settings.AMADEUS_CLIENT_SECRET]):
    amadeus_client = Client(
        client_id=settings.AMADEUS_CLIENT_ID,
        client_secret=settings.AMADEUS_CLIENT_SECRET,
    )
    logger.info("Amadeus client initialized successfully.")
else:
    logger.warning("Amadeus credentials not found. Flight tool will be disabled.")

def validate_date(date_str: str) -> bool:
    """Validate that the date is in the future."""
    try:
        search_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        today = date.today()
        return search_date >= today
    except ValueError:
        return False

@tool("flight_search")
def flight_search_tool(origin: str, destination: str, departure_date: str) -> str:
    """
    Finds flight offers for a given route and date.
    The docstring for this tool is crucial as it's what the LLM uses to decide when to call it.
    Args:
        origin (str): The 3-letter IATA code for the origin city (e.g., 'DEL' for Delhi).
        destination (str): The 3-letter IATA code for the destination city (e.g., 'GOI' for Goa).
        departure_date (str): The departure date in 'YYYY-MM-DD' format.
    """
    if not amadeus_client:
        return "Error: Flight search is unavailable because Amadeus API credentials are not configured."

    # Validate the date
    if not validate_date(departure_date):
        return f"Error: The departure date {departure_date} must be today or a future date."

    logger.info(f"Searching flights: {origin} -> {destination} on {departure_date}")
    try:
        # Log the API call parameters for debugging
        params = {
            'originLocationCode': origin,
            'destinationLocationCode': destination,
            'departureDate': departure_date,
            'adults': 1,
            'max': 3
        }
        logger.info(f"Calling Amadeus API with parameters: {params}")
        
        response = amadeus_client.shopping.flight_offers_search.get(**params).data
        
        if not response:
            return f"No flights were found from {origin} to {destination} on {departure_date}."

        summaries = ["Here are the top flight options found:"]
        for offer in response:
            price = f"{offer['price']['total']} {offer['price']['currency']}"
            carrier = offer['validatingAirlineCodes'][0]
            departure_time = offer['itineraries'][0]['segments'][0]['departure']['at'].split('T')[1]
            arrival_time = offer['itineraries'][0]['segments'][-1]['arrival']['at'].split('T')[1]
            summary = f"- Flight with carrier {carrier} departing at {departure_time}, arriving at {arrival_time}. Price: {price}."
            summaries.append(summary)
        
        return "\n".join(summaries)

    except ResponseError as e:
        logger.error(f"Amadeus API Error: {e}")
        error_detail = e.description[0]['detail'] if e.description and 'detail' in e.description[0] else str(e)
        return f"Error from Amadeus API: {error_detail}"
    except Exception as e:
        logger.error(f"Unexpected error in flight search: {e}", exc_info=True)
        return f"An unexpected error occurred during flight search: {str(e)}"