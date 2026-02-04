

import logging
import os
import asyncio
from fastmcp import FastMCP
import datetime
import random
import uuid
import copy

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

mcp = FastMCP("Flight MCP Server ✈️")

# A dummy database of flights for consistent results between tools
DUMMY_FLIGHT_DATABASE = {
    "DX456": {
        "flight_number": "DX456",
        "airline": "DevAir",
        "departure_airport": "BER",
        "arrival_airport": "STO",
        "departure_time": "2024-11-15T08:30:00",
        "arrival_time": "2024-11-15T10:30:00",
        "duration": "2h 0m",
        "price": 250.75,
        "currency": "USD",
        "stops": 0,
        "layovers": [],
        "terminal": "2",
        "gate": "B32",
        "boarding_time": "2024-11-15T07:45:00",
        "aircraft": "Airbus A320",
        "baggage_allowance": {
            "carry_on": "1 piece (8kg)",
            "checked": "2 pieces (23kg each)"
        }
    },
    "ADK789": {
        "flight_number": "ADK789",
        "airline": "Agent Airways",
        "departure_airport": "BER",
        "arrival_airport": "STO",
        "departure_time": "2024-11-15T14:00:00",
        "arrival_time": "2024-11-15T17:30:00",
        "duration": "3h 30m",
        "price": 180.50,
        "currency": "USD",
        "stops": 1,
        "layovers": [
            {
                "airport": "CPH",
                "duration": "1h 30m"
            }
        ],
        "terminal": "1",
        "gate": "A10",
        "boarding_time": "2024-11-15T13:15:00",
        "aircraft": "Boeing 737",
        "baggage_allowance": {
            "carry_on": "1 piece (7kg)",
            "checked": "1 piece (23kg)"
        }
    }
}

def update_flight_date(flight_data, new_date_str):
    """
    Updates the date part of datetime strings in the flight data
    to match the requested new_date_str (YYYY-MM-DD).
    """
    updated_flight = copy.deepcopy(flight_data)
    
    # Helper to replace date in "YYYY-MM-DDTHH:MM:SS"
    def replace_date(timestamp_str, new_date):
        if not timestamp_str:
            return timestamp_str
        try:
            # Split time part
            _, time_part = timestamp_str.split('T')
            return f"{new_date}T{time_part}"
        except ValueError:
            return timestamp_str

    if "departure_time" in updated_flight:
        updated_flight["departure_time"] = replace_date(updated_flight["departure_time"], new_date_str)
    
    if "arrival_time" in updated_flight:
        updated_flight["arrival_time"] = replace_date(updated_flight["arrival_time"], new_date_str)
        
    if "boarding_time" in updated_flight:
        updated_flight["boarding_time"] = replace_date(updated_flight["boarding_time"], new_date_str)
        
    return updated_flight


@mcp.tool()
def search_flights(
    departure_city: str,
    arrival_city: str,
    departure_date: str,
):
    """Searches for available flights for a given route and date.

    Args:
        departure_city: The city or airport code to depart from (e.g., "New York", "JFK").
        arrival_city: The city or airport code for the arrival (e.g., "London", "LHR").
        departure_date: The desired date of departure in YYYY-MM-DD format.

    Returns:
        A list of dictionaries, where each dictionary represents an available flight.
    """
    logger.info(f"--- 🛠️ Tool: search_flights called for {departure_city} to {arrival_city} on {departure_date} ---")
    
    # Return our dummy flights but updated with the requested date
    results = []
    for flight in DUMMY_FLIGHT_DATABASE.values():
        # Update the date
        updated_flight = update_flight_date(flight, departure_date)
        
        # Filter for summary view
        summary = {k: v for k, v in updated_flight.items() if k in ["flight_number", "airline", "departure_time", "arrival_time", "price", "currency", "stops"]}
        results.append(summary)

    logger.info(f'✅ Returning {len(results)} dummy flights for {departure_date}.')
    return results

@mcp.tool()
def get_flight_details(flight_number: str):
    """Gets all available details for a specific flight number.

    Args:
        flight_number: The flight number to get details for (e.g., "DX456").

    Returns:
        A dictionary containing the detailed flight information or an error message.
    """
    logger.info(f"--- 🛠️ Tool: get_flight_details called for {flight_number} ---")
    
    flight = DUMMY_FLIGHT_DATABASE.get(flight_number)
    
    if not flight:
        logger.warning(f"Flight {flight_number} not found.")
        return {"error": f"Flight with number {flight_number} not found."}
    
    # For details, default to "today" since we don't have context, 
    # or arguably we could require date. But to keep it simple, we'll use today.
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    updated_flight = update_flight_date(flight, today_str)
    
    logger.info(f"✅ Returning details for flight {flight_number}.")
    return updated_flight

@mcp.tool()
def book_flight(flight_number: str, passenger_name: str, number_of_bags: int = 0):
    """Books a flight for a passenger.

    Args:
        flight_number: The flight number to book (e.g., "DX456").
        passenger_name: The full name of the passenger.
        number_of_bags: The number of checked bags.

    Returns:
        A dictionary containing the booking confirmation details or an error message.
    """
    logger.info(f"--- 🛠️ Tool: book_flight called for {flight_number} for {passenger_name} ---")

    flight = DUMMY_FLIGHT_DATABASE.get(flight_number)
    
    if not flight:
        logger.warning(f"Flight {flight_number} not found for booking.")
        return {"error": f"Cannot book flight. Flight number {flight_number} not found."}

    # Use today's date for the booking confirmation
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    flight = update_flight_date(flight, today_str)

    confirmation_number = str(uuid.uuid4()).split('-')[0].upper()
    
    booking_confirmation = {
        "status": "CONFIRMED",
        "confirmation_number": confirmation_number,
        "passenger_name": passenger_name,
        "flight_details": {
            "flight_number": flight["flight_number"],
            "airline": flight["airline"],
            "departure_airport": flight["departure_airport"],
            "arrival_airport": flight["arrival_airport"],
            "departure_time": flight["departure_time"],
            "arrival_time": flight["arrival_time"],
        },
        "checked_bags": number_of_bags,
        "total_price": flight["price"] + (number_of_bags * 25.0), # Assuming $25 per bag
        "currency": flight["currency"],
        "message": "Thank you for booking! Please check your email for your e-ticket."
    }

    logger.info(f"✅ Flight {flight_number} booked successfully. Confirmation: {confirmation_number}")
    return booking_confirmation


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"🚀 MCP server started on port {port}")
    asyncio.run(
        mcp.run_async(
            transport="http",
            host="0.0.0.0",
            port=port,
        )
    )
