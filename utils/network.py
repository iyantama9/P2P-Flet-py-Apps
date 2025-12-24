import asyncio
import websockets
import socket
import miniupnpc 

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

def setup_upnp(port: int):
    """
    Mencoba melakukan Port Forwarding otomatis menggunakan UPnP.
    Mengembalikan Public IP jika berhasil, atau None jika gagal.
    """
    print(f"\n[UPnP] Mencoba membuka port {port} di router...")
    try:
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        devices = upnp.discover()
        if devices == 0:
            print("[UPnP] Tidak ada perangkat UPnP ditemukan.")
            return None

        upnp.selectigd()
        
        lan_ip = upnp.lanaddr
        external_ip = upnp.externalipaddress()

        print(f"[UPnP] Router ditemukan. IP Lokal: {lan_ip}, IP Publik: {external_ip}")

        upnp.addportmapping(port, 'TCP', lan_ip, port, 'P2P Python Chat', '')
        
        print(f"[UPnP] BERHASIL! Port {port} telah diteruskan.")
        print(f"[UPnP] -> Berikan teman Anda IP ini untuk Join: {external_ip}")
        print(f"[UPnP] -> Port: {port}")
        
        return external_ip

    except Exception as e:
        print(f"[UPnP] Gagal melakukan port forwarding: {e}")
        print("[UPnP] Aplikasi tetap berjalan via LAN (Local Network Only).")
        return None

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
    
    setup_upnp(port)

    async with websockets.serve(handle_incoming_messages, "0.0.0.0", port):
        if on_ready_callback:
            on_ready_callback()
        await asyncio.Future() 

async def start_client_async(ip: str, port: int, on_success_callback):
    """Connects to the WebSocket server."""
    uri = f"ws://{ip}:{port}"
    print(f"Connecting to {uri}...")
    async with websockets.connect(uri) as websocket:
        on_success_callback()
        await handle_incoming_messages(websocket)

async def send_message_async(message: bytes):
    """Sends a message over the websocket."""
    if websocket_connection:
        await websocket_connection.send(message)
