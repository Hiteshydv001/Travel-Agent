import json
import time
from pydantic import ValidationError
from google.api_core.exceptions import ResourceExhausted

from app.agent.graph import AgentState
from app.schemas.trip import ParsedTripRequest
# We will now import the main 'llm' instance (Gemini Pro) to use for all tasks.
from app.agent.agent_logic import agent_executor, llm
from app.core.config import logger

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
    The first node in the graph. It parses the initial user prompt into a structured format
    using the main Gemini Pro model for maximum accuracy.
    """
    logger.info("Executing Node: parse_user_prompt")
    
    prompt_template = f"""
    You are a meticulous data extraction assistant. Your sole purpose is to analyze a user's travel request and extract key information into a JSON object. Do not be conversational. Your only output should be the JSON object.

    **Instructions:**
    1.  Today's date is `{__import__('datetime').date.today().strftime('%Y-%m-%d')}`. Use this to resolve relative dates like "next month" or "tomorrow".
    2.  You MUST provide a string value for "origin", "destination", "departure_date", and "return_date".
    3.  If you absolutely cannot determine one of these required values from the user's request, you MUST use the string "UNKNOWN" as its value. Do NOT use null, None, or omit the key.
    4.  Infer the 3-letter IATA code for all cities (e.g., San Francisco is SFO, London is LON).
    5.  Extract the user's email if it is present. If not, use null for the "user_email" field.

    **User Request:**
    "{state['user_prompt']}"

    **Output JSON:**
    """
    try:
        def parse_prompt():
            result = llm.invoke(prompt_template)
            cleaned_result = result.content.strip().replace("```json", "").replace("```", "").strip()
            parsed_json = json.loads(cleaned_result)
            return parsed_json

        parsed_json = retry_with_backoff(parse_prompt)

        for key, value in parsed_json.items():
            if value == "UNKNOWN":
                raise ValueError(f"Could not determine the '{key}' from your request. Please be more specific.")

        parsed_data = ParsedTripRequest(**parsed_json)
        return {
            "parsed_prompt": parsed_data,
            "intermediate_steps": ["✅ Validated trip details from your request."]
        }
    except ValueError as e:
        logger.error(f"LLM could not determine a required field: {e}")
        return {"error": str(e)}
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Failed to parse or validate LLM response: {e}")
        return {"error": "I had trouble understanding the details in your request. Please try rephrasing with a clear origin, destination, and specific dates."}
    except ResourceExhausted as e:
        logger.error(f"Google API rate limit exceeded during parsing: {e}")
        return {"error": "The AI service is currently busy due to high demand. Please try again in a few minutes."}
    except Exception as e:
        logger.error(f"An unexpected error occurred in parsing prompt: {e}", exc_info=True)
        return {"error": "An unexpected critical error occurred while processing your request."}

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
    task = f"Find hotels in {parsed.destination} for check-in on {parsed.departure_date} and check-out on {parsed.return_date}."
    
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