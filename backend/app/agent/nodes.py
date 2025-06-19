import json
import time
from pydantic import ValidationError
from google.api_core.exceptions import ResourceExhausted
from datetime import datetime

from app.agent.graph import AgentState
from app.schemas.trip import ParsedTripRequest
# We will now import the main 'llm' instance (Gemini Pro) to use for all tasks.
from app.agent.agent_logic import agent_executor, llm
from app.core.config import logger
from app.tools.email_tool import send_email_tool

def retry_with_backoff(func, max_retries=3, initial_delay=1):
    """Helper function to retry operations with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except ResourceExhausted as e:
            if attempt == max_retries - 1:  # Last attempt
                raise
            delay = initial_delay * (2 ** attempt)  # Exponential backoff
            logger.warning(f"Rate limit hit, retrying in {delay} seconds...")
            time.sleep(delay)

# --- Agent Nodes: Each function represents a distinct step in the agent's workflow ---

def parse_user_prompt_node(state: AgentState) -> dict:
    """
    Parses the user's prompt to extract structured information.
    """
    logger.info("Executing Node: parse_user_prompt")
    
    try:
        # Get the user's prompt from the state
        user_prompt = state.get("user_prompt", "")
        if not user_prompt:
            return {
                "error": "No prompt provided. Please provide your trip details.",
                "intermediate_steps": ["❌ No trip details provided."]
            }
        
        # Create a more specific prompt for the LLM
        parse_prompt = f"""
        You are a travel request parser. Your task is to extract travel information from the user's request and format it as a JSON object.
        IMPORTANT: You must respond with ONLY a valid JSON object, no other text or explanation.

        User's travel request: {user_prompt}

        Extract the following information:
        1. Origin: The city they are traveling from
        2. Destination: The city they want to visit
        3. Departure Date: When they want to start (YYYY-MM-DD)
        4. Return Date: When they want to end (YYYY-MM-DD)
        5. Budget: Their budget (if mentioned)
        6. Preferences: Any specific preferences
        7. Email: Their email address (if provided)

        If any required information is missing, add it to the missing_info array.

        Respond with ONLY this JSON structure:
        {{
            "origin": "city name",
            "destination": "city name",
            "departure_date": "YYYY-MM-DD",
            "return_date": "YYYY-MM-DD",
            "budget": "amount or empty string",
            "preferences": ["preference1", "preference2"],
            "user_email": "email or empty string",
            "missing_info": ["list of missing fields"]
        }}

        Example response for "I want to go to Goa from Mumbai next week":
        {{
            "origin": "Mumbai",
            "destination": "Goa",
            "departure_date": "2024-06-24",
            "return_date": "2024-06-28",
            "budget": "",
            "preferences": [],
            "user_email": "",
            "missing_info": ["budget", "specific dates"]
        }}

        Remember: Respond with ONLY the JSON object, no other text.
        """
        
        # Get the response from the LLM and extract the content
        response = llm.invoke(parse_prompt)
        response_content = response.content.strip()
        
        # Clean up the response content
        response_content = response_content.replace("```json", "").replace("```", "").strip()
        
        # Try to find JSON content if there's any surrounding text
        try:
            # First try direct JSON parsing
            parsed_data = json.loads(response_content)
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from the text
            import re
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                try:
                    parsed_data = json.loads(json_match.group())
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from extracted content: {e}")
                    logger.error(f"Raw response content: {response_content}")
                    return {
                        "error": "Could not parse the response. Please try again with clearer trip details.",
                        "intermediate_steps": ["❌ Could not parse trip details. Please try again."]
                    }
            else:
                logger.error(f"No JSON object found in response: {response_content}")
                return {
                    "error": "Could not find valid trip details in the response. Please try again.",
                    "intermediate_steps": ["❌ Could not find valid trip details. Please try again."]
                }
        
        # Validate required fields
        missing_fields = []
        if not parsed_data.get("origin"):
            missing_fields.append("origin")
        if not parsed_data.get("destination"):
            missing_fields.append("destination")
        if not parsed_data.get("departure_date"):
            missing_fields.append("departure date")
        if not parsed_data.get("return_date"):
            missing_fields.append("return date")
        
        if missing_fields:
            return {
                "error": f"Missing required information: {', '.join(missing_fields)}. Please provide these details.",
                "intermediate_steps": [f"❌ Missing required information: {', '.join(missing_fields)}"]
            }
        
        # Convert dates to datetime objects
        try:
            departure_date = datetime.strptime(parsed_data["departure_date"], "%Y-%m-%d")
            return_date = datetime.strptime(parsed_data["return_date"], "%Y-%m-%d")
            
            # Validate dates
            if departure_date < datetime.now():
                return {
                    "error": "Departure date must be in the future.",
                    "intermediate_steps": ["❌ Departure date must be in the future."]
                }
            if return_date <= departure_date:
                return {
                    "error": "Return date must be after departure date.",
                    "intermediate_steps": ["❌ Return date must be after departure date."]
                }
        except ValueError as e:
            return {
                "error": f"Invalid date format: {str(e)}. Please use YYYY-MM-DD format.",
                "intermediate_steps": ["❌ Invalid date format. Please use YYYY-MM-DD format."]
            }
        
        # Create the parsed prompt object
        parsed_prompt = ParsedTripRequest(
            origin=parsed_data["origin"],
            destination=parsed_data["destination"],
            departure_date=parsed_data["departure_date"],
            return_date=parsed_data["return_date"],
            budget=parsed_data.get("budget", ""),
            preferences=parsed_data.get("preferences", []),
            user_email=parsed_data.get("user_email", ""),
            missing_info=parsed_data.get("missing_info", [])
        )
        
        return {
            "parsed_prompt": parsed_prompt,
            "intermediate_steps": state.get("intermediate_steps", []) + ["✅ Successfully parsed trip details."]
        }
            
    except Exception as e:
        logger.error(f"An unexpected error occurred in parse_user_prompt_node: {e}", exc_info=True)
        return {
            "error": f"An unexpected error occurred: {str(e)}",
            "intermediate_steps": ["❌ An unexpected error occurred while parsing your request."]
        }

def flight_search_node(state: AgentState) -> dict:
    """Node to search for flights with specific error handling for rate limits."""
    logger.info("Executing Node: flight_search")
    parsed = state["parsed_prompt"]
    task = f"Find flights from {parsed.origin} to {parsed.destination} on {parsed.departure_date}."
    
    try:
        def search_flights():
            result = agent_executor.invoke({"input": task})
            return result.get("output", "")

        output = retry_with_backoff(search_flights)
        
        if "error" in output.lower():
            return {"error": output}
        return {
            "flight_info": output,
            "intermediate_steps": state["intermediate_steps"] + ["✈️ Searched for flight options."]
        }
    except ResourceExhausted as e:
        logger.error(f"Google API rate limit exceeded during flight search: {e}")
        error_message = "The AI model is currently busy due to high demand. Please try again in a few minutes."
        return {"error": error_message}
    except Exception as e:
        logger.error(f"An unexpected error occurred in flight_search_node: {e}", exc_info=True)
        return {"error": "An unexpected error occurred while searching for flights."}

def hotel_search_node(state: AgentState) -> dict:
    """Node to search for hotels with specific error handling for rate limits."""
    logger.info("Executing Node: hotel_search")
    parsed = state["parsed_prompt"]
    
    # Convert airport code to proper location name
    location_mapping = {
        "GOI": "Goa, India",
        "DEL": "Delhi, India",
        "BOM": "Mumbai, India",
        "MAA": "Chennai, India",
        "BLR": "Bangalore, India",
        "HYD": "Hyderabad, India",
        "CCU": "Kolkata, India",
        "COK": "Kochi, India",
        "TRV": "Trivandrum, India",
        "PNQ": "Pune, India"
    }
    
    # Get the proper location name, defaulting to the original if not found in mapping
    location = location_mapping.get(parsed.destination, parsed.destination)
    
    task = f"Find hotels in {location} for check-in on {parsed.departure_date} and check-out on {parsed.return_date}."
    
    try:
        def search_hotels():
            result = agent_executor.invoke({"input": task})
            return result.get("output", "")

        output = retry_with_backoff(search_hotels)
        
        if "error" in output.lower():
            return {"error": output}
        return {
            "hotel_info": output,
            "intermediate_steps": state["intermediate_steps"] + ["🏨 Searched for accommodation options."]
        }
    except ResourceExhausted as e:
        logger.error(f"Google API rate limit exceeded during hotel search: {e}")
        error_message = "The AI model is currently busy due to high demand. Please try again in a few minutes."
        return {"error": error_message}
    except Exception as e:
        logger.error(f"An unexpected error occurred in hotel_search_node: {e}", exc_info=True)
        return {"error": "An unexpected error occurred while searching for hotels."}

def activities_search_node(state: AgentState) -> dict:
    """Node to search for local activities and attractions."""
    logger.info("Executing Node: activities_search")
    parsed = state["parsed_prompt"]
    task = f"What are some top attractions, local food to try, and cultural highlights in {parsed.destination}?"
    
    try:
        def search_activities():
            result = agent_executor.invoke({"input": task})
            return result.get("output", "")

        output = retry_with_backoff(search_activities)
        
        return {
            "activity_info": output,
            "intermediate_steps": state["intermediate_steps"] + ["🗺️ Researched local attractions and activities."]
        }
    except ResourceExhausted as e:
        logger.error(f"Google API rate limit exceeded during activity search: {e}")
        error_message = "The AI model is currently busy due to high demand. Please try again in a few minutes."
        return {"error": error_message}
    except Exception as e:
        logger.error(f"An unexpected error occurred in activities_search_node: {e}", exc_info=True)
        return {"error": "An unexpected error occurred while researching activities."}

def compile_plan_node(state: AgentState) -> dict:
    """
    Final node. It compiles all gathered information into a comprehensive, user-friendly plan.
    """
    logger.info("Executing Node: compile_plan")
    if state.get("error"):
        error_message = f"I apologize, but I couldn't complete your trip plan due to an issue:\n\n**Details:** {state['error']}"
        return {"final_plan": error_message}

    prompt = f"""
    You are a world-class travel agent. Your task is to compile a complete, well-formatted travel itinerary in Markdown format using the information below.
    Your tone should be friendly, helpful, and professional. If any piece of information is missing or unavailable (e.g., no hotels found), state that clearly and gracefully.

    **Original User Request:** {state['user_prompt']}
    ---
    **Flight Information Found:**
    {state.get('flight_info', 'No flight information was available or an error occurred.')}
    ---
    **Accommodation Information Found:**
    {state.get('hotel_info', 'No hotel information was available or an error occurred.')}
    ---
    **Local Activities & Recommendations:**
    {state.get('activity_info', 'No activity information was available.')}
    ---

    **Instructions:**
    1.  Start with a friendly greeting and a brief summary of the trip plan.
    2.  Create a clear "Flights" section with the details found.
    3.  Create an "Accommodation" section.
    4.  Create a "Suggested Itinerary & Activities" section. Organize the recommendations in a clear, easy-to-read format (like a list).
    5.  End with a friendly closing remark, like "Have a wonderful trip!".
    """
    try:
        def compile_final_plan():
            result = llm.invoke(prompt)
            return result.content

        final_plan = retry_with_backoff(compile_final_plan)
        return {"final_plan": final_plan}
    except ResourceExhausted as e:
        logger.error(f"Google API rate limit exceeded during plan compilation: {e}")
        return {"final_plan": "I apologize, but I'm currently experiencing high demand. Please try again in a few minutes."}
    except Exception as e:
        logger.error(f"An unexpected error occurred in compile_plan_node: {e}", exc_info=True)
        return {"final_plan": "An unexpected error occurred while compiling your trip plan. Please try again."}

def send_email_node(state: AgentState) -> dict:
    """
    Sends the final trip plan to the user's email if provided.
    """
    logger.info("Executing Node: send_email")
    
    # Check if we have a valid parsed prompt
    if "error" in state or "parsed_prompt" not in state:
        logger.info("No valid parsed prompt available, skipping email sending.")
        return {
            "intermediate_steps": state.get("intermediate_steps", []) + ["📧 No email sent due to incomplete trip details."]
        }
    
    parsed = state["parsed_prompt"]
    
    if not parsed.user_email:
        logger.info("No email address provided, skipping email sending.")
        return {
            "intermediate_steps": state["intermediate_steps"] + ["📧 No email address provided, skipping email sending."]
        }
    
    try:
        # Create the input for the email tool
        email_input = {
            "to_email": parsed.user_email,
            "subject": "Your Trip Plan",
            "body_html": state["final_plan"]
        }
        
        # Use invoke instead of direct call
        email_result = send_email_tool.invoke(email_input)
        
        if "error" in email_result.lower():
            logger.error(f"Failed to send email: {email_result}")
            return {
                "intermediate_steps": state["intermediate_steps"] + ["❌ Failed to send email."]
            }
        
        return {
            "intermediate_steps": state["intermediate_steps"] + ["📧 Trip plan sent to your email."]
        }
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending email: {e}", exc_info=True)
        return {
            "intermediate_steps": state.get("intermediate_steps", []) + ["❌ An error occurred while sending the email."]
        }