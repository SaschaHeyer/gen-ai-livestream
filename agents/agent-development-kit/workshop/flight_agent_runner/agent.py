import os
from dotenv import load_dotenv, find_dotenv
from google.adk.agents import Agent

# --- Configuration (Vertex AI) ---
# Load environment variables from .env file (searches parent directories)
load_dotenv(find_dotenv())

# --- Tools ---
def search_flights(origin: str, destination: str) -> str:
    """Searches for flights between origin and destination."""
    print(f"\n[Tool] Searching for flights from {origin} to {destination}...")
    return f"Found the following flights from {origin} to {destination}:\n1. Flight 101: 10:00 AM - $300\n2. Flight 202: 2:00 PM - $350"

def book_flight(flight_number: str) -> str:
    """Books a specific flight by flight number."""
    print(f"\n[Tool] Booking flight {flight_number}...")
    return f"Successfully booked flight {flight_number}. Confirmation code: ABC-123."

# --- Agent Definition ---
flight_agent = Agent(
    name="flight_agent",
    model="gemini-2.5-flash",
    description="Specialized assistant for searching and booking flights.",
    instruction="""You are the Flight Specialist. Your tasks are to:
Use the 'search_flights' tool when the user wants to find flights.
Use the 'book_flight' tool when the user wants to book a specific flight.
Always verify the flight details with the user before booking.
""",
    tools=[search_flights, book_flight]
)
