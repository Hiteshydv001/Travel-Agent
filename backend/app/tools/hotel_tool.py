from datetime import datetime
from langchain.tools import tool
from amadeus import Client, ResponseError, ClientError
from app.core.config import settings, logger

def validate_dates(checkin_date: str, checkout_date: str) -> tuple[bool, str]:
    """Validates that dates are logical and in the future."""
    try:
        checkin = datetime.strptime(checkin_date, '%Y-%m-%d').date()
        checkout = datetime.strptime(checkout_date, '%Y-%m-%d').date()
        today = datetime.now().date()
        
        if checkin < today:
            return False, f"Check-in date {checkin_date} must be today or a future date."
        if checkout <= checkin:
            return False, f"Check-out date {checkout_date} must be after the check-in date {checkin_date}."
        return True, ""
    except ValueError:
        return False, "Invalid date format. Please use YYYY-MM-DD format."

@tool("hotel_search")
def hotel_search_tool(location: str, check_in_date: str, check_out_date: str) -> str:
    """
    Searches for hotels in a specific city using the Amadeus API for given check-in and check-out dates.
    For the 'location' parameter, use a proper city name like 'Goa', 'Madrid', or 'New York'.
    """
    is_valid, error_msg = validate_dates(check_in_date, check_out_date)
    if not is_valid:
        return error_msg

    if not settings.AMADEUS_CLIENT_ID or not settings.AMADEUS_CLIENT_SECRET:
        return "Amadeus credentials are not configured."

    logger.info(f"Searching hotels in {location} from {check_in_date} to {check_out_date}")
    try:
        amadeus_client = Client(
            client_id=settings.AMADEUS_CLIENT_ID,
            client_secret=settings.AMADEUS_CLIENT_SECRET,
        )

        # Step 1: Get city code
        city_response = amadeus_client.reference_data.locations.get(
            keyword=location,
            subType='CITY'
        )

        if not city_response.data:
            return f"Could not find a city matching '{location}'. Try a major city like 'London', 'Goa', or 'New York'."

        city_code = city_response.data[0]['iataCode']
        logger.info(f"City code for {location} is {city_code}")

        # Step 2: Search for hotel offers with minimal required parameters
        hotel_offer_params = {
            'cityCode': city_code,
            'checkInDate': check_in_date,
            'checkOutDate': check_out_date,
            'roomQuantity': 1,
            'adults': 1,
            'view': 'LIGHT',
            'currency': 'INR'  # Adding currency for Indian locations
        }
        
        logger.info(f"Searching hotel offers with params: {hotel_offer_params}")

        try:
            hotel_response = amadeus_client.shopping.hotel_offers_search.get(**hotel_offer_params)
        except ResponseError as e:
            logger.error(f"Amadeus API error: {e}")
            if "400" in str(e):
                return f"Unable to find hotels in {location} for the specified dates. Please try different dates or location."
            return f"Error searching for hotels: {str(e)}"

        if not hotel_response.data:
            logger.warning("No hotel offers found or data is empty.")
            return f"No hotels found in {location} for the given dates. Try changing the city or dates."

        # Format the results
        summaries = [f"🏨 Hotel options in {location}:"]
        for offer in hotel_response.data[:5]:  # Limit to 5 results
            hotel = offer.get('hotel', {})
            hotel_name = hotel.get('name', 'Unnamed Hotel')
            address = hotel.get('address', {}).get('lines', [''])[0]
            rating = hotel.get('rating', 'No rating')
            price_info = offer.get('offers', [{}])[0].get('price', {})
            price = price_info.get('total', 'N/A')
            currency = price_info.get('currency', '')
            
            summary = f"- {hotel_name}\n  📍 {address}\n  ⭐ {rating}\n  💰 {price} {currency}"
            summaries.append(summary)

        return "\n".join(summaries)

    except Exception as e:
        logger.exception("Unexpected error during hotel search")
        return "An unexpected error occurred while searching for hotels. Please try again later."
