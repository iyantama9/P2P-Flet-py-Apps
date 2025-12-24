import flet as ft
import asyncio
import threading
import json
from datetime import datetime

from components import startup_view, chat_view
from utils import crypto, network

username = ""
is_currently_typing = False
is_host = False  
local_public_key_bytes = None  


def main(page: ft.Page):
    page.title = "CAM - P2P Ver"


    def pubsub_handler(message):
        msg_type = message.get("type")
        payload = message.get("payload")

        if msg_type == "update_status":
            show_status(payload)
        elif msg_type == "update_error":
            show_error(payload)
        elif msg_type == "client_connect_success":
            on_client_connect_success()
        elif msg_type == "peer_connected":
            on_peer_connected()
        elif msg_type == "peer_disconnected":
            on_peer_disconnected()
        elif msg_type == "message_received":
            on_message_received(payload)

    page.pubsub.subscribe(pubsub_handler)

    def show_error(message):
        if startup_container.visible:
            startup_view.error_text.value = message
        else:
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

    def show_main_chat_view():
        startup_container.visible = False
        chat_container.visible = True
        page.update()

    def send_public_key():
        if not local_public_key_bytes:
            show_error("Local public key not found.")
            return
        key_data = {
            "type": "dh_key_exchange",
            "key": local_public_key_bytes.decode()
        }
        json_data = json.dumps(key_data)
        threading.Thread(
            target=lambda: asyncio.run(
                network.send_message_async(json_data.encode())
            ),
            daemon=True
        ).start()

    def send_encrypted_message(message_data: dict):
        json_data = json.dumps(message_data)
        try:
            encrypted_message = crypto.encrypt_message(json_data)

            # 🔐 PRINT HANYA UNTUK CHAT
            if message_data.get("type") == "chat":
                print(f"[CRYPTO][ENCRYPT] {encrypted_message}")

            threading.Thread(
                target=lambda: asyncio.run(
                    network.send_message_async(encrypted_message)
                ),
                daemon=True
            ).start()
        except Exception as e:
            show_error(f"Failed to send message: {e}")

    # --- Receive Handler ---
    def on_message_received(message: bytes):
        if crypto.cipher_suite is None:
            try:
                data = json.loads(message.decode())
                if data.get("type") == "dh_key_exchange":
                    show_status("Received peer key, establishing secure channel...")
                    peer_public_key_bytes = data["key"].encode()

                    success, error = crypto.establish_secure_channel(peer_public_key_bytes)
                    if not success:
                        show_error(f"DH exchange failed: {error}")
                        return

                    if is_host:
                        send_public_key()

                    show_status("Secure channel established! You can now chat.")
                    chat_view.ChatView.send_button.disabled = False
                    page.update()
                else:
                    show_error("Received unexpected unencrypted message.")
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                show_error(f"Failed to parse key exchange message: {e}")
            return

        try:
            decrypted_json = crypto.decrypt_message(message)
            data = json.loads(decrypted_json)

            # 🔐 PRINT HANYA UNTUK CHAT
            if data.get("type") == "chat":
                print(f"[CRYPTO][RECEIVE-ENCRYPTED] {message}")
                print(f"[CRYPTO][DECRYPT] {decrypted_json}")

            if data.get("type") == "typing":
                chat_view.typing_indicator.value = (
                    f"{data.get('username', 'Peer')} is typing..."
                    if data["status"] == "start" else ""
                )
                page.update()
            elif data.get("type") == "chat":
                add_chat_message(
                    data["timestamp"],
                    data["username"],
                    data["message"]
                )

        except Exception as e:
            add_chat_message(
                datetime.now().strftime("%H:%M:%S"),
                "Error",
                f"Failed to decrypt message: {e}",
                color="red"
            )

    def on_peer_disconnected():
        show_status("Peer disconnected.")
        chat_view.typing_indicator.value = ""
        chat_view.ChatView.send_button.disabled = True
        crypto.cipher_suite = None
        crypto.dh_private_key = None
        page.update()

    def on_client_connect_success():
        show_status("Connected to peer. Initiating key exchange...")
        send_public_key()

    def on_peer_connected():
        show_status("Peer connected. Initiating key exchange...")


    def ps_on_message_received(msg):
        page.pubsub.send_all({"type": "message_received", "payload": msg})

    def ps_on_peer_disconnected():
        page.pubsub.send_all({"type": "peer_disconnected"})

    def ps_on_client_connect_success():
        page.pubsub.send_all({"type": "client_connect_success"})

    def ps_on_peer_connected():
        page.pubsub.send_all({"type": "peer_connected"})

    network.on_message_received = ps_on_message_received
    network.on_peer_disconnected = ps_on_peer_disconnected
    network.on_peer_connected = ps_on_peer_connected

    def handle_typing_change(text_value: str):
        global is_currently_typing
        if crypto.cipher_suite is None:
            return
        if text_value and not is_currently_typing:
            is_currently_typing = True
            send_encrypted_message(
                {"type": "typing", "username": username, "status": "start"}
            )
        elif not text_value and is_currently_typing:
            is_currently_typing = False
            send_encrypted_message(
                {"type": "typing", "username": username, "status": "stop"}
            )

    def host_chat_click(e):
        global username, is_host
        username = startup_view.username_input.value
        if not username:
            show_error("Username cannot be empty.")
            return
        is_host = True
        port = int(startup_view.port_input.value)
        show_main_chat_view()
        show_status("Generating cryptographic keys...")

        def start_hosting_in_background():
            global local_public_key_bytes
            _, pub_key_bytes = crypto.generate_dh_keys()
            local_public_key_bytes = pub_key_bytes
            page.pubsub.send_all(
                {"type": "update_status", "payload": "Starting server..."}
            )

            def on_server_ready():
                page.pubsub.send_all({
                    "type": "update_status",
                    "payload": f"Hosting on {network.get_local_ip()}:{port}\nWaiting for peer to connect..."
                })

            asyncio.run(
                network.start_server_async(port, on_ready_callback=on_server_ready)
            )

        threading.Thread(
            target=start_hosting_in_background,
            daemon=True
        ).start()

    def join_chat_click(e):
        global username, is_host
        username = startup_view.username_input.value
        if not username:
            show_error("Username cannot be empty.")
            return
        is_host = False
        ip = startup_view.ip_input.value
        port = int(startup_view.port_input.value)
        if not ip:
            show_error("IP address is required.")
            return
        show_main_chat_view()
        show_status("Generating cryptographic keys...")

        def start_joining_in_background():
            global local_public_key_bytes
            _, pub_key_bytes = crypto.generate_dh_keys()
            local_public_key_bytes = pub_key_bytes
            page.pubsub.send_all({
                "type": "update_status",
                "payload": f"Connecting to {ip}:{port}..."
            })
            asyncio.run(
                network.start_client_async(ip, port, ps_on_client_connect_success)
            )

        threading.Thread(
            target=start_joining_in_background,
            daemon=True
        ).start()

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
        handle_typing_change("")
        page.update()

    startup_view.on_host_click = host_chat_click
    startup_view.on_join_click = join_chat_click
    chat_view.on_send_message_click = send_message_click
    chat_view.on_typing_change = handle_typing_change

    startup_container = startup_view.StartupView()
    chat_container = chat_view.ChatView()
    page.add(startup_container, chat_container)


if __name__ == "__main__":
    print("Please run this application using run.py")
