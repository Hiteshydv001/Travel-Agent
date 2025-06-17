from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
from app.tools import all_tools

# Initialize the primary LLM used by the agent for tool-calling and reasoning.
# Using a powerful model like Gemini Pro is recommended for better agent performance.
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0,
    convert_system_message_to_human=True,
)

# This is the core prompt that instructs the agent on how to behave.
# It includes placeholders for the input and the agent's internal thought process ("scratchpad").
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a powerful travel planning assistant. Your goal is to create a complete and helpful itinerary. Use the tools provided to find all the necessary information. Do not make up information; rely on the tools for real-world data."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# Create the agent by binding the tools to the LLM.
# `create_tool_calling_agent` is the recommended way to build agents that leverage a model's native tool-use capabilities.
agent = create_tool_calling_agent(llm, all_tools, prompt)

# The AgentExecutor is the runtime for the agent. It's what actually calls the agent, executes the tools, and returns the response.
# `handle_parsing_errors=True` makes the agent more resilient if it generates a malformed tool call.
agent_executor = AgentExecutor(
    agent=agent, 
    tools=all_tools, 
    verbose=False, # Set to True for detailed console logging of agent's thoughts
    handle_parsing_errors=True
)