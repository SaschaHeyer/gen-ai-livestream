import asyncio
import websockets

# This handler is called for each new client connection
async def handler(websocket, path=None):
    print(f"Client connected from {websocket.remote_address}")
    # Keep the connection open and process messages
    async for message in websocket:
        print(f"Received from client: '{message}'")
        reply = f"Server received: '{message}'"
        await websocket.send(reply)
        print(f"Sent to client: '{reply}'")
    print(f"Connection with {websocket.remote_address} ended.")

async def main():
    # Define the host and port for the server
    host = "localhost"
    port = 8765 # A common port for WebSocket development

    # Start the WebSocket server
    async with websockets.serve(handler, host, port):
        print(f"WebSocket server started on ws://{host}:{port}")
        await asyncio.Future()  # Run forever until interrupted

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server shutting down...")
