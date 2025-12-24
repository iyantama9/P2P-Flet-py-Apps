import asyncio
import websockets
import socket

on_message_received = None 
on_peer_disconnected = None
on_peer_connected = None
websocket_connection = None

def get_local_ip() -> str:
    """Gets the local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

async def handle_incoming_messages(websocket):
    """Listens for messages and calls the registered callback."""
    global websocket_connection
    websocket_connection = websocket
    if on_peer_connected:
        on_peer_connected()
    try:
        async for message in websocket:
            if on_message_received:
                on_message_received(message)
    except websockets.exceptions.ConnectionClosed:
        if on_peer_disconnected:
            on_peer_disconnected()

async def start_server_async(port: int, on_ready_callback=None):
    """Starts the WebSocket server and calls a callback when ready."""
    async with websockets.serve(handle_incoming_messages, "0.0.0.0", port):
        if on_ready_callback:
            on_ready_callback()
        await asyncio.Future() 

async def start_client_async(ip: str, port: int, on_success_callback):
    """Connects to the WebSocket server."""
    uri = f"ws://{ip}:{port}"
    async with websockets.connect(uri) as websocket:
        on_success_callback()
        await handle_incoming_messages(websocket)

async def send_message_async(message: bytes):
    """Sends a message over the websocket."""
    if websocket_connection:
        await websocket_connection.send(message)
