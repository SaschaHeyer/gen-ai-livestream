
import asyncio
import pprint
from fastmcp import Client

async def test_server():
    """
    Connects to the local MCP server and tests the available flight tools
    using the fastmcp Client.
    """
    # Use 127.0.0.1 to avoid localhost IPv6 issues on macOS
    server_url = "http://127.0.0.1:8080/mcp"
    
    print(f"--- ⏳ Connecting to MCP Server at {server_url}... ---")
    
    # fastmcp Client context manager handles the connection
    async with Client(server_url) as client:
        
        # --- Test 1: search_flights ---
        print("\n--- ✈️  Test 1: Calling 'search_flights' ---")
        try:
            # We use call_tool directly with the tool name and arguments dictionary
            result = await client.call_tool(
                "search_flights", 
                {
                    "departure_city": "BER",
                    "arrival_city": "STO",
                    "departure_date": "2024-11-15"
                }
            )
            
            # fastmcp returns a CallToolResult object. The actual data is in content[0].text
            # But since our server returns a JSON-serializable list/dict, fastmcp might handle it.
            # Let's inspect the result.
            print("--- ✅ Success! Found flights: ---")
            
            # The result from call_tool is expected to be a list of Content objects.
            # If the tool returned structured data, it's often serialized to text (JSON).
            # We'll print the raw text content for verification.
            if result.content:
                print(result.content[0].text)
            else:
                print("No content returned.")

            # For the purpose of the test flow, we need to parse this or just pick a hardcoded ID
            # Since parsing the text response back to JSON here might be verbose without extra libs,
            # and we know our server has "DX456", we'll use that for the next tests.
            flight_number_to_test = "DX456"

        except Exception as e:
            print(f"--- ❌ Error in search_flights: {e} ---")
            flight_number_to_test = "DX456"

        # --- Test 2: get_flight_details ---
        print(f"\n--- ✈️  Test 2: Calling 'get_flight_details' for {flight_number_to_test} ---")
        try:
            result = await client.call_tool(
                "get_flight_details",
                {"flight_number": flight_number_to_test}
            )
            print(f"--- ✅ Success! Details for {flight_number_to_test}: ---")
            if result.content:
                print(result.content[0].text)

        except Exception as e:
            print(f"--- ❌ Error in get_flight_details: {e} ---")

        # --- Test 3: book_flight ---
        print(f"\n--- ✈️  Test 3: Calling 'book_flight' for {flight_number_to_test} ---")
        try:
            result = await client.call_tool(
                "book_flight",
                {
                    "flight_number": flight_number_to_test,
                    "passenger_name": "Alex Doe",
                    "number_of_bags": 1
                }
            )
            print(f"--- ✅ Success! Booking for {flight_number_to_test}: ---")
            if result.content:
                print(result.content[0].text)

        except Exception as e:
            print(f"--- ❌ Error in book_flight: {e} ---")


if __name__ == "__main__":
    asyncio.run(test_server())
