
import flet as ft
import asyncio
import threading
import json
from datetime import datetime

from components import startup_view, chat_view
from utils import crypto, network

# --- Global State ---
username = ""
is_currently_typing = False
is_host = False # To differentiate behavior between Host and Joiner
local_public_key_bytes = None # To store our own generated public key

def main(page: ft.Page):
    page.title = "P2P Encrypted Messenger"

    # --- Helper Functions to update UI from other threads ---
    def show_error(message):
        chat_view.status_text.value = f"Error: {message}"
        page.update()

    def show_status(message):
        chat_view.status_text.value = message
        page.update()
        
    def add_chat_message(timestamp: str, sender: str, message: str, color: str = ""):
        chat_view.messages.controls.append(
            ft.Text(f"[{timestamp}] {sender}: {message}", color=color)
        )
        page.update()

    # --- View Management ---
    def show_main_chat_view():
        startup_container.visible = False
        chat_container.visible = True
        page.update()

    # --- Network Logic ---
    def send_public_key():
        """Sends the local public key to the peer (unencrypted)."""
        if not local_public_key_bytes:
            show_error("Local public key not found.")
            return
        key_data = {
            "type": "dh_key_exchange",
            "key": local_public_key_bytes.decode() # Send as a PEM string
        }
        json_data = json.dumps(key_data)
        # This is the only message sent unencrypted.
        threading.Thread(
            target=lambda: asyncio.run(network.send_message_async(json_data.encode())),
            daemon=True
        ).start()

    def send_encrypted_message(message_data: dict):
        """Encrypts and sends a JSON-serializable dictionary."""
        json_data = json.dumps(message_data)
        try:
            encrypted_message = crypto.encrypt_message(json_data)
            threading.Thread(
                target=lambda: asyncio.run(network.send_message_async(encrypted_message)),
                daemon=True
            ).start()
        except Exception as e:
            show_error(f"Failed to send message: {e}")

    # --- Network Event Handlers (Called from network.py) ---
    def on_message_received(message: bytes):
        # If the secure channel is not yet established, this must be the DH key exchange.
        if crypto.cipher_suite is None:
            try:
                data = json.loads(message.decode())
                if data.get("type") == "dh_key_exchange":
                    show_status("Received peer key, establishing secure channel...")
                    peer_public_key_bytes = data["key"].encode()
                    
                    success, error = crypto.establish_secure_channel(peer_public_key_bytes)
                    if not success:
                        show_error(f"DH exchange failed: {error}")
                        # Consider disconnecting the peer here.
                        return
                    
                    # If I am the HOST, the joiner initiated the exchange. I must reply with my key.
                    if is_host:
                        send_public_key()
                    
                    # The channel is now secure. Enable the chat UI.
                    show_status("Secure channel established! You can now chat.")
                    chat_view.ChatView.send_button.disabled = False
                    page.update()
                else:
                    show_error("Received unexpected unencrypted message.")
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                show_error(f"Failed to parse key exchange message: {e}")
            return # Stop processing, as this was a setup message

        # --- If we get here, the channel is secure. All messages are encrypted. ---
        try:
            decrypted_json = crypto.decrypt_message(message)
            data = json.loads(decrypted_json)
            message_type = data.get("type")

            if message_type == "typing":
                if data["status"] == "start":
                    chat_view.typing_indicator.value = f"{data.get('username', 'Peer')} is typing..."
                else: # "stop"
                    chat_view.typing_indicator.value = ""
                page.update()
            elif message_type == "chat":
                add_chat_message(data["timestamp"], data["username"], data["message"])

        except json.JSONDecodeError:
            add_chat_message(datetime.now().strftime("%H:%M:%S"), "System", "Received an invalid message format.", color="red")
        except Exception as e:
            add_chat_message(datetime.now().strftime("%H:%M:%S"), "Error", f"Failed to decrypt message: {e}", color="red")

    def on_peer_disconnected():
        show_status("Peer disconnected.")
        chat_view.typing_indicator.value = ""
        chat_view.ChatView.send_button.disabled = True
        # Reset cryptographic state
        crypto.cipher_suite = None
        crypto.dh_private_key = None
        page.update()
        
    def on_client_connect_success():
        # This is for the JOINER. Once connected, start the key exchange.
        show_status("Connected to peer. Initiating key exchange...")
        send_public_key()

    # Assign handlers to the network module
    network.on_message_received = on_message_received
    network.on_peer_disconnected = on_peer_disconnected

    # --- UI Event Handlers (Callbacks for components) ---
    def handle_typing_change(text_value: str):
        global is_currently_typing
        # Don't send typing indicators if the channel isn't secure yet
        if crypto.cipher_suite is None:
            return
        if text_value and not is_currently_typing:
            is_currently_typing = True
            send_encrypted_message({"type": "typing", "username": username, "status": "start"})
        elif not text_value and is_currently_typing:
            is_currently_typing = False
            send_encrypted_message({"type": "typing", "username": username, "status": "stop"})

    def host_chat_click(e):
        global username, is_host, local_public_key_bytes
        username = startup_view.username_input.value
        if not username:
            show_error("Username cannot be empty.")
            return

        is_host = True
        _, pub_key_bytes = crypto.generate_dh_keys()
        local_public_key_bytes = pub_key_bytes
        
        port = int(startup_view.port_input.value)
        threading.Thread(target=lambda: asyncio.run(network.start_server_async(port)), daemon=True).start()
        
        show_status(f"Hosting on {network.get_local_ip()}:{port}\nWaiting for peer to connect...")
        show_main_chat_view()

    def join_chat_click(e):
        global username, is_host, local_public_key_bytes
        username = startup_view.username_input.value
        if not username:
            show_error("Username cannot be empty.")
            return

        is_host = False
        _, pub_key_bytes = crypto.generate_dh_keys()
        local_public_key_bytes = pub_key_bytes

        ip = startup_view.ip_input.value
        port = int(startup_view.port_input.value)
        if not ip:
            show_error("IP address is required.")
            return
        
        threading.Thread(target=lambda: asyncio.run(network.start_client_async(ip, port, on_client_connect_success)), daemon=True).start()
        
        show_main_chat_view()
        show_status(f"Connecting to {ip}:{port}...")

    def send_message_click(e):
        message_text = chat_view.new_message.value
        if not message_text:
            return
            
        now = datetime.now()
        timestamp = now.strftime("%H:%M:%S")

        message_data = {
            "type": "chat",
            "username": username,
            "message": message_text,
            "timestamp": timestamp
        }
        send_encrypted_message(message_data)
        
        add_chat_message(timestamp, "You", message_text)
        chat_view.new_message.value = ""
        # We are no longer typing after sending a message
        handle_typing_change("") 
        page.update()

    # --- Initial Page Setup ---
    startup_view.on_host_click = host_chat_click
    startup_view.on_join_click = join_chat_click
    chat_view.on_send_message_click = send_message_click
    chat_view.on_typing_change = handle_typing_change

    startup_container = startup_view.StartupView()
    chat_container = chat_view.ChatView()
    page.add(startup_container, chat_container)

if __name__ == "__main__":
    # This script is not meant to be run directly. Use run.py
    print("Please run this application using run.py")
