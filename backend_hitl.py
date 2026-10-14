
import os
import psycopg
import requests
import math

from pathlib import Path
from dotenv import load_dotenv
from psycopg.rows import dict_row

from typing import TypedDict, Annotated,Any
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres import PostgresSaver
from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage,SystemMessage
from langgraph.prebuilt import tools_condition,ToolNode
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langgraph.types import interrupt,Command

load_dotenv()
os.environ["TAVILY_API_KEY"]=os.getenv("TAVILY_API_KEY")


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

model = init_chat_model(
    "openai/gpt-oss-120b",
    model_provider="groq",
    temperature=0.2
)

embedding_model=GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
)


SYSTEM_PROMPT = """
You are a helpful AI assistant with access to tools.

Tool usage rules:

1. For tavily_search:
- You MUST provide the required argument named "query".
- Never call tavily_search with an empty argument object.
- Example valid call: tavily_search({"query": "latest world news today"}).
- For weather requests, use get_current_weather instead of web search
  unless the user also requests related news or web research.

2. Use get_current_weather for current weather.
   Always provide the required `location` argument.

3. Use get_stock_price for stock prices.
   Always provide the required `company` argument.
   Prefer stock symbols such as AAPL, MSFT, and TSLA.
   If the company or exchange is ambiguous, ask the user to clarify.

4. Use calculator for mathematical calculations.
   Always provide the required `expression` argument.

5. Use `rag_tool` for questions about the uploaded PDF or document. "
   "Always retrieve relevant document content before answering PDF-related questions."

5. When a request requires multiple tools, call each relevant tool
   with all required arguments. Never invent missing tool results.

6. After receiving tool results, answer in natural language.
   For web research, include source URLs when available.

7. If a tool reports an error, explain it honestly.
"""

def ingest_rag_document(file_path):
    DB_PATH = "faiss_db"
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    vector_store = FAISS.from_documents(chunks, embedding_model)
    vector_store.save_local(DB_PATH)
    


def get_retriever():
    DB_PATH = "faiss_db"
    vector_store = FAISS.load_local(
            folder_path=DB_PATH,
            embeddings=embedding_model,
            allow_dangerous_deserialization=True
        )
    
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}
    )

    return retriever


# Tools


# Initialize Tavily
web_search_tool = TavilySearch(
    max_results=5,
    topic="general",
    search_depth="advanced",
)

@tool
def tavily_search(query: str) -> str:
    """Search the web for current news, recent events, and factual information.

    Args:
        query: A specific, non-empty web search query.
    """
    if not query or not query.strip():
        return "Error: Search query cannot be empty."

    try:
        result = web_search_tool.invoke({
            "query": query.strip()
        })
        return str(result)

    except Exception as error:
        return f"Web search failed: {error}"
    
@tool
def calculator(expression: str) -> str:
    """
    Useful for simple math calculations.
    Input should be a valid math expression.
    Example: 2 + 2, math.sqrt(16), 10 * 5
    """

    try:
        allowed = {
            "math": math,
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum
        }

        result = eval(expression, {"__builtins__": {}}, allowed)
        return str(result)

    except Exception as e:
        return f"Calculation error: {str(e)}"

@tool
def get_stock_price(company:str)->dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={company}&interval=5min&apikey=R0LOZRN8U0ENG0C0'
    r = requests.get(url)
    return r.json()

@tool
def purchase_stock(symbol: str, quantity: int) -> dict:
    """
    Simulate purchasing a given quantity of a stock symbol.

    HUMAN-IN-THE-LOOP:
    Before confirming the purchase, this tool will interrupt
    and wait for a human decision ("yes" / anything else).
    """
    # This pauses the graph and returns control to the caller
    decision = interrupt(f"Approve buying {quantity} shares of {symbol}? (yes/no)")

    if isinstance(decision, str) and decision.lower() == "yes":
        return {
            "status": "success",
            "message": f"Purchase order placed for {quantity} shares of {symbol}.",
            "symbol": symbol,
            "quantity": quantity,
        }
    
    else:
        return {
            "status": "cancelled",
            "message": f"Purchase of {quantity} shares of {symbol} was declined by human.",
            "symbol": symbol,
            "quantity": quantity,
        }



@tool
def get_current_weather(location: str) -> str:
    """
    Get current weather for a city or location.

    Args:
        location: City name, e.g. Hyderabad, London, UK.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")

    if not api_key:
        return "Error: OPENWEATHER_API_KEY environment variable is missing."

    try:
        # Step 1: Convert location into latitude and longitude
        geo_url = "https://api.openweathermap.org/geo/1.0/direct"

        geo_response = requests.get(
            geo_url,
            params={
                "q": location,
                "limit": 1,
                "appid": api_key,
            },
            timeout=10,
        )
        geo_response.raise_for_status()

        locations: list[dict[str, Any]] = geo_response.json()

        if not locations:
            return f"Could not find location: {location}"

        latitude = locations[0]["lat"]
        longitude = locations[0]["lon"]

        city = locations[0].get("name", location)
        state = locations[0].get("state", "")
        country = locations[0].get("country", "")

        display_location = ", ".join(
            part for part in [city, state, country] if part
        )

        # Step 2: Fetch current weather using coordinates
        weather_url = "https://api.openweathermap.org/data/2.5/weather"

        weather_response = requests.get(
            weather_url,
            params={
                "lat": latitude,
                "lon": longitude,
                "appid": api_key,
                "units": "metric",
            },
            timeout=10,
        )
        weather_response.raise_for_status()

        data = weather_response.json()

        # Step 3: Extract weather information
        temperature = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        pressure = data["main"]["pressure"]
        description = data["weather"][0]["description"]
        wind_speed = data.get("wind", {}).get("speed", "N/A")

        visibility_meters = data.get("visibility")
        visibility_km = (
            round(visibility_meters / 1000, 1)
            if visibility_meters is not None
            else "N/A"
        )

        # Step 4: Format the result
        return (
            f"Current weather in {display_location}:\n"
            f"- Condition: {description.title()}\n"
            f"- Temperature: {temperature}°C\n"
            f"- Feels like: {feels_like}°C\n"
            f"- Humidity: {humidity}%\n"
            f"- Pressure: {pressure} hPa\n"
            f"- Wind speed: {wind_speed} m/s\n"
            f"- Visibility: {visibility_km} km"
        )

    except requests.exceptions.Timeout:
        return "Error: Weather service request timed out."

    except requests.exceptions.HTTPError as error:
        status = error.response.status_code if error.response else 0

        if status == 401:
            return "Error: Invalid or inactive OpenWeather API key."
        if status == 404:
            return f"Error: Weather data not found for {location}."
        if status == 429:
            return "Error: OpenWeather API rate limit exceeded."

        return f"Error: OpenWeather API returned HTTP {status}."

    except requests.exceptions.RequestException:
        return "Error: Could not connect to the OpenWeather service."

    except (KeyError, IndexError, TypeError, ValueError):
        return "Error: Unexpected or invalid weather API response."
@tool
def rag_tool(query: str) -> str:
    """
    Retrieve relevant information from the PDF document.

    Use this tool when the user asks factual or conceptual questions
    that may be answered using the stored PDF documents.

    Args:
        query: The question or search query used to retrieve PDF content.
    """
    retriever = get_retriever()
    documents = retriever.invoke(query)

    if not documents:
        return "No relevant information was found in the PDF."

    formatted_documents = []

    for index, document in enumerate(documents, start=1):
        source = document.metadata.get("source", "Unknown source")
        page = document.metadata.get("page", "Unknown page")

        formatted_documents.append(
            f"Document {index}\n"
            f"Source: {source}\n"
            f"Page: {page}\n"
            f"Content: {document.page_content}"
        )

    return "\n\n".join(formatted_documents)

tools=[rag_tool,tavily_search,calculator,get_stock_price,get_current_weather,purchase_stock]

llm_with_tools=model.bind_tools(tools)

def chat_message(state: ChatState):
    messages = state["messages"]

    # Add the system prompt only when it is missing.
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            *messages,
        ]

    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}

toolnode=ToolNode(tools)


DB_URI = os.getenv("DATABASE_URL")
if not DB_URI:
    raise ValueError("DB_URI is missing from your .env file")

conn = psycopg.connect(
    DB_URI,
    autocommit=True,
    row_factory=dict_row
)

checkpointer = PostgresSaver(conn)
checkpointer.setup()

graph = StateGraph(ChatState)
graph.add_node("chat_message",chat_message)
graph.add_node("tools",toolnode)

graph.add_edge(START,"chat_message")
graph.add_conditional_edges("chat_message",tools_condition)
graph.add_edge("tools", "chat_message") 

workflow = graph.compile(checkpointer=checkpointer)

def get_all_threads():
    threads = set()

    for checkpoint in checkpointer.list(None):
        thread_id = checkpoint.config["configurable"].get("thread_id")
        if thread_id:
            threads.add(thread_id)

    return list(threads)
