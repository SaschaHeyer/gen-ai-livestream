import os
from dotenv import load_dotenv, find_dotenv
from google.adk.agents import Agent
from vertexai.preview import reasoning_engines

# --- Configuration (Vertex AI) ---
# Load environment variables from .env file
load_dotenv(find_dotenv())

# ==========================================
# 1. Flight Agent & Tools
# ==========================================

def search_flights(origin: str, destination: str) -> str:
    """Searches for flights between origin and destination."""
    print(f"\n[Flight Tool] Searching for flights from {origin} to {destination}...")
    return (f"Found flights from {origin} to {destination}:\n" 
            f"1. Flight 101 (SkyHigh Air): 08:00 AM - 11:00 AM (3h 00m) - $300\n" 
            f"2. Flight 202 (Oceanic Airlines): 02:00 PM - 06:30 PM (4h 30m) - $350")

def book_flight(flight_number: str) -> str:
    """Books a specific flight by flight number."""
    print(f"\n[Flight Tool] Booking flight {flight_number}...")
    return f"Confirmed booking for flight {flight_number}. Ref: FLT-123."

flight_agent = Agent(
    name="flight_agent",
    model="gemini-2.5-flash",
    description="Specialized assistant for searching and booking flights.",
    instruction="""You are the Flight Specialist.
Use 'search_flights' to find options.
Use 'book_flight' to book specific flights.
Always verify details before booking.""",
    tools=[search_flights, book_flight]
)

# ==========================================
# 2. Hotel Agent & Tools
# ==========================================

def search_hotels(location: str) -> str:
    """Searches for hotels in a specific location."""
    print(f"\n[Hotel Tool] Searching for hotels in {location}...")
    return f"Found hotels in {location}: Hotel Sunshine ($150/night), Grand Plaza ($250/night)."

def book_hotel(hotel_name: str, nights: int) -> str:
    """Books a hotel for a number of nights."""
    print(f"\n[Hotel Tool] Booking {hotel_name} for {nights} nights...")
    return f"Confirmed booking at {hotel_name} for {nights} nights. Ref: HTL-456."

hotel_agent = Agent(
    name="hotel_agent",
    model="gemini-2.5-flash",
    description="Specialized assistant for searching and booking hotels.",
    instruction="""You are the Hotel Specialist.
Use 'search_hotels' to find accommodation.
Use 'book_hotel' to make a reservation.
Always verify details before booking.""",
    tools=[search_hotels, book_hotel]
)

# ==========================================
# 3. Root Travel Coordinator Agent
# ==========================================

root_agent = Agent(
    name="root_travel_agent",
    model="gemini-2.5-flash",
    description="Main travel assistant that coordinates requests for flights and hotels by delegating to specialized agents.",
    instruction="""You are the primary Travel Coordinator assistant.
Your main role is to help users plan their trips by coordinating flights and hotels.

Use the descriptions of the 'flight_agent' and 'hotel_agent' to decide when to delegate.
- Delegate flight-related requests to 'flight_agent'.
- Delegate accommodation/hotel requests to 'hotel_agent'.

You do not have tools to book directly; you must delegate to the specialists.
If a user asks for a full trip plan, you may need to consult both agents.
""",
    sub_agents=[flight_agent, hotel_agent]
)

# Define the App explicitly for deployment
app = reasoning_engines.AdkApp(
    agent=root_agent,
    enable_tracing=True,
)
