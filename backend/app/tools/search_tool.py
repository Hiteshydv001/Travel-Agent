import os
from langchain.tools import Tool
from langchain_community.utilities import SerpAPIWrapper
from app.core.config import settings

def _create_web_search_tool() -> Tool:
    """Initializes and returns the SerpAPI web search tool."""
    os.environ["SERPAPI_API_KEY"] = settings.SERP_API_KEY
    search = SerpAPIWrapper()
    return Tool(
        name="web_search",
        func=search.run,
        description="A general-purpose web search tool. Use it to find information about activities, local culture, restaurants, or any other real-time information.",
    )

web_search_tool = _create_web_search_tool()